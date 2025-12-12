"""REST API server for live execution operations."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.live.database import init_pool, close_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage database pool lifecycle."""
    # Startup: Initialize database pool
    await init_pool()
    yield
    # Shutdown: Close database pool
    await close_pool()


app = FastAPI(
    title="Odum Trader Live Execution API",
    lifespan=lifespan
)

# CORS middleware (same as backtest API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "live-execution"}

