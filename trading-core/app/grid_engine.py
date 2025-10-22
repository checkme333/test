import hashlib
import math
from typing import List, Dict, Any, Optional
from app.models import GridSignal, OrderRequest, OrderSide, SpacingType, LevelState
from app.database import db
from app.aster_client import aster_client
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class GridEngine:
    
    @staticmethod
    def generate_client_order_id(model: str, symbol: str, config_id: int, level_idx: int) -> str:
        data = f"{model}:{symbol}:{config_id}:{level_idx}"
        return hashlib.md5(data.encode()).hexdigest()[:16]
    
    @staticmethod
    def calculate_grid_levels(lower: float, upper: float, grids: int, 
                             spacing: SpacingType) -> List[float]:
        levels = []
        
        if spacing == SpacingType.ARITHMETIC:
            step = (upper - lower) / (grids - 1)
            for i in range(grids):
                levels.append(lower + i * step)
        
        elif spacing == SpacingType.GEOMETRIC:
            ratio = (upper / lower) ** (1 / (grids - 1))
            for i in range(grids):
                levels.append(lower * (ratio ** i))
        
        return levels
    
    @staticmethod
    def calculate_qty_per_level(base_allocation: float, grids: int, 
                                leverage: int, price: float) -> float:
        notional_per_level = base_allocation / grids
        qty = (notional_per_level * leverage) / price
        return round(qty, 3)
    
    @staticmethod
    async def check_risk_limits(model: str, symbol: str, signal: GridSignal) -> tuple[bool, Optional[str]]:
        if signal.leverage > settings.risk_max_leverage:
            return False, f"Leverage {signal.leverage} exceeds max {settings.risk_max_leverage}"
        
        total_exposure = signal.base_allocation * signal.leverage
        if total_exposure > settings.risk_max_symbol_exposure:
            return False, f"Exposure {total_exposure} exceeds max {settings.risk_max_symbol_exposure}"
        
        orders = db.get_orders(model=model)
        daily_pnl = sum(order.get('pnl', 0) for order in orders 
                       if order.get('created_at') and 
                       (order['created_at'].date() == orders[0]['created_at'].date() if orders else False))
        
        if daily_pnl < settings.risk_max_daily_loss:
            return False, f"Daily loss {daily_pnl} exceeds limit {settings.risk_max_daily_loss}"
        
        return True, None
    
    @staticmethod
    async def apply_grid(signal: GridSignal) -> Dict[str, Any]:
        logger.info(f"Applying grid for {signal.model} on {signal.symbol}")
        
        risk_ok, risk_msg = await GridEngine.check_risk_limits(signal.model, signal.symbol, signal)
        if not risk_ok:
            logger.error(f"Risk check failed: {risk_msg}")
            db.update_grid_status(signal.model, signal.symbol, "tripped")
            return {
                "status": "error",
                "message": risk_msg,
                "config_id": None
            }
        
        config_data = {
            "model": signal.model,
            "symbol": signal.symbol,
            "lower": float(signal.lower),
            "upper": float(signal.upper),
            "grids": signal.grids,
            "spacing": signal.spacing.value,
            "base_allocation": float(signal.base_allocation),
            "leverage": signal.leverage,
            "tp_pct": float(signal.tp_pct),
            "sl_pct": float(signal.sl_pct),
            "rebalance": signal.rebalance,
            "status": "active"
        }
        
        config_id = db.upsert_grid_config(config_data)
        logger.info(f"Grid config created/updated: {config_id}")
        
        prices = GridEngine.calculate_grid_levels(
            signal.lower, signal.upper, signal.grids, signal.spacing
        )
        
        mid_price = (signal.lower + signal.upper) / 2
        
        placed_count = 0
        error_count = 0
        
        for idx, price in enumerate(prices):
            side = OrderSide.BUY if price <= mid_price else OrderSide.SELL
            qty = GridEngine.calculate_qty_per_level(
                signal.base_allocation, signal.grids, signal.leverage, price
            )
            
            client_order_id = GridEngine.generate_client_order_id(
                signal.model, signal.symbol, config_id, idx
            )
            
            level_data = {
                "config_id": config_id,
                "level_idx": idx,
                "price": float(price),
                "side": side.value,
                "qty": float(qty),
                "client_order_id": client_order_id,
                "state": LevelState.PLANNED.value
            }
            db.insert_grid_level(level_data)
            
            try:
                existing_order = await aster_client.query_order_by_client_id(
                    signal.symbol, client_order_id
                )
                
                if existing_order:
                    logger.info(f"Order already exists: {client_order_id}")
                    db.update_grid_level_state(client_order_id, LevelState.PLACED.value)
                    placed_count += 1
                    continue
                
                order_req = OrderRequest(
                    symbol=signal.symbol,
                    side=side,
                    price=price,
                    qty=qty,
                    order_type="LIMIT",
                    client_order_id=client_order_id,
                    time_in_force="GTC"
                )
                
                result = await aster_client.place_order(order_req)
                
                order_data = {
                    "model": signal.model,
                    "symbol": signal.symbol,
                    "client_order_id": client_order_id,
                    "exchange_order_id": result.get('orderId'),
                    "side": side.value,
                    "price": float(price),
                    "qty": float(qty),
                    "fill_qty": float(result.get('executedQty', 0)),
                    "status": result.get('status', 'NEW').lower(),
                    "fee": 0.0,
                    "pnl": 0.0
                }
                db.insert_order(order_data)
                db.update_grid_level_state(client_order_id, LevelState.PLACED.value)
                placed_count += 1
                
            except Exception as e:
                logger.error(f"Failed to place order for level {idx}: {str(e)}")
                db.update_grid_level_state(client_order_id, LevelState.ERROR.value, str(e))
                error_count += 1
        
        return {
            "status": "ok",
            "config_id": config_id,
            "placed": placed_count,
            "errors": error_count,
            "total_levels": len(prices)
        }
    
    @staticmethod
    async def sync_grid_orders(config_id: int) -> Dict[str, Any]:
        levels = db.get_grid_levels(config_id)
        
        synced = 0
        filled = 0
        
        for level in levels:
            if level['state'] not in [LevelState.PLACED.value, LevelState.FILLED.value]:
                continue
            
            try:
                order = await aster_client.query_order_by_client_id(
                    level['symbol'] if 'symbol' in level else None,
                    level['client_order_id']
                )
                
                if not order:
                    continue
                
                status = order.get('status', '').lower()
                fill_qty = float(order.get('executedQty', 0))
                
                order_data = {
                    "model": level.get('model', ''),
                    "symbol": order.get('symbol', ''),
                    "client_order_id": level['client_order_id'],
                    "exchange_order_id": order.get('orderId'),
                    "side": level['side'],
                    "price": float(level['price']),
                    "qty": float(level['qty']),
                    "fill_qty": fill_qty,
                    "status": status,
                    "fee": 0.0,
                    "pnl": 0.0
                }
                db.insert_order(order_data)
                
                if status == 'filled':
                    db.update_grid_level_state(level['client_order_id'], LevelState.FILLED.value)
                    filled += 1
                
                synced += 1
                
            except Exception as e:
                logger.error(f"Failed to sync order {level['client_order_id']}: {str(e)}")
        
        return {
            "status": "ok",
            "synced": synced,
            "filled": filled
        }


grid_engine = GridEngine()
