#!/usr/bin/env python3
"""
Automated Trading Bot for AI Trading Competition
Polls LLMs every 3 minutes and executes their trading decisions

Features:
- All 4 LLMs: ChatGPT, Grok, Claude, DeepSeek
- Max 20% of balance per trade
- Leverage: 3-10x (AI decides within this range)
- Symbols: BTC, ETH, BNB, ASTER
- AI has full autonomy for trading decisions
"""

import asyncio
import httpx
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

API_BASE = "http://localhost:8000"
MODELS = ["chatgpt", "grok", "claude", "deepseek"]  # All 4 LLMs
SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ASTERUSDT"]
POLL_INTERVAL = 180  # 3 minutes in seconds
MAX_POSITION_SIZE_PCT = 0.20  # 20% of balance max per trade
MIN_LEVERAGE = 3
MAX_LEVERAGE = 10


async def get_model_account(client: httpx.AsyncClient, model: str) -> Optional[Dict]:
    """Get model account balance"""
    try:
        response = await client.get(f"{API_BASE}/models/{model}/account", timeout=10.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error getting account for {model}: {e}")
        return None


async def get_llm_decision(client: httpx.AsyncClient, model: str, symbol: str) -> Optional[Dict[str, Any]]:
    """Get trading decision from an LLM"""
    try:
        logger.info(f"{model.upper()}: Requesting decision for {symbol}...")
        response = await client.post(
            f"{API_BASE}/llm/decision",
            params={"model": model, "symbol": symbol},
            timeout=60.0  # Increased timeout for LLM calls
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error getting decision from {model} for {symbol}: {e}")
        return None


async def execute_trade(client: httpx.AsyncClient, model: str, symbol: str, decision: Dict[str, Any], account: Dict) -> bool:
    """Execute a trade based on LLM decision with safety checks"""
    try:
        action = decision.get("action", "HOLD")
        
        if action == "HOLD":
            logger.info(f"{model.upper()}: HOLD decision, no trade executed")
            return False
        
        current_balance = float(account.get("current_balance", 1000.0))
        
        max_position_size = current_balance * MAX_POSITION_SIZE_PCT
        
        desired_size_usd = decision.get("size_usd", 100.0)
        desired_leverage = decision.get("leverage", 5)
        
        size_usd = min(desired_size_usd, max_position_size)
        leverage = max(MIN_LEVERAGE, min(desired_leverage, MAX_LEVERAGE))
        
        if size_usd != desired_size_usd:
            logger.warning(f"{model.upper()}: Adjusted position size from ${desired_size_usd:.2f} to ${size_usd:.2f} (20% limit)")
        if leverage != desired_leverage:
            logger.warning(f"{model.upper()}: Adjusted leverage from {desired_leverage}x to {leverage}x (3-10x limit)")
        
        if action == "BUY":
            side = "buy"
        elif action == "SELL":
            side = "sell"
        elif action == "CLOSE":
            logger.info(f"{model.upper()}: CLOSE action - will be handled by position management")
            return False
        else:
            logger.warning(f"{model.upper()}: Unknown action {action}")
            return False
        
        price_response = await client.get(f"{API_BASE}/price/latest", params={"symbol": symbol}, timeout=10.0)
        if not price_response.is_success:
            logger.error(f"{model.upper()}: Failed to get current price for {symbol}")
            return False
        
        price_data = price_response.json()
        current_price = float(price_data.get("price", 0))
        
        if current_price <= 0:
            logger.error(f"{model.upper()}: Invalid price {current_price} for {symbol}")
            return False
        
        qty = (size_usd * leverage) / current_price
        
        order_data = {
            "model": model,  # Include model for correct API key selection
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "order_type": "MARKET",
            "reduce_only": False
        }
        
        logger.info(f"{model.upper()}: Executing {action} order for {symbol}")
        logger.info(f"  Size: ${size_usd:.2f} ({size_usd/current_balance*100:.1f}% of balance)")
        logger.info(f"  Leverage: {leverage}x")
        logger.info(f"  Quantity: {qty:.6f}")
        logger.info(f"  Price: ${current_price:.2f}")
        
        response = await client.post(
            f"{API_BASE}/order",
            json=order_data,
            timeout=30.0
        )
        
        if response.is_success:
            result = response.json()
            logger.info(f"{model.upper()}: ✅ Order executed successfully")
            logger.info(f"  Order ID: {result.get('orderId', 'N/A')}")
            return True
        else:
            logger.error(f"{model.upper()}: ❌ Order failed with status {response.status_code}")
            logger.error(f"  Response: {response.text}")
            return False
        
    except Exception as e:
        logger.error(f"Error executing trade for {model}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def trading_cycle():
    """Run one complete trading cycle for all models"""
    async with httpx.AsyncClient() as client:
        logger.info("=" * 80)
        logger.info(f"🔄 Starting trading cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        
        for model in MODELS:
            logger.info(f"\n{'='*60}")
            logger.info(f"🤖 Processing {model.upper()}")
            logger.info(f"{'='*60}")
            
            account = await get_model_account(client, model)
            if not account:
                logger.error(f"{model.upper()}: Failed to get account info, skipping")
                continue
            
            balance = float(account.get("current_balance", 0))
            pnl = float(account.get("total_pnl", 0))
            logger.info(f"{model.upper()}: Balance=${balance:.2f}, P&L=${pnl:.2f}")
            
            for symbol in SYMBOLS:
                logger.info(f"\n{model.upper()}: Analyzing {symbol}...")
                
                decision_response = await get_llm_decision(client, model, symbol)
                if not decision_response:
                    logger.warning(f"{model.upper()}: No decision received for {symbol}")
                    continue
                
                decision = decision_response.get("decision", {})
                reasoning = decision.get("reasoning", "No reasoning provided")
                action = decision.get("action", "HOLD")
                
                logger.info(f"{model.upper()}: Decision for {symbol} = {action}")
                logger.info(f"{model.upper()}: Reasoning: {reasoning[:200]}...")
                
                if action != "HOLD":
                    success = await execute_trade(client, model, symbol, decision, account)
                    if success:
                        logger.info(f"{model.upper()}: ✅ Trade executed for {symbol}")
                        account = await get_model_account(client, model)
                    else:
                        logger.warning(f"{model.upper()}: ❌ Trade failed for {symbol}")
                
                await asyncio.sleep(1)
            
            await asyncio.sleep(2)
        
        logger.info("\n" + "=" * 80)
        logger.info(f"✅ Trading cycle completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"⏰ Next cycle in {POLL_INTERVAL} seconds ({POLL_INTERVAL/60} minutes)")
        logger.info("=" * 80 + "\n")


async def main():
    """Main loop - run trading cycles every 3 minutes"""
    logger.info("🚀 AI Trading Bot Started")
    logger.info(f"📊 Models: {', '.join(MODELS)}")
    logger.info(f"💱 Symbols: {', '.join(SYMBOLS)}")
    logger.info(f"⏱️  Poll Interval: {POLL_INTERVAL} seconds ({POLL_INTERVAL/60} minutes)")
    logger.info(f"💰 Max Position Size: {MAX_POSITION_SIZE_PCT*100}% of balance")
    logger.info(f"📈 Leverage Range: {MIN_LEVERAGE}x - {MAX_LEVERAGE}x")
    logger.info("")
    
    while True:
        try:
            await trading_cycle()
            await asyncio.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            logger.info("\n🛑 Bot stopped by user")
            break
        except Exception as e:
            logger.error(f"❌ Error in main loop: {e}")
            import traceback
            logger.error(traceback.format_exc())
            logger.info("⏰ Retrying in 60 seconds...")
            await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
