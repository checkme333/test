#!/usr/bin/env python3
"""
Automated Trading Bot for AI Trading Competition
Polls LLMs every 3 minutes and executes their trading decisions
"""

import asyncio
import httpx
import logging
from datetime import datetime
from typing import Dict, Any, List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

API_BASE = "http://localhost:8000"
MODELS = ["chatgpt", "deepseek"]  # Only working APIs
SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ASTERUSDT"]
POLL_INTERVAL = 180  # 3 minutes in seconds


async def get_llm_decision(client: httpx.AsyncClient, model: str, symbol: str) -> Dict[str, Any]:
    """Get trading decision from an LLM"""
    try:
        response = await client.post(
            f"{API_BASE}/llm/decision",
            params={"model": model, "symbol": symbol},
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error getting decision from {model} for {symbol}: {e}")
        return None


async def execute_trade(client: httpx.AsyncClient, model: str, decision: Dict[str, Any]) -> bool:
    """Execute a trade based on LLM decision"""
    try:
        action = decision.get("action")
        if action == "HOLD":
            logger.info(f"{model}: HOLD decision, no trade executed")
            return False
        
        size_usd = decision.get("size_usd", 100.0)
        leverage = decision.get("leverage", 5)
        symbol = decision.get("symbol", "BTCUSDT")
        
        if action == "BUY":
            side = "BUY"
        elif action == "SELL":
            side = "SELL"
        elif action == "CLOSE":
            logger.info(f"{model}: CLOSE action - position closing not yet implemented")
            return False
        else:
            logger.warning(f"{model}: Unknown action {action}")
            return False
        
        order_data = {
            "model": model,
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": size_usd / 100.0,  # Convert USD to quantity (simplified)
            "leverage": leverage
        }
        
        logger.info(f"{model}: Executing {action} order for {symbol} - Size: ${size_usd}, Leverage: {leverage}x")
        
        response = await client.post(
            f"{API_BASE}/order",
            json=order_data,
            timeout=30.0
        )
        response.raise_for_status()
        result = response.json()
        
        logger.info(f"{model}: Order executed successfully - {result}")
        return True
        
    except Exception as e:
        logger.error(f"Error executing trade for {model}: {e}")
        return False


async def trading_cycle():
    """Run one complete trading cycle for all models"""
    async with httpx.AsyncClient() as client:
        logger.info("=" * 80)
        logger.info(f"Starting trading cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        
        for model in MODELS:
            symbol_index = MODELS.index(model) % len(SYMBOLS)
            symbol = SYMBOLS[symbol_index]
            
            logger.info(f"\n{model.upper()}: Requesting decision for {symbol}...")
            
            decision_response = await get_llm_decision(client, model, symbol)
            if not decision_response:
                continue
            
            decision = decision_response.get("decision", {})
            reasoning = decision.get("reasoning", "No reasoning provided")
            action = decision.get("action", "HOLD")
            
            logger.info(f"{model.upper()}: Decision = {action}")
            logger.info(f"{model.upper()}: Reasoning = {reasoning}")
            
            if action != "HOLD":
                await execute_trade(client, model, decision)
            
            await asyncio.sleep(2)
        
        logger.info("\n" + "=" * 80)
        logger.info(f"Trading cycle completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Next cycle in {POLL_INTERVAL} seconds")
        logger.info("=" * 80 + "\n")


async def main():
    """Main loop - run trading cycles every 3 minutes"""
    logger.info("🤖 AI Trading Bot Started")
    logger.info(f"Models: {', '.join(MODELS)}")
    logger.info(f"Symbols: {', '.join(SYMBOLS)}")
    logger.info(f"Poll Interval: {POLL_INTERVAL} seconds ({POLL_INTERVAL/60} minutes)")
    logger.info("")
    
    while True:
        try:
            await trading_cycle()
            await asyncio.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            logger.info("\n🛑 Bot stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            logger.info("Retrying in 60 seconds...")
            await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
