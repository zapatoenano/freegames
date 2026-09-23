from datetime import datetime, timezone
from sqlalchemy.orm import Session
from .models import Offer
from typing import Optional


def normalize_offer(raw: dict, store: str) -> dict:
    # Expect raw to contain at least 'title' and optionally 'url','start','end'
    return {
        "title": raw.get("title") or raw.get("name") or "",
        "url": raw.get("url"),
        "image": raw.get("image") or raw.get("image_url") or None,
        "description": raw.get("description") or raw.get("desc") or None,
        "genre": raw.get("genre") or None,
        "store": store,
        "start": parse_dt(raw.get("start")),
        "end": parse_dt(raw.get("end")),
    }


def parse_dt(val):
    if not val:
        return None
    if isinstance(val, datetime):
        # ensure timezone-aware UTC
        return val if val.tzinfo is not None else val.replace(tzinfo=timezone.utc)
    # try ISO formats
    try:
        dt = datetime.fromisoformat(val)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        # fallback parsing
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(val, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                continue
    return None


def upsert_offers(db: Session, offers: list[dict], store: str):
    """Insert or update offers into DB. Marks active flags appropriately."""
    now = datetime.now(timezone.utc)
    # Normalize and upsert
    incoming = []
    for raw in offers:
        o = normalize_offer(raw, store)
        incoming.append(o)

    # Mark all existing offers from this store inactive; we'll re-activate matched ones
    existing = db.query(Offer).filter(Offer.store == store).all()
    for e in existing:
        e.active = False
    db.flush()

    for o in incoming:
        q = db.query(Offer).filter(Offer.title == o["title"], Offer.store == store).first()
        if q:
            q.url = o.get("url") or q.url
            q.image = o.get("image") or q.image
            q.description = o.get("description") or q.description
            q.genre = o.get("genre") or q.genre
            q.start = o.get("start") or q.start
            q.end = o.get("end") or q.end
            q.active = True
            q.last_seen = now
        else:
            new = Offer(
                title=o["title"],
                url=o.get("url"),
                image=o.get("image"),
                description=o.get("description"),
                genre=o.get("genre"),
                store=store,
                start=o.get("start"),
                end=o.get("end"),
                active=True,
            )
            db.add(new)
    db.commit()
