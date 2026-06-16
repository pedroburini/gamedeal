from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Game, PriceSnapshot, WatchlistItem
from app.schemas import GameReport, PriceHistoryPoint, WatchlistItemCreate, WatchlistItemOut
from app.auth import get_current_user
from app.models import User
from sqlalchemy.orm import selectinload

router = APIRouter(tags=["prices"])


# ── RELATÓRIO DE PREÇOS ───────────────────────────────────
@router.get("/games/{game_id}/report", response_model=GameReport)
async def game_report(game_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Game).options(selectinload(Game.prices)).where(Game.id == game_id)
    )
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Jogo não encontrado")

    snapshots = sorted(game.prices, key=lambda x: x.captured_at, reverse=True)

    lowest = min((s for s in snapshots if s.price is not None), key=lambda x: x.price, default=None)

    current = snapshots[0] if snapshots else None

    history = [
        PriceHistoryPoint(
            store=s.store,
            price=s.price,
            discount_percent=s.discount_percent,
            captured_at=s.captured_at
        )
        for s in snapshots[:50]
    ]

    return GameReport(
        game_id=game.id,
        title=game.title,
        lowest_price=lowest.price if lowest else None,
        lowest_price_store=lowest.store if lowest else None,
        current_discount=current.discount_percent if current else None,
        history=history
    )


# ── PROMOÇÕES ATIVAS ──────────────────────────────────────
@router.get("/deals", response_model=list[dict])
async def active_deals(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PriceSnapshot)
        .options(selectinload(PriceSnapshot.game))
        .where(PriceSnapshot.discount_percent > 0)
        .order_by(PriceSnapshot.captured_at.desc())
    )
    snapshots = result.scalars().all()

    seen = set()
    deals = []
    for s in snapshots:
        key = (s.game_id, s.store)
        if key in seen:
            continue
        seen.add(key)
        deals.append({
            "game_id": s.game_id,
            "title": s.game.title,
            "cover_url": s.game.cover_url,
            "store": s.store,
            "price": s.price,
            "original_price": s.original_price,
            "discount_percent": s.discount_percent,
            "captured_at": s.captured_at.isoformat()
        })

    return deals


# ── WATCHLIST ─────────────────────────────────────────────
@router.get("/watchlist", response_model=list[WatchlistItemOut])
async def get_watchlist(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(WatchlistItem)
        .options(selectinload(WatchlistItem.game))
        .where(WatchlistItem.user_id == current_user.id)
    )
    return result.scalars().all()


@router.post("/watchlist", response_model=WatchlistItemOut, status_code=201)
async def add_to_watchlist(
    body: WatchlistItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Game).where(Game.id == body.game_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Jogo não encontrado")

    item = WatchlistItem(
        user_id=current_user.id,
        game_id=body.game_id,
        target_price=body.target_price
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    result = await db.execute(
        select(WatchlistItem)
        .options(selectinload(WatchlistItem.game))
        .where(WatchlistItem.id == item.id)
    )
    return result.scalar_one()


@router.delete("/watchlist/{item_id}", status_code=204)
async def remove_from_watchlist(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.id == item_id,
            WatchlistItem.user_id == current_user.id
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    await db.delete(item)
    await db.commit()
    