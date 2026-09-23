import os
import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from .epic import get_free_games_epic as _get_free_games_epic
from .steam import get_free_games_steam as _get_free_games_steam
import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from .epic import get_free_games_epic as _get_free_games_epic
from .steam import get_free_games_steam as _get_free_games_steam
from .cache import ttl_cache
from .db import init_db, SessionLocal
from .service import upsert_offers
from .models import Offer
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import time
from fastapi import Request
import threading
from . import metrics as metrics_mod
from .rate_limit_redis import RedisRateLimiter, make_redis_rate_middleware
import asyncio

app = FastAPI(title="Free Games API")

# basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger('freegames')


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Init DB on startup
init_db()

# Cachear resultados por tienda; TTL configurable vía FREEGAMES_TTL (segundos)
try:
    TTL = int(os.getenv("FREEGAMES_TTL", "300"))
except Exception:
    TTL = 300


@ttl_cache(TTL)
def cached_epic():
    return _get_free_games_epic()


@ttl_cache(TTL)
def cached_steam():
    return _get_free_games_steam()


# Rate limiting config
try:
    RATE_LIMIT_PER_MIN = int(os.getenv("FREEGAMES_RATE_LIMIT_PER_MIN", "60"))
except Exception:
    RATE_LIMIT_PER_MIN = 60

RATE_LIMIT_ENABLED = os.getenv("FREEGAMES_RATE_LIMIT_ENABLED", "true").lower() in ("1", "true", "yes")

# in-memory store: ip -> (count, window_start_ts)
_rate_store: dict = {}
_rate_lock = threading.Lock()

# Redis rate-limiter (optional)
REDIS_URL = os.getenv("FREEGAMES_RATE_LIMIT_REDIS_URL")
_redis_limiter: RedisRateLimiter | None = None

async def _init_redis_limiter():
    global _redis_limiter
    if REDIS_URL:
        try:
            _redis_limiter = RedisRateLimiter(REDIS_URL, per_min=RATE_LIMIT_PER_MIN)
            await _redis_limiter.init()
            # mount redis middleware at the top if enabled
            app.middleware_stack = None
            app.add_middleware = app.add_middleware
            app.middleware("http")(_redis_middleware)
        except Exception:
            logger.exception("Failed to init Redis rate limiter, falling back to in-memory")


async def _redis_middleware(request, call_next):
    # this wrapper ensures limiter is initialized
    global _redis_limiter
    if _redis_limiter is None:
        return await call_next(request)
    mw = make_redis_rate_middleware(_redis_limiter)
    return await mw(request, call_next)


@app.on_event("startup")
async def _startup_redis():
    await _init_redis_limiter()


@app.on_event("shutdown")
async def _shutdown_redis():
    if _redis_limiter is not None:
        await _redis_limiter.close()


@app.middleware("http")
async def metrics_and_rate_middleware(request: Request, call_next):
    start = time.time()
    client_ip = request.client.host if request.client else "unknown"

    # rate limiting (fixed window per minute)
    if RATE_LIMIT_ENABLED:
        now = int(time.time())
        window = now // 60
        with _rate_lock:
            entry = _rate_store.get(client_ip)
            if not entry or entry[0] != window:
                # reset: store as (window, count)
                _rate_store[client_ip] = (window, 1)
            else:
                w, cnt = entry
                if cnt >= RATE_LIMIT_PER_MIN:
                    # too many requests
                    duration = time.time() - start
                    metrics_mod.observe_request(request.url.path, request.method, 429, duration)
                    return JSONResponse(status_code=429, content={"detail": "rate limit exceeded"})
                else:
                    _rate_store[client_ip] = (w, cnt + 1)

    # process request
    try:
        response = await call_next(request)
    except Exception as e:
        duration = time.time() - start
        metrics_mod.observe_request(request.url.path, request.method, 500, duration)
        raise

    duration = time.time() - start
    try:
        metrics_mod.observe_request(request.url.path, request.method, response.status_code, duration)
    except Exception:
        pass
    return response


@app.get("/metrics")
def metrics_endpoint():
    return metrics_mod.metrics_response()


@app.get("/free-now")
def free_now(db: Session = Depends(get_db)):
    """Devuelve los juegos gratis actualmente en Epic y Steam (usa DB y cache)."""
    epic = cached_epic()
    steam = cached_steam()
    # Upsert into DB asynchronously via scheduler job, but provide immediate response
    try:
        upsert_offers(db, epic, "epic")
        upsert_offers(db, steam, "steam")
    except Exception as e:
        # don't block the response if DB fails
        logger.exception("upsert_offers failed: %s", e)
    return JSONResponse(content={"epic": epic, "steam": steam})


@app.get("/free-now/epic")
def free_now_epic(db: Session = Depends(get_db)):
    data = cached_epic()
    try:
        upsert_offers(db, data, "epic")
    except Exception as e:
        logger.exception("upsert epic failed: %s", e)
    return JSONResponse(content={"epic": data})


@app.get("/free-now/steam")
def free_now_steam(db: Session = Depends(get_db)):
    data = cached_steam()
    try:
        upsert_offers(db, data, "steam")
    except Exception as e:
        logger.exception("upsert steam failed: %s", e)
    return JSONResponse(content={"steam": data})


@app.get("/offers")
def list_offers(active: bool = True, db: Session = Depends(get_db)):
    q = db.query(Offer).filter(Offer.active == active).all()
    out = []
    for o in q:
        out.append({
            "id": o.id,
            "title": o.title,
            "url": o.url,
            "store": o.store,
            "image": o.image,
            "description": o.description,
            "genre": o.genre,
            "start": o.start.isoformat() if o.start else None,
            "end": o.end.isoformat() if o.end else None,
            "active": o.active,
        })
    return out


@app.get("/health")
def health():
    return {"status": "ok"}


# Background scheduled fetch to keep DB up to date
FETCH_MINUTES = int(os.getenv("FREEGAMES_FETCH_MINUTES", "15"))


def scheduled_fetch():
    db = SessionLocal()
    try:
        epic = cached_epic()
        steam = cached_steam()
        logger.info("Scheduled fetch: epic=%d steam=%d", len(epic) if isinstance(epic, list) else 0, len(steam) if isinstance(steam, list) else 0)
        upsert_offers(db, epic, "epic")
        upsert_offers(db, steam, "steam")
    except Exception:
        logger.exception("scheduled_fetch failed")
    finally:
        db.close()


scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_fetch, "interval", minutes=FETCH_MINUTES)
scheduler.start()
# Shutdown hook
atexit.register(lambda: scheduler.shutdown(wait=False))

# expose app metadata for runtime checks
app.state.rate_limit_enabled = RATE_LIMIT_ENABLED
app.state.rate_limit_per_min = RATE_LIMIT_PER_MIN
