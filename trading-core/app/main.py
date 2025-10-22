from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional, List
import logging

from app.models import GridSignal, OrderRequest, Position, PnLMetrics
from app.database import db
from app.aster_client import aster_client
from app.grid_engine import grid_engine
from app.llm_clients import llm_clients
from pydantic import BaseModel
from datetime import datetime
import json

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


@app.post("/models/init")
async def init_models(initial_balance: float = 1000.0):
    try:
        models = ["chatgpt", "grok", "claude", "deepseek"]
        for model in models:
            db.init_model_account(model, initial_balance)
        return {"status": "ok", "message": f"Initialized {len(models)} model accounts with ${initial_balance} each"}
    except Exception as e:
        logger.error(f"Error initializing models: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models/accounts")
async def get_model_accounts():
    try:
        accounts = db.get_all_model_accounts()
        return {"accounts": accounts}
    except Exception as e:
        logger.error(f"Error fetching model accounts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models/{model}/account")
async def get_model_account(model: str):
    try:
        account = db.get_model_account(model)
        if not account:
            raise HTTPException(status_code=404, detail=f"Model account not found: {model}")
        return account
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching model account: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/llm/decision")
async def get_llm_decision(model: str, symbol: str = "SOLUSDT"):
    try:
        if model not in llm_clients:
            raise HTTPException(status_code=400, detail=f"Invalid model: {model}")
        
        client = llm_clients[model]
        
        account = db.get_model_account(model)
        if not account:
            raise HTTPException(status_code=404, detail=f"Model account not found: {model}")
        
        price_history = db.get_price_history(symbol, hours=1)
        latest_price = db.get_latest_price(symbol)
        current_price = latest_price['price'] if latest_price else 200.0
        
        positions = db.get_positions(model=model)
        position = positions[0] if positions else None
        
        market_data = {
            "symbol": symbol,
            "current_price": float(current_price),
            "price_history": [{"price": float(p['price']), "timestamp": str(p['timestamp'])} for p in price_history],
            "position": position,
            "account": {
                "current_balance": float(account['current_balance']),
                "total_pnl": float(account['total_pnl']),
                "total_trades": account['total_trades'],
                "winning_trades": account['winning_trades']
            }
        }
        
        decision = await client.get_trading_decision(market_data)
        
        decision_id = db.insert_llm_decision({
            "model": model,
            "symbol": symbol,
            "decision_type": "trading",
            "action": decision.get("action", "HOLD"),
            "reasoning": decision.get("reasoning", ""),
            "market_data": json.dumps(market_data),
            "decision_data": json.dumps(decision),
            "executed": False
        })
        
        return {
            "decision_id": decision_id,
            "model": model,
            "decision": decision,
            "market_data": market_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting LLM decision: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/llm/decisions")
async def get_llm_decisions(model: Optional[str] = None, limit: int = 50):
    try:
        decisions = db.get_recent_decisions(model=model, limit=limit)
        for decision in decisions:
            if decision.get('market_data') and isinstance(decision['market_data'], str):
                decision['market_data'] = json.loads(decision['market_data'])
            if decision.get('decision_data') and isinstance(decision['decision_data'], str):
                decision['decision_data'] = json.loads(decision['decision_data'])
        return {"decisions": decisions}
    except Exception as e:
        logger.error(f"Error fetching LLM decisions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/price/update")
async def update_price(symbol: str, price: float, volume: Optional[float] = None):
    try:
        db.insert_price(symbol, price, volume)
        return {"status": "ok", "symbol": symbol, "price": price}
    except Exception as e:
        logger.error(f"Error updating price: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/price/history")
async def get_price_history_endpoint(symbol: str, hours: int = 1):
    try:
        history = db.get_price_history(symbol, hours)
        return {"symbol": symbol, "history": history}
    except Exception as e:
        logger.error(f"Error fetching price history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/price/latest")
async def get_latest_price_endpoint(symbol: str):
    try:
        price = db.get_latest_price(symbol)
        if not price:
            raise HTTPException(status_code=404, detail=f"No price data found for {symbol}")
        return price
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching latest price: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models/positions")
async def get_all_positions(model: Optional[str] = None):
    try:
        positions = db.get_positions(model=model)
        return {"positions": positions}
    except Exception as e:
        logger.error(f"Error fetching positions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dashboard/stats")
async def get_dashboard_stats():
    try:
        accounts = db.get_all_model_accounts()
        
        latest_prices = {}
        for symbol in ["SOLUSDT", "BTCUSDT", "ETHUSDT"]:
            price = db.get_latest_price(symbol)
            if price:
                latest_prices[symbol] = float(price['price'])
        
        recent_decisions = db.get_recent_decisions(limit=20)
        for decision in recent_decisions:
            if decision.get('decision_data') and isinstance(decision['decision_data'], str):
                decision['decision_data'] = json.loads(decision['decision_data'])
        
        all_positions = db.get_positions()
        
        return {
            "accounts": accounts,
            "prices": latest_prices,
            "recent_decisions": recent_decisions,
            "positions": all_positions,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
