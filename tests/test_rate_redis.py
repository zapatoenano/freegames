import pytest
from fastapi.testclient import TestClient
import fakeredis.aioredis as fakeredis
import asyncio

from app.main import app
from app.rate_limit_redis import RedisRateLimiter, make_redis_rate_middleware
@pytest.mark.asyncio
async def test_redis_rate_limit(monkeypatch):
    # use fakeredis to simulate Redis
    fake = await fakeredis.FakeRedis()

    limiter = RedisRateLimiter(redis_url="redis://localhost:6379", per_min=2)
    await limiter.init()
    limiter._redis = fake

    # create a lightweight FastAPI app using the redis middleware
    from fastapi import FastAPI

    test_app = FastAPI()

    @test_app.get("/health")
    def health():
        return {"status": "ok"}

    # mount middleware created with our limiter
    test_app.middleware("http")(make_redis_rate_middleware(limiter))

    client = TestClient(test_app)

    # First allowed
    r1 = client.get("/health")
    assert r1.status_code == 200
    # Second allowed
    r2 = client.get("/health")
    assert r2.status_code == 200
    # Third blocked
    r3 = client.get("/health")
    assert r3.status_code == 429
