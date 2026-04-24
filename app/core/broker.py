import os
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend
import structlog

log = structlog.get_logger()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Инициализируем брокер и бэкенд результатов
result_backend = RedisAsyncResultBackend(REDIS_URL)
broker = ListQueueBroker(REDIS_URL).with_result_backend(result_backend)

@broker.on_event("startup")
async def startup() -> None:
    log.info("taskiq_broker_started", redis_url=REDIS_URL)

@broker.on_event("shutdown")
async def shutdown() -> None:
    log.info("taskiq_broker_shutdown")