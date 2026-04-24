import uuid
import structlog
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

from app.core.logger import setup_logging
from app.api.dependencies import get_db_session
from app.db.models import Job, JobStatus
from app.core.broker import broker

from app.db.database import engine, Base

import app.workers.tryon

import os
from fastapi.responses import FileResponse

setup_logging()
log = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # СОЗДАЕМ ТАБЛИЦЫ В БД ПРИ СТАРТЕ
    log.info("initializing_database")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    await broker.startup()
    yield
    await broker.shutdown()

app = FastAPI(title="Virtual Try-On AI SaaS", lifespan=lifespan)

@app.get("/", response_class=FileResponse, include_in_schema=False)
async def serve_admin_dashboard():
    file_path = os.path.join(os.path.dirname(__file__), "admin.html")
    return FileResponse(file_path)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error("unhandled_exception", url=str(request.url), error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. We are working on it."}
    )

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Systems nominal"}

@app.get("/v1/status/{job_id}", status_code=200)
async def get_job_status(job_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    log.info("check_status_called", job_id=str(job_id))
    
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Высчитываем время с момента создания (в секундах)
    # Приводим к UTC для безопасного сравнения
    now_utc = datetime.now(timezone.utc)
    # Предполагаем, что job.created_at сохранено с timezone
    created_at_utc = job.created_at.replace(tzinfo=timezone.utc) if job.created_at.tzinfo is None else job.created_at
    
    time_in_system = round((now_utc - created_at_utc).total_seconds(), 2)
    
    response = {
        "id": job.id,
        "status": job.status,
        "created_at": job.created_at,
        "result_url": job.result_url
    }

    if job.status == JobStatus.PENDING:
        response["queue_wait_time_sec"] = time_in_system
    elif job.status == JobStatus.PROCESSING:
        response["processing_time_sec"] = time_in_system
    elif job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
        response["total_time_sec"] = time_in_system
        response["performance_metrics"] = job.performance_metrics

    return response

@app.post("/v1/jobs", status_code=202)
async def create_job(original_url: str, db: AsyncSession = Depends(get_db_session)):
    # 1. Создаем запись в БД
    new_job = Job(original_url=original_url)
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)
    
    # 2. Отправляем в TaskIQ (обращаемся к импортированному модулю напрямую)
    from app.workers.tryon import process_tryon_job
    await process_tryon_job.kiq(str(new_job.id))
    
    return {"id": new_job.id, "status": "PENDING"}