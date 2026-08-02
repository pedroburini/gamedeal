from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Response
from contextlib import asynccontextmanager
from app.database import engine, Base
from app.routers import users, games, prices
from app.scheduler import start_scheduler, run_full_sync
import asyncio
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    start_scheduler()
    asyncio.create_task(run_full_sync())
    yield


app = FastAPI(
    title="GameDeal API",
    description="Monitoramento de preços de jogos — Steam e Nuuvem",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.head("/")
async def head_root():
    return Response(status_code=200)

app.include_router(users.router, prefix="/api")
app.include_router(games.router, prefix="/api")
app.include_router(prices.router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "GameDeal API — acesse /docs para a documentação"}
