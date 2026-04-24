import structlog
from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logger import setup_logging
from app.api.dependencies import get_db_session

# Инициализирование логирования
setup_logging()
log = structlog.get_logger()

app = FastAPI(title="Virtual Try-On AI SaaS")

# Глобальный обработчик ошибок
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error("unhandled_exception", url=str(request.url), error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. We are working on it."}
    )

# Базовый роут Healthcheck
@app.get("/health")
async def health_check():
    log.info("healthcheck_called", status="ok")
    return {"status": "ok", "message": "Systems nominal"}

# Роут с БД
@app.get("/jobs", status_code=200)
async def list_jobs(db: AsyncSession = Depends(get_db_session)):
    log.info("fetch_jobs_started")
    # Здесь будет вызов к БД: await db.execute(select(Job))
    return {"message": "Job list will be here"}