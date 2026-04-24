import asyncio
import httpx
import time

URL = "http://localhost:8000/v1/jobs?original_url=https://raw.githubusercontent.com/python/pythondotorg/master/static/img/python-logo.png"
TOTAL_REQUESTS = 1000
CONCURRENT_CONNECTIONS = 100 # Сколько запросов шлем одновременно

async def make_request(client: httpx.AsyncClient, i: int):
    try:
        resp = await client.post(URL)
        return resp.status_code
    except Exception as e:
        return str(e)

async def main():
    print(f"🚀 Начинаем бомбардировку: {TOTAL_REQUESTS} запросов...")
    t0 = time.time()
    
    # Настраиваем лимиты, чтобы не "задушить" сам скрипт тестирования
    limits = httpx.Limits(max_connections=CONCURRENT_CONNECTIONS, max_keepalive_connections=CONCURRENT_CONNECTIONS)
    
    async with httpx.AsyncClient(limits=limits, timeout=30.0) as client:
        tasks = [make_request(client, i) for i in range(TOTAL_REQUESTS)]
        # asyncio.gather запускает все задачи конкурентно
        results = await asyncio.gather(*tasks)
    
    t1 = time.time()
    success = results.count(202)
    errors = TOTAL_REQUESTS - success
    
    print("-" * 30)
    print(f"⏱ Время теста: {t1-t0:.2f} сек")
    print(f"✅ Успешных (202 Accepted): {success}/{TOTAL_REQUESTS}")
    if errors > 0:
        print(f"❌ Ошибок: {errors}")
    print(f"⚡ Пропускная способность API: {TOTAL_REQUESTS / (t1-t0):.2f} req/sec")
    print("-" * 30)

if __name__ == "__main__":
    asyncio.run(main())