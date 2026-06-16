from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# ── AUTH ──────────────────────────────────────────────────
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}

class Token(BaseModel):
    access_token: str
    token_type: str


# ── GAMES ─────────────────────────────────────────────────
class GameCreate(BaseModel):
    title: str
    steam_app_id: Optional[str] = None
    nuuvem_slug: Optional[str] = None
    cover_url: Optional[str] = None

class GameOut(BaseModel):
    id: int
    title: str
    steam_app_id: Optional[str] = None
    nuuvem_slug: Optional[str] = None
    cover_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── PRICES ────────────────────────────────────────────────
class PriceSnapshotOut(BaseModel):
    id: int
    store: str
    price: Optional[float] = None
    original_price: Optional[float] = None
    discount_percent: Optional[int] = None
    is_free: bool
    captured_at: datetime

    model_config = {"from_attributes": True}

class GameWithPrices(BaseModel):
    id: int
    title: str
    cover_url: Optional[str] = None
    prices: list[PriceSnapshotOut] = []

    model_config = {"from_attributes": True}


# ── WATCHLIST ─────────────────────────────────────────────
class WatchlistItemCreate(BaseModel):
    game_id: int
    target_price: Optional[float] = None

class WatchlistItemOut(BaseModel):
    id: int
    game_id: int
    target_price: Optional[float] = None
    added_at: datetime
    game: GameOut

    model_config = {"from_attributes": True}


# ── REPORTS ───────────────────────────────────────────────
class PriceHistoryPoint(BaseModel):
    store: str
    price: Optional[float]
    discount_percent: Optional[int]
    captured_at: datetime

    model_config = {"from_attributes": True}

class GameReport(BaseModel):
    game_id: int
    title: str
    lowest_price: Optional[float]
    lowest_price_store: Optional[str]
    current_discount: Optional[int]
    history: list[PriceHistoryPoint]
    