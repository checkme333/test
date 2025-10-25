from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional, List
import logging

from app.models import GridSignal, OrderRequest, Position, PnLMetrics, PnLSnapshot
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
        from app.aster_client import get_model_aster_client
        
        if order.model:
            client = get_model_aster_client(order.model)
            logger.info(f"Using {order.model} Aster client for order")
        else:
            client = aster_client
            logger.info("Using default Aster client for order")
        
        result = await client.place_order(order)
        
        if result and result.get('orderId'):
            db.insert_order({
                'model': order.model or 'default',
                'symbol': order.symbol,
                'client_order_id': order.client_order_id or f"order_{result['orderId']}",
                'exchange_order_id': str(result['orderId']),
                'side': order.side.value,
                'price': float(order.price) if order.price else 0,
                'qty': float(order.qty),
                'fill_qty': 0,
                'status': 'NEW',
                'fee': 0,
                'pnl': 0
            })
            logger.info(f"Recorded order {result['orderId']} to database")
        
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
        models = ["chatgpt", "grok", "gemini", "deepseek"]
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
    import time
    request_timestamp = time.time()
    try:
        from app.market_analysis import analyze_market_data, get_order_book_depth
        from app.aster_client import get_model_aster_client
        
        logger.info(f"Getting LLM decision for model={model}, symbol={symbol}")
        
        if model not in llm_clients:
            raise HTTPException(status_code=400, detail=f"Invalid model: {model}")
        
        if model == "grok":
            from app.llm_clients import GrokClient
            client = GrokClient()
            logger.info(f"Created fresh Grok client: has_key={bool(client.api_key)}, mock_mode={client.mock_mode}")
        else:
            client = llm_clients[model]
        
        logger.info(f"Got client: {type(client).__name__}")
        
        account = db.get_model_account(model)
        if not account:
            raise HTTPException(status_code=404, detail=f"Model account not found: {model}")
        
        price_history = db.get_price_history(symbol, hours=1)
        latest_price = db.get_latest_price(symbol)
        current_price = latest_price['price'] if latest_price else 200.0
        
        positions = db.get_positions(model=model)
        position = positions[0] if positions else None
        
        technical_analysis = analyze_market_data(price_history, symbol)
        
        aster_client_model = get_model_aster_client(model)
        order_book = await get_order_book_depth(aster_client_model, symbol)
        
        market_data = {
            "symbol": symbol,
            "current_price": float(current_price),
            "price_history": [{"price": float(p['price']), "timestamp": str(p['timestamp'])} for p in price_history[-30:]],
            "position": position,
            "account": {
                "current_balance": float(account['current_balance']),
                "total_pnl": float(account['total_pnl']),
                "total_trades": account['total_trades'],
                "winning_trades": account['winning_trades']
            },
            "technical_indicators": technical_analysis,
            "order_book": order_book
        }
        
        logger.info(f"Calling {model} client.get_trading_decision...")
        decision = await client.get_trading_decision(market_data)
        logger.info(f"Got decision from {model}: {decision.get('action', 'UNKNOWN')}")
        
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
        
        response = {
            "decision_id": decision_id,
            "model": model,
            "decision": decision,
            "market_data": market_data,
            "request_timestamp": request_timestamp,
            "code_version": "2025-10-23-v2"
        }
        
        if model == "grok":
            import os
            response["debug"] = {
                "client_has_api_key": bool(client.api_key),
                "client_api_key_prefix": client.api_key[:20] if client.api_key else "NONE",
                "client_mock_mode": client.mock_mode,
                "client_base_url": client.base_url,
                "env_xai_key_exists": bool(os.getenv("XAI_API_KEY")),
                "env_xai_key_prefix": os.getenv("XAI_API_KEY", "")[:20]
            }
        
        return response
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


@app.post("/llm/execute-decision")
async def execute_llm_decision(model: str, symbol: str):
    """Get AI decision and execute it immediately"""
    try:
        from app.order_executor import execute_trading_decision
        
        decision_response = await get_llm_decision(model, symbol)
        decision = decision_response['decision']
        decision_id = decision_response['decision_id']
        
        execution_result = await execute_trading_decision(model, symbol, decision, decision_id)
        
        return {
            "model": model,
            "symbol": symbol,
            "decision": decision,
            "execution": execution_result
        }
    except Exception as e:
        logger.error(f"Error executing LLM decision: {str(e)}")
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


@app.post("/prices/sync")
async def sync_prices():
    """Fetch latest prices from Aster API and update database"""
    try:
        symbols = ["SOLUSDT", "BTCUSDT", "ETHUSDT", "BNBUSDT", "ASTERUSDT"]
        synced = []
        errors = []
        
        for symbol in symbols:
            try:
                ticker = await aster_client.get_ticker(symbol)
                if ticker and 'lastPrice' in ticker:
                    price = float(ticker['lastPrice'])
                    volume = float(ticker.get('volume', 0))
                    db.insert_price(symbol, price, volume)
                    synced.append({
                        "symbol": symbol,
                        "price": price
                    })
                else:
                    errors.append({
                        "symbol": symbol,
                        "error": "Price not found in ticker data"
                    })
            except Exception as e:
                logger.error(f"Error fetching price for {symbol}: {str(e)}")
                errors.append({
                    "symbol": symbol,
                    "error": str(e)
                })
        
        return {
            "status": "ok",
            "synced": synced,
            "errors": errors
        }
    except Exception as e:
        logger.error(f"Error syncing prices: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/models/sync-balances")
async def sync_model_balances():
    """Sync balances from Aster API for each model"""
    try:
        from app.aster_client import get_model_aster_client
        
        models = ["chatgpt", "grok", "gemini", "deepseek"]
        synced = []
        errors = []
        
        for model in models:
            try:
                client = get_model_aster_client(model)
                balance_data = await client.get_balance()
                
                usdt_balance = next((b for b in balance_data if b.get('asset') == 'USDT'), None)
                if usdt_balance:
                    available_balance = float(usdt_balance.get('availableBalance', 0))
                    
                    account = db.get_model_account(model)
                    if account:
                        initial_balance = float(account['initial_balance'])
                        pnl = available_balance - initial_balance
                    else:
                        pnl = 0
                    
                    db.update_model_balance(model, available_balance, pnl)
                    synced.append({
                        "model": model,
                        "balance": available_balance,
                        "pnl": pnl
                    })
                else:
                    errors.append({
                        "model": model,
                        "error": "USDT balance not found"
                    })
            except Exception as e:
                logger.error(f"Error syncing balance for {model}: {str(e)}")
                errors.append({
                    "model": model,
                    "error": str(e)
                })
        
        return {
            "status": "ok",
            "synced": synced,
            "errors": errors
        }
    except Exception as e:
        logger.error(f"Error syncing model balances: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/models/sync-positions")
async def sync_model_positions():
    """Sync positions from Aster API for each model"""
    try:
        from app.aster_client import get_model_aster_client
        
        models = ["chatgpt", "grok", "gemini", "deepseek"]
        synced = []
        errors = []
        
        db.execute_query("DELETE FROM positions")
        
        for model in models:
            try:
                client = get_model_aster_client(model)
                positions_data = await client.get_position()
                
                for pos in positions_data:
                    position_amt = float(pos.get('positionAmt', 0))
                    if position_amt != 0:
                        symbol = pos.get('symbol')
                        side = 'LONG' if position_amt > 0 else 'SHORT'
                        size = abs(position_amt)
                        entry_price = float(pos.get('entryPrice', 0))
                        mark_price = float(pos.get('markPrice', 0))
                        unrealized_pnl = float(pos.get('unRealizedProfit', 0))
                        leverage = int(pos.get('leverage', 1))
                        
                        db.execute_query("""
                            INSERT INTO positions (model, symbol, side, size, entry_price, current_price, unrealized_pnl, leverage)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (model, symbol) DO UPDATE SET
                                side = EXCLUDED.side,
                                size = EXCLUDED.size,
                                entry_price = EXCLUDED.entry_price,
                                current_price = EXCLUDED.current_price,
                                unrealized_pnl = EXCLUDED.unrealized_pnl,
                                leverage = EXCLUDED.leverage,
                                updated_at = NOW()
                        """, (model, symbol, side, size, entry_price, mark_price, unrealized_pnl, leverage))
                        
                        synced.append({
                            "model": model,
                            "symbol": symbol,
                            "side": side,
                            "size": size,
                            "unrealized_pnl": unrealized_pnl
                        })
            except Exception as e:
                logger.error(f"Error syncing positions for {model}: {str(e)}")
                errors.append({
                    "model": model,
                    "error": str(e)
                })
        
        return {
            "status": "ok",
            "synced": synced,
            "errors": errors
        }
    except Exception as e:
        logger.error(f"Error syncing model positions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/models/sync-trades")
async def sync_model_trades():
    """Sync trade history from Aster API for each model and calculate statistics"""
    try:
        from app.aster_client import get_model_aster_client
        
        models = ["chatgpt", "grok", "gemini", "deepseek"]
        synced = []
        errors = []
        
        for model in models:
            try:
                client = get_model_aster_client(model)
                account = db.get_model_account(model)
                if not account:
                    continue
                
                symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ASTERUSDT", "SOLUSDT"]
                all_trades = []
                
                for symbol in symbols:
                    try:
                        trades = await client.get_all_orders(symbol, limit=100)
                        for trade in trades:
                            if trade.get('status') == 'FILLED':
                                all_trades.append(trade)
                    except Exception as e:
                        logger.warning(f"Error fetching trades for {model} {symbol}: {str(e)}")
                
                winning_trades = 0
                losing_trades = 0
                total_pnl = 0
                max_drawdown = 0
                peak_balance = float(account['initial_balance'])
                
                for trade in all_trades:
                    realized_pnl = float(trade.get('realizedPnl', 0))
                    total_pnl += realized_pnl
                    
                    if realized_pnl > 0:
                        winning_trades += 1
                    elif realized_pnl < 0:
                        losing_trades += 1
                    
                    current_balance = float(account['initial_balance']) + total_pnl
                    if current_balance > peak_balance:
                        peak_balance = current_balance
                    
                    drawdown = (peak_balance - current_balance) / peak_balance * 100
                    if drawdown > max_drawdown:
                        max_drawdown = drawdown
                
                total_trades = winning_trades + losing_trades
                
                with db.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            UPDATE model_accounts 
                            SET total_trades = %s, 
                                winning_trades = %s, 
                                losing_trades = %s,
                                max_drawdown = %s,
                                updated_at = NOW()
                            WHERE model = %s
                        """, (total_trades, winning_trades, losing_trades, max_drawdown, model))
                        conn.commit()
                
                synced.append({
                    "model": model,
                    "total_trades": total_trades,
                    "winning_trades": winning_trades,
                    "losing_trades": losing_trades,
                    "max_drawdown": max_drawdown
                })
            except Exception as e:
                logger.error(f"Error syncing trades for {model}: {str(e)}")
                errors.append({
                    "model": model,
                    "error": str(e)
                })
        
        return {
            "status": "ok",
            "synced": synced,
            "errors": errors
        }
    except Exception as e:
        logger.error(f"Error syncing model trades: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dashboard/stats")
async def get_dashboard_stats():
    try:
        from app.aster_client import get_model_aster_client
        
        accounts = db.get_all_model_accounts()
        
        models = ["chatgpt", "grok", "gemini", "deepseek"]
        for account in accounts:
            model = account['model']
            if model in models:
                try:
                    client = get_model_aster_client(model)
                    
                    account_info = await client.get_account()
                    available_balance = float(account_info.get('availableBalance', 0))
                    total_position_margin = float(account_info.get('totalPositionInitialMargin', 0))
                    total_unrealized_pnl = float(account_info.get('totalUnrealizedProfit', 0))
                    
                    positions_data = await client.get_position()
                    
                    total_position_value = 0
                    for pos in positions_data:
                        position_amt = float(pos.get('positionAmt', 0))
                        if position_amt != 0:
                            mark_price = float(pos.get('markPrice', 0))
                            total_position_value += abs(position_amt) * mark_price
                    
                    total_equity = available_balance + total_position_margin + total_unrealized_pnl
                    
                    total_pnl = total_equity - float(account['initial_balance'])
                    
                    account['current_balance'] = available_balance
                    account['total_position_value'] = total_position_value
                    account['total_position_margin'] = total_position_margin
                    account['unrealized_pnl'] = total_unrealized_pnl
                    account['total_equity'] = total_equity
                    account['total_pnl'] = total_pnl
                except Exception as e:
                    logger.error(f"Error getting positions for {model}: {str(e)}")
                    account['total_position_value'] = 0
                    account['total_position_margin'] = 0
                    account['unrealized_pnl'] = 0
                    account['total_equity'] = float(account['current_balance'])
        
        latest_prices = {}
        price_changes = {}
        for symbol in ["SOLUSDT", "BTCUSDT", "ETHUSDT", "BNBUSDT", "ASTERUSDT"]:
            price = db.get_latest_price(symbol)
            if price:
                latest_prices[symbol] = float(price['price'])
                
                history_24h = db.get_price_history(symbol, hours=24)
                if len(history_24h) > 0:
                    old_price = float(history_24h[0]['price'])
                    current_price = float(price['price'])
                    change_pct = ((current_price - old_price) / old_price) * 100
                    price_changes[symbol] = change_pct
                else:
                    price_changes[symbol] = 0
        
        recent_decisions = db.get_recent_decisions(limit=50)
        for decision in recent_decisions:
            if decision.get('decision_data') and isinstance(decision['decision_data'], str):
                decision['decision_data'] = json.loads(decision['decision_data'])
        
        all_positions = []
        for model in models:
            try:
                client = get_model_aster_client(model)
                positions_data = await client.get_position()
                
                for pos in positions_data:
                    position_amt = float(pos.get('positionAmt', 0))
                    if position_amt != 0:
                        all_positions.append({
                            "model": model,
                            "symbol": pos.get('symbol'),
                            "side": 'LONG' if position_amt > 0 else 'SHORT',
                            "size": abs(position_amt),
                            "entry_price": float(pos.get('entryPrice', 0)),
                            "current_price": float(pos.get('markPrice', 0)),
                            "unrealized_pnl": float(pos.get('unRealizedProfit', 0))
                        })
            except Exception as e:
                logger.error(f"Error getting positions for {model}: {str(e)}")
        
        all_orders = []
        for model in models:
            try:
                client = get_model_aster_client(model)
                symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ASTERUSDT", "SOLUSDT"]
                
                for symbol in symbols:
                    try:
                        trades = await client.get_user_trades(symbol, limit=50)
                        for trade in trades:
                            realized_pnl = float(trade.get('realizedPnl', 0))
                            commission = float(trade.get('commission', 0))
                            
                            if realized_pnl == 0 and commission != 0:
                                realized_pnl = -abs(commission)
                            
                            all_orders.append({
                                "id": trade.get('id'),
                                "model": model,
                                "symbol": trade.get('symbol'),
                                "side": trade.get('side'),
                                "price": float(trade.get('price', 0)),
                                "qty": float(trade.get('qty', 0)),
                                "status": "FILLED",
                                "pnl": realized_pnl,
                                "created_at": datetime.fromtimestamp(int(trade.get('time', 0)) / 1000).isoformat()
                            })
                    except Exception as e:
                        logger.warning(f"Error fetching trades for {model} {symbol}: {str(e)}")
            except Exception as e:
                logger.error(f"Error fetching trades for {model}: {str(e)}")
        
        all_orders.sort(key=lambda x: x['created_at'], reverse=True)
        all_orders = all_orders[:100]
        
        return {
            "accounts": accounts,
            "prices": latest_prices,
            "price_changes": price_changes,
            "recent_decisions": recent_decisions,
            "positions": all_positions,
            "orders": all_orders,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/pnl/snapshots")
async def get_pnl_snapshots(
    model: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=168)
):
    try:
        snapshots = db.get_pnl_snapshots(model=model, hours=hours)
        return {"snapshots": snapshots}
    except Exception as e:
        logger.error(f"Error fetching PNL snapshots: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pnl/snapshot")
async def create_pnl_snapshot(model: str, pnl: float):
    try:
        db.insert_pnl_snapshot(model, pnl)
        return {"status": "ok", "message": f"PNL snapshot created for {model}"}
    except Exception as e:
        logger.error(f"Error creating PNL snapshot: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
