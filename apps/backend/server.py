from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lib.database import init_db, close_db
from routes.register import router as register_router
from routes.balance import router as balance_router
from routes.trade import router as trade_router
from routes.markets import router as markets_router
from routes.agents import router as agents_router
from routes.deposit import router as deposit_router
from routes.export_key import router as export_key_router
from routes.oauth import router as oauth_router
from routes.device import router as device_router
from routes.stats import router as stats_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB pool + schema. Shutdown: close pool."""
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="EigenPoly Backend",
    version="0.2.0",
    description="Multi-agent trading backend for Polymarket — TEE-secured with Google OAuth",
    lifespan=lifespan,
)

# CORS — allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount route modules
app.include_router(register_router, tags=["Registration"])
app.include_router(balance_router, tags=["Balance"])
app.include_router(trade_router, tags=["Trading"])
app.include_router(markets_router, tags=["Markets"])
app.include_router(agents_router, tags=["Agents"])
app.include_router(deposit_router)
app.include_router(export_key_router, tags=["Wallet"])
app.include_router(oauth_router)
app.include_router(device_router)
app.include_router(stats_router, tags=["Stats"])


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "eigenpoly-backend", "version": "0.2.0"}
