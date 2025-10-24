"""
Order Execution Module
Executes trading decisions from AI models via Aster API
"""
import logging
from typing import Dict, Any, Optional
from app.aster_client import get_model_aster_client
from app.database import db
from app.models import OrderRequest, OrderSide

logger = logging.getLogger(__name__)


async def execute_trading_decision(model: str, symbol: str, decision: Dict[str, Any], decision_id: int) -> Dict[str, Any]:
    """
    Execute a trading decision from an AI model
    
    Args:
        model: Model name (chatgpt, grok, claude, deepseek)
        symbol: Trading symbol (e.g., BTCUSDT)
        decision: Decision dict with action, size_usd, leverage, etc.
        decision_id: ID of the decision record in database
    
    Returns:
        Dict containing execution result
    """
    try:
        action = decision.get('action', 'HOLD')
        
        if action == 'HOLD':
            logger.info(f"{model} decided to HOLD on {symbol}")
            return {
                "status": "success",
                "action": "HOLD",
                "message": "No action taken"
            }
        
        client = get_model_aster_client(model)
        account = db.get_model_account(model)
        
        if not account:
            raise Exception(f"Account not found for model: {model}")
        
        current_balance = float(account['current_balance'])
        
        if action == 'CLOSE':
            return await _execute_close(client, model, symbol, decision)
        
        elif action in ['BUY', 'SELL']:
            return await _execute_open(client, model, symbol, decision, current_balance)
        
        else:
            raise Exception(f"Unknown action: {action}")
    
    except Exception as e:
        logger.error(f"Error executing decision for {model}: {str(e)}")
        return {
            "status": "error",
            "action": decision.get('action'),
            "error": str(e)
        }


async def _execute_open(client, model: str, symbol: str, decision: Dict[str, Any], current_balance: float) -> Dict[str, Any]:
    """Execute BUY or SELL order"""
    action = decision.get('action')
    size_usd = float(decision.get('size_usd', 0))
    leverage = int(decision.get('leverage', 5))
    
    account_info = await client.get_account()
    available_balance = float(account_info.get('availableBalance', current_balance))
    total_position_margin = float(account_info.get('totalPositionInitialMargin', 0))
    total_unrealized_pnl = float(account_info.get('totalUnrealizedProfit', 0))
    
    total_equity = available_balance + total_position_margin + total_unrealized_pnl
    
    if available_balance < 100:
        logger.warning(f"{model}: Available balance ${available_balance:.2f} < $100, cannot open new positions")
        return {
            "status": "skipped",
            "action": action,
            "message": f"Available balance ${available_balance:.2f} is below $100 minimum, can only close existing positions"
        }
    
    max_usable_equity = min(total_equity - 100, 400)
    already_used = total_position_margin
    max_operable = max_usable_equity - already_used
    
    if max_operable < 50:
        logger.warning(f"{model}: Max operable ${max_operable:.2f} < $50, already at capital limits")
        return {
            "status": "skipped",
            "action": action,
            "message": f"Already at maximum capital usage (${already_used:.2f}), cannot open new position"
        }
    
    max_per_trade = total_equity * 0.2
    if size_usd > max_per_trade:
        logger.warning(f"{model}: Requested size ${size_usd} exceeds 20% of equity (${max_per_trade:.2f}), adjusting")
        size_usd = max_per_trade
    
    if size_usd < 50:
        logger.warning(f"{model}: Order size ${size_usd} < $50 minimum, skipping")
        return {
            "status": "skipped",
            "action": action,
            "message": f"Order size ${size_usd} is below $50 minimum"
        }
    
    if size_usd > max_operable:
        logger.warning(f"{model}: Requested size ${size_usd} exceeds max operable ${max_operable:.2f}, adjusting")
        size_usd = min(size_usd, max_operable)
    
    if size_usd < 50:
        logger.warning(f"{model}: Adjusted size ${size_usd} < $50 minimum after applying limits, skipping")
        return {
            "status": "skipped",
            "action": action,
            "message": f"Order size ${size_usd} is below $50 minimum after applying limits"
        }
    
    if leverage < 3:
        leverage = 3
    elif leverage > 10:
        leverage = 10
    
    try:
        await client.change_leverage(symbol, leverage)
        logger.info(f"{model}: Set leverage to {leverage}x for {symbol}")
    except Exception as e:
        logger.warning(f"{model}: Failed to set leverage: {str(e)}")
    
    latest_price = db.get_latest_price(symbol)
    if not latest_price:
        raise Exception(f"No price data available for {symbol}")
    
    current_price = float(latest_price['price'])
    
    quantity = (size_usd * leverage) / current_price
    quantity = round(quantity, 3)
    
    if quantity <= 0:
        raise Exception(f"Invalid quantity: {quantity}")
    
    side = OrderSide.BUY if action == 'BUY' else OrderSide.SELL
    
    order_request = OrderRequest(
        symbol=symbol,
        side=side,
        order_type="MARKET",
        qty=quantity,
        time_in_force="GTC"
    )
    
    logger.info(f"{model}: Placing {action} order for {symbol}: {quantity} @ ${current_price:.2f} (leverage: {leverage}x)")
    
    order_result = await client.place_order(order_request)
    
    db.insert_order({
        "model": model,
        "symbol": symbol,
        "order_id": order_result.get('orderId'),
        "side": action,
        "order_type": "MARKET",
        "quantity": quantity,
        "price": current_price,
        "status": order_result.get('status', 'NEW')
    })
    
    positions = await client.get_position(symbol)
    if positions:
        for pos in positions:
            if float(pos.get('positionAmt', 0)) != 0:
                db.upsert_position({
                    "model": model,
                    "symbol": symbol,
                    "side": "LONG" if float(pos['positionAmt']) > 0 else "SHORT",
                    "size": abs(float(pos['positionAmt'])),
                    "entry_price": float(pos.get('entryPrice', 0)),
                    "current_price": current_price,
                    "unrealized_pnl": float(pos.get('unRealizedProfit', 0)),
                    "leverage": int(pos.get('leverage', leverage))
                })
    
    logger.info(f"{model}: Order executed successfully: {order_result}")
    
    return {
        "status": "success",
        "action": action,
        "order_id": order_result.get('orderId'),
        "symbol": symbol,
        "quantity": quantity,
        "price": current_price,
        "leverage": leverage,
        "size_usd": size_usd
    }


async def _execute_close(client, model: str, symbol: str, decision: Dict[str, Any]) -> Dict[str, Any]:
    """Execute CLOSE order"""
    close_percent = float(decision.get('close_percent', 100))
    
    if close_percent <= 0 or close_percent > 100:
        close_percent = 100
    
    if close_percent < 20:
        logger.warning(f"{model}: Close percent {close_percent}% < 20% minimum, adjusting to 20%")
        close_percent = 20
    
    positions = await client.get_position(symbol)
    
    if not positions:
        logger.warning(f"{model}: No position found to close for {symbol}")
        return {
            "status": "success",
            "action": "CLOSE",
            "message": "No position to close"
        }
    
    position = None
    for pos in positions:
        if float(pos.get('positionAmt', 0)) != 0:
            position = pos
            break
    
    if not position:
        logger.warning(f"{model}: No open position found for {symbol}")
        return {
            "status": "success",
            "action": "CLOSE",
            "message": "No open position"
        }
    
    position_amt = float(position['positionAmt'])
    close_qty = abs(position_amt) * (close_percent / 100)
    close_qty = round(close_qty, 3)
    
    if close_qty <= 0:
        raise Exception(f"Invalid close quantity: {close_qty}")
    
    side = OrderSide.SELL if position_amt > 0 else OrderSide.BUY
    
    order_request = OrderRequest(
        symbol=symbol,
        side=side,
        order_type="MARKET",
        qty=close_qty,
        time_in_force="GTC",
        reduce_only=True
    )
    
    logger.info(f"{model}: Closing {close_percent}% of {symbol} position: {close_qty}")
    
    order_result = await client.place_order(order_request)
    
    db.insert_order({
        "model": model,
        "symbol": symbol,
        "order_id": order_result.get('orderId'),
        "side": side.value,
        "order_type": "MARKET",
        "quantity": close_qty,
        "price": 0,
        "status": order_result.get('status', 'NEW')
    })
    
    if close_percent >= 100:
        db.close_position(model, symbol)
        logger.info(f"{model}: Position fully closed for {symbol}")
    else:
        positions_updated = await client.get_position(symbol)
        if positions_updated:
            for pos in positions_updated:
                if float(pos.get('positionAmt', 0)) != 0:
                    latest_price = db.get_latest_price(symbol)
                    current_price = float(latest_price['price']) if latest_price else 0
                    
                    db.upsert_position({
                        "model": model,
                        "symbol": symbol,
                        "side": "LONG" if float(pos['positionAmt']) > 0 else "SHORT",
                        "size": abs(float(pos['positionAmt'])),
                        "entry_price": float(pos.get('entryPrice', 0)),
                        "current_price": current_price,
                        "unrealized_pnl": float(pos.get('unRealizedProfit', 0)),
                        "leverage": int(pos.get('leverage', 1))
                    })
    
    logger.info(f"{model}: Close order executed successfully: {order_result}")
    
    return {
        "status": "success",
        "action": "CLOSE",
        "order_id": order_result.get('orderId'),
        "symbol": symbol,
        "close_percent": close_percent,
        "quantity": close_qty
    }
