from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Game, PriceSnapshot
from app.scrapers.steam import get_steam_price
from app.scrapers.nuuvem import get_nuuvem_price
from app.scrapers.catalog import fetch_top_sellers
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def sync_catalog():
    """Busca top sellers da Steam e cadastra jogos novos no banco."""
    logger.info("Scheduler: sincronizando catálogo...")
    games = await fetch_top_sellers(count=50)
    if not games:
        logger.warning("Scheduler: nenhum jogo retornado do catálogo.")
        return

    async with AsyncSessionLocal() as db:
        for g in games:
            result = await db.execute(
                select(Game).where(Game.steam_app_id == g["steam_app_id"])
            )
            if result.scalar_one_or_none():
                continue  # já existe
            new_game = Game(
                title=g["title"],
                steam_app_id=g["steam_app_id"],
                nuuvem_slug=g["nuuvem_slug"]
            )
            db.add(new_game)
        await db.commit()

    logger.info(f"Scheduler: catálogo sincronizado — {len(games)} jogos processados.")


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
    """Sincroniza catálogo e coleta preços em sequência."""
    await sync_catalog()
    await fetch_all_prices()


def start_scheduler():
    # Sincroniza catálogo + preços a cada 6 horas
    scheduler.add_job(run_full_sync, "interval", hours=6, id="full_sync")
    # Roda imediatamente na inicialização
    scheduler.add_job(run_full_sync, "date", id="full_sync_startup")
    scheduler.start()
    logger.info("Scheduler iniciado — sincronização a cada 6 horas.")
