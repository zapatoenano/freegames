from datetime import datetime
from sqlalchemy.orm import Session
from .models import Offer


def normalize_offer(raw: dict, store: str) -> dict:
    # Expect raw to contain at least 'title' and optionally 'url','start','end'
    return {
        "title": raw.get("title") or raw.get("name") or "",
        "url": raw.get("url"),
        "store": store,
        "start": parse_dt(raw.get("start")),
        "end": parse_dt(raw.get("end")),
    }


def parse_dt(val):
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    # try ISO formats
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.fromisoformat(val)
        except Exception:
            continue
    return None


def upsert_offers(db: Session, offers: list[dict], store: str):
    """Insert or update offers into DB. Marks active flags appropriately."""
    now = datetime.utcnow()
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
            q.start = o.get("start") or q.start
            q.end = o.get("end") or q.end
            q.active = True
            q.last_seen = now
        else:
            new = Offer(title=o["title"], url=o.get("url"), store=store, start=o.get("start"), end=o.get("end"), active=True)
            db.add(new)
    db.commit()
