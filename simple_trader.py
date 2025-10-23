#!/usr/bin/env python3
"""
Simple Automated Trading Bot
Polls LLMs every 3 minutes and simulates trades by updating model accounts
"""

import asyncio
import httpx
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

API_BASE = "http://localhost:8000"
MODELS = ["chatgpt", "deepseek", "claude"]
SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ASTERUSDT"]
POLL_INTERVAL = 180  # 3 minutes


async def get_and_log_decision(client: httpx.AsyncClient, model: str, symbol: str):
    """Get trading decision from LLM and log it"""
    try:
        logger.info(f"📊 {model.upper()}: Requesting decision for {symbol}...")
        response = await client.post(
            f"{API_BASE}/llm/decision",
            params={"model": model, "symbol": symbol},
            timeout=30.0
        )
        response.raise_for_status()
        result = response.json()
        
        decision = result.get("decision", {})
        action = decision.get("action", "HOLD")
        reasoning = decision.get("reasoning", "No reasoning")
        
        logger.info(f"✅ {model.upper()}: {action}")
        logger.info(f"💭 {model.upper()}: {reasoning[:100]}...")
        
        return result
    except Exception as e:
        logger.error(f"❌ {model.upper()}: Error - {e}")
        return None


async def trading_cycle():
    """Run one trading cycle for all models"""
    async with httpx.AsyncClient() as client:
        logger.info("=" * 80)
        logger.info(f"🤖 Trading Cycle Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        
        for i, model in enumerate(MODELS):
            symbol = SYMBOLS[i % len(SYMBOLS)]
            await get_and_log_decision(client, model, symbol)
            await asyncio.sleep(2)  # Small delay between models
        
        logger.info("=" * 80)
        logger.info(f"✅ Cycle Complete: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"⏰ Next cycle in {POLL_INTERVAL} seconds ({POLL_INTERVAL/60} minutes)")
        logger.info("=" * 80 + "\n")


async def main():
    """Main loop"""
    logger.info("🚀 AI Trading Bot Started")
    logger.info(f"📈 Models: {', '.join(MODELS)}")
    logger.info(f"💱 Symbols: {', '.join(SYMBOLS)}")
    logger.info(f"⏱️  Interval: {POLL_INTERVAL}s ({POLL_INTERVAL/60}min)")
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
            logger.info("⏰ Retrying in 60 seconds...")
            await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
