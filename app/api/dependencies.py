from typing import AsyncGenerator
from app.db.database import AsyncSessionLocal

# Dependency для получения сессии БД в роутах
async def get_db_session() -> AsyncGenerator:
    async with AsyncSessionLocal() as session:
        yield session