from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import AsyncSessionLocal
from app.models import Game, PriceSnapshot
from app.scrapers.steam import get_steam_price
from app.scrapers.nuuvem import get_nuuvem_price
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def fetch_all_prices():
    logger.info("Scheduler: iniciando coleta de preços...")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Game))
        games = result.scalars().all()

        now = datetime.now(timezone.utc)

        for game in games:
            if game.steam_app_id:
                data = await get_steam_price(game.steam_app_id)
                if data:
                    if not game.cover_url and data.get("cover_url"):
                        game.cover_url = data["cover_url"]
                    db.add(PriceSnapshot(
                        game_id=game.id,
                        store="steam",
                        price=data["price"],
                        original_price=data["original_price"],
                        discount_percent=data["discount_percent"],
                        is_free=data["is_free"],
                        captured_at=now
                    ))

            if game.nuuvem_slug:
                data = await get_nuuvem_price(game.nuuvem_slug)
                if data:
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
    logger.info("Scheduler: coleta concluída.")


def start_scheduler():
    scheduler.add_job(fetch_all_prices, "interval", hours=6, id="fetch_prices")
    scheduler.start()
    logger.info("Scheduler iniciado — coleta a cada 6 horas.")
    