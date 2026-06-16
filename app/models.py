from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    watchlist = relationship("WatchlistItem", back_populates="user", cascade="all, delete")


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    steam_app_id = Column(String, unique=True, nullable=True)
    nuuvem_slug = Column(String, unique=True, nullable=True)
    cover_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    prices = relationship("PriceSnapshot", back_populates="game", cascade="all, delete")
    watchlist_items = relationship("WatchlistItem", back_populates="game", cascade="all, delete")


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    store = Column(String, nullable=False)  # "steam" | "nuuvem"
    price = Column(Float, nullable=True)
    original_price = Column(Float, nullable=True)
    discount_percent = Column(Integer, nullable=True)
    is_free = Column(Boolean, default=False)
    captured_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    game = relationship("Game", back_populates="prices")


class WatchlistItem(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    target_price = Column(Float, nullable=True)
    added_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="watchlist")
    game = relationship("Game", back_populates="watchlist_items")
    