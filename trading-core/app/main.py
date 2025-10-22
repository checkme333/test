from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional, List
import logging

from app.models import GridSignal, OrderRequest, Position, PnLMetrics
from app.database import db
from app.aster_client import aster_client
from app.grid_engine import grid_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database schema...")
    db.init_schema()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down...")
    await aster_client.close()


app = FastAPI(lifespan=lifespan)

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/grid/apply")
async def apply_grid(signal: GridSignal):
    try:
        result = await grid_engine.apply_grid(signal)
        return result
    except Exception as e:
        logger.error(f"Error applying grid: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/order")
async def place_order(order: OrderRequest):
    try:
        result = await aster_client.place_order(order)
        return result
    except Exception as e:
        logger.error(f"Error placing order: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/positions")
async def get_positions(symbol: Optional[str] = None):
    try:
        positions = await aster_client.get_position(symbol)
        return {"positions": positions}
    except Exception as e:
        logger.error(f"Error fetching positions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/orders")
async def get_orders(
    model: Optional[str] = Query(None),
    symbol: Optional[str] = Query(None)
):
    try:
        orders = db.get_orders(model=model, symbol=symbol)
        return {"orders": orders}
    except Exception as e:
        logger.error(f"Error fetching orders: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/pnl")
async def get_pnl(
    model: Optional[str] = Query(None),
    window: str = Query("all", regex="^(daily|weekly|all)$")
):
    try:
        metrics = db.get_metrics(model=model, window=window)
        return {"metrics": metrics}
    except Exception as e:
        logger.error(f"Error fetching PnL: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/grid/status")
async def get_grid_status(model: str, symbol: str):
    try:
        config = db.get_grid_config(model, symbol)
        if not config:
            raise HTTPException(status_code=404, detail="Grid config not found")
        
        levels = db.get_grid_levels(config['id'])
        
        return {
            "config": config,
            "levels": levels
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching grid status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/grid/pause")
async def pause_grid(model: str, symbol: str):
    try:
        db.update_grid_status(model, symbol, "paused")
        return {"status": "ok", "message": f"Grid paused for {model}/{symbol}"}
    except Exception as e:
        logger.error(f"Error pausing grid: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/grid/resume")
async def resume_grid(model: str, symbol: str):
    try:
        db.update_grid_status(model, symbol, "active")
        return {"status": "ok", "message": f"Grid resumed for {model}/{symbol}"}
    except Exception as e:
        logger.error(f"Error resuming grid: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/account")
async def get_account():
    try:
        account = await aster_client.get_account()
        return account
    except Exception as e:
        logger.error(f"Error fetching account: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/balance")
async def get_balance():
    try:
        balance = await aster_client.get_balance()
        return {"balance": balance}
    except Exception as e:
        logger.error(f"Error fetching balance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
