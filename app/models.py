from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from .db import Base


class Offer(Base):
    __tablename__ = "offers"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(512), nullable=False)
    url = Column(Text, nullable=True)
    image = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    genre = Column(String(200), nullable=True)
    store = Column(String(50), nullable=False)
    start = Column(DateTime(timezone=True), nullable=True)
    end = Column(DateTime(timezone=True), nullable=True)
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), onupdate=func.now())
    active = Column(Boolean, default=True, nullable=False)
