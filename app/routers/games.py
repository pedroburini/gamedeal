from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models import Game, PriceSnapshot, User
from app.schemas import GameCreate, GameOut, GameWithPrices
from app.auth import get_current_user
from app.scrapers.steam import get_steam_price
from app.scrapers.nuuvem import get_nuuvem_price
from datetime import datetime, timezone

router = APIRouter(prefix="/games", tags=["games"])


@router.get("/", response_model=list[GameOut])
async def list_games(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Game))
    return result.scalars().all()


@router.post("/", response_model=GameOut, status_code=201)
async def create_game(
    body: GameCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    game = Game(**body.model_dump())
    db.add(game)
    await db.commit()
    await db.refresh(game)
    return game


@router.get("/{game_id}", response_model=GameWithPrices)
async def get_game(game_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Game).options(selectinload(Game.prices)).where(Game.id == game_id)
    )
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Jogo não encontrado")
    return game


@router.delete("/{game_id}", status_code=204)
async def delete_game(
    game_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Jogo não encontrado")
    await db.delete(game)
    await db.commit()


@router.post("/{game_id}/fetch-prices", response_model=GameWithPrices)
async def fetch_prices(
    game_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Game).options(selectinload(Game.prices)).where(Game.id == game_id)
    )
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Jogo não encontrado")

    now = datetime.now(timezone.utc)

    if game.steam_app_id:
        data = await get_steam_price(game.steam_app_id)
        if data:
            if not game.cover_url and data.get("cover_url"):
                game.cover_url = data["cover_url"]
            snapshot = PriceSnapshot(
                game_id=game.id,
                store="steam",
                price=data["price"],
                original_price=data["original_price"],
                discount_percent=data["discount_percent"],
                is_free=data["is_free"],
                captured_at=now
            )
            db.add(snapshot)

    if game.nuuvem_slug:
        data = await get_nuuvem_price(game.nuuvem_slug)
        if data:
            if not game.cover_url and data.get("cover_url"):
                game.cover_url = data["cover_url"]
            snapshot = PriceSnapshot(
                game_id=game.id,
                store="nuuvem",
                price=data["price"],
                original_price=data["original_price"],
                discount_percent=data["discount_percent"],
                is_free=data["is_free"],
                captured_at=now
            )
            db.add(snapshot)

    await db.commit()
    await db.refresh(game)

    result = await db.execute(
        select(Game).options(selectinload(Game.prices)).where(Game.id == game_id)
    )
    return result.scalar_one()


@router.get("/{game_id}/nuuvem-price")
async def fetch_nuuvem_price_on_demand(
    game_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Consulta o preço da Nuuvem em tempo real (sem autenticação).
    Chamado pelo frontend só quando o usuário abre um jogo específico —
    a Nuuvem NÃO é mais consultada automaticamente pelo scheduler."""
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Jogo não encontrado")
    if not game.nuuvem_slug:
        raise HTTPException(status_code=404, detail="Jogo não disponível na Nuuvem")

    data = await get_nuuvem_price(game.nuuvem_slug)
    if not data:
        raise HTTPException(status_code=404, detail="Preço não encontrado na Nuuvem")

    now = datetime.now(timezone.utc)
    if not game.cover_url and data.get("cover_url"):
        game.cover_url = data["cover_url"]
    db.add(PriceSnapshot(
        game_id=game.id,
        store="nuuvem",
        price=data["price"],
        original_price=data["original_price"],
        discount_percent=data["discount_percent"],
        is_free=data["is_free"],
        captured_at=now
    ))
    await db.commit()

    return data
