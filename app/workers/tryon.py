import asyncio
import time
import httpx
import structlog
import rust_processor
from uuid import UUID

from app.core.broker import broker
from app.db.database import AsyncSessionLocal
from app.db.models import Job, JobStatus

log = structlog.get_logger()

async def mock_ai_call(image_bytes: bytes) -> str:
    """Мок вызова к GPU-инстансу"""
    await asyncio.sleep(2.0) 
    import random
    if random.random() < 0.6:
        raise ConnectionError("AI GPU node timeout or OOM")
    return "https://cdn.saas.com/results/success_tryon.jpg"


@broker.task(task_name="process_tryon_job")
async def process_tryon_job(job_id: str):
    # Биндим ID 
    job_log = log.bind(job_id=job_id)
    job_log.info("job_started")
    
    metrics = {}
    
    # TaskIQ запускается в отдельном процессе, нужна своя сессия БД
    async with AsyncSessionLocal() as db:
        # 1. Загрузка Job из БД
        job = await db.get(Job, UUID(job_id))
        if not job:
            job_log.error("job_not_found")
            return

        # Обновляем статус
        job.status = JobStatus.PROCESSING
        await db.commit()

        try:
            # --- ЭТАП 1: Скачивание (I/O) ---
            t0 = time.perf_counter()
            async with httpx.AsyncClient() as client:
                resp = await client.get(job.original_url, timeout=10.0)
                resp.raise_for_status()
                raw_bytes = resp.content
            metrics["download_ms"] = round((time.perf_counter() - t0) * 1000, 2)
            
            # --- ЭТАП 2: Rust Processing (CPU) ---
            t0 = time.perf_counter()
            try:
                processed_bytes = rust_processor.process_image(raw_bytes)
            except Exception as e:
                job_log.error("rust_processing_failed", error=str(e), exc_info=True)
                job.status = JobStatus.FAILED
                job.performance_metrics = metrics
                await db.commit()
                return 

            metrics["rust_cpu_ms"] = round((time.perf_counter() - t0) * 1000, 2)

            # --- ЭТАП 3: AI Inference (Network/GPU) с Exponential Backoff ---
            t0 = time.perf_counter()
            ai_result_url = None
            backoff_delays = [5, 15, 30]
            
            for attempt, delay in enumerate(backoff_delays + [None]):
                try:
                    job_log.info("ai_call_attempt", attempt=attempt+1)
                    ai_result_url = await mock_ai_call(processed_bytes)
                    break # Успех
                except Exception as e:
                    if delay is None:
                        job_log.error("ai_call_fatal", error=str(e), attempts=len(backoff_delays)+1)
                        job.status = JobStatus.FAILED
                        job.performance_metrics = metrics
                        await db.commit()
                        return
                    
                    job_log.warning("ai_call_failed_retrying", delay=delay, error=str(e))
                    await asyncio.sleep(delay)
            
            metrics["ai_gpu_ms"] = round((time.perf_counter() - t0) * 1000, 2)

            # --- ЭТАП 4: Успешное завершение ---
            job.status = JobStatus.COMPLETED
            job.result_url = ai_result_url
            job.performance_metrics = metrics
            await db.commit()
            
            job_log.info("job_completed_successfully", metrics=metrics)

        except Exception as e:
            job_log.error("job_failed_unexpectedly", error=str(e), exc_info=True)
            job.status = JobStatus.FAILED
            await db.commit()