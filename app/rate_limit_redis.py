from typing import Optional
import os
import time
from fastapi import Request
from fastapi.responses import JSONResponse
from redis import asyncio as aioredis


class RedisRateLimiter:
    def __init__(self, redis_url: str, per_min: int = 60, prefix: str = "rl"):
        self.redis_url = redis_url
        self.per_min = per_min
        self.prefix = prefix
        self._redis: Optional[aioredis.Redis] = None

    async def init(self):
        if self._redis is None:
            self._redis = aioredis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)

    async def close(self):
        if self._redis is not None:
            try:
                await self._redis.close()
            except Exception:
                pass

    async def allow_request(self, ip: str) -> bool:
        """Fixed-window counter per minute implemented with INCR + EXPIRE."""
        if self._redis is None:
            raise RuntimeError("redis client not initialized")
        now = int(time.time())
        window = now // 60
        key = f"{self.prefix}:{ip}:{window}"
        # INCR
        val = await self._redis.incr(key)
        if val == 1:
            # set expire to 61 seconds to cover the minute
            await self._redis.expire(key, 61)
        return val <= self.per_min


def make_redis_rate_middleware(limiter: RedisRateLimiter):
    async def middleware(request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        allowed = True
        try:
            allowed = await limiter.allow_request(client_ip)
        except Exception:
            # On redis errors, fallback to allow (fail-open)
            allowed = True

        if not allowed:
            return JSONResponse(status_code=429, content={"detail": "rate limit exceeded"})

        return await call_next(request)

    return middleware
