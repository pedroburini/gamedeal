from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Game, PriceSnapshot
from app.scrapers.steam import get_steam_price
from app.scrapers.nuuvem import get_nuuvem_price
from app.scrapers.catalog import fetch_on_sale, fetch_top_sellers
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def sync_catalog():
    """Busca jogos em promoção + top sellers e cadastra os novos no banco."""
    logger.info("Scheduler: sincronizando catálogo...")

    on_sale = await fetch_on_sale(count=200)
    top = await fetch_top_sellers(count=50)

    # Merge sem duplicatas por steam_app_id
    seen = set()
    games = []
    for g in on_sale + top:
        if g["steam_app_id"] not in seen:
            seen.add(g["steam_app_id"])
            games.append(g)

    if not games:
        logger.warning("Scheduler: nenhum jogo retornado do catálogo.")
        return

    async with AsyncSessionLocal() as db:
        added = 0
        for g in games:
            result = await db.execute(
                select(Game).where(Game.steam_app_id == g["steam_app_id"])
            )
            if result.scalar_one_or_none():
                continue
            db.add(Game(
                title=g["title"],
                steam_app_id=g["steam_app_id"],
                nuuvem_slug=g["nuuvem_slug"]
            ))
            added += 1
        await db.commit()

    logger.info(f"Scheduler: {added} jogos novos adicionados ({len(games)} processados).")


async def fetch_all_prices():
    """Coleta preços de todos os jogos cadastrados."""
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
    logger.info("Scheduler: coleta de preços concluída.")


async def run_full_sync():
    await sync_catalog()
    await fetch_all_prices()


def start_scheduler():
    scheduler.add_job(run_full_sync, "interval", hours=6, id="full_sync")
    scheduler.start()
    logger.info("Scheduler iniciado — sincronização a cada 6 horas.")
