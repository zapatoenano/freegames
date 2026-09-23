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
