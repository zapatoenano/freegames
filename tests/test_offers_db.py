import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Offer
from app.service import upsert_offers


def test_upsert_offers(tmp_path):
    db_file = tmp_path / "test.db"
    url = f"sqlite:///{db_file}"
    engine = create_engine(url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    offers = [{"title": "Free Game A", "url": "https://epic/a", "start": None, "end": None}]
    upsert_offers(db, offers, "epic")
    q = db.query(Offer).filter(Offer.store == "epic").all()
    assert len(q) == 1
    assert q[0].title == "Free Game A"
