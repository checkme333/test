import httpx
import json
import os
import asyncio
from typing import Dict, Any, Optional
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class LLMClient:
    """Base class for LLM API clients"""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.mock_mode = os.getenv("MOCK_MODE", "false").lower() == "true"
    
    async def get_trading_decision(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get trading decision from LLM"""
        raise NotImplementedError
    
    def _build_prompt(self, market_data: Dict[str, Any]) -> str:
        """Build prompt for LLM with market data"""
        current_price = market_data.get('current_price', 0)
        price_history = market_data.get('price_history', [])
        position = market_data.get('position')
        account = market_data.get('account', {})
        
        price_change_1h = 0
        if len(price_history) >= 2:
            price_change_1h = ((current_price - price_history[0]['price']) / price_history[0]['price']) * 100
        
        prompt = f"""You are an AI trading agent competing in a live trading competition. You have FULL AUTONOMY to manage your portfolio and make trading decisions.

**Current Market Data:**
- Symbol: {market_data.get('symbol', 'SOLUSDT')}
- Current Price: ${current_price:.2f}
- 1-Hour Price Change: {price_change_1h:+.2f}%
- Price History (last hour): {len(price_history)} data points

**Your Account Status:**
- Available Balance: ${account.get('current_balance', 0):.2f}
- Total P&L: ${account.get('total_pnl', 0):.2f}
- Win Rate: {account.get('winning_trades', 0) / max(account.get('total_trades', 1), 1) * 100:.1f}%

**Current Position:**
"""
        if position:
            prompt += f"""- Side: {position['side'].upper()}
- Size: {position['size']}
- Entry Price: ${position['entry_price']:.2f}
- Unrealized P&L: ${position.get('unrealized_pnl', 0):.2f}
"""
        else:
            prompt += "- No open position\n"
        
        prompt += """
**Trading Rules & Guidelines:**
- You can trade ONLY these assets: BTC, ETH, BNB, ASTER (all paired with USDT)
- Maximum position size per trade: 20% of total balance
- Leverage range: 3x to 10x (you decide based on market conditions and confidence)
- You can hold multiple positions simultaneously across different assets
- You have complete autonomy to decide position sizes and leverage within the rules
- BE AGGRESSIVE: We need at least 3 trades (open + close) within 30 minutes for testing
- Make decisions based on price trends, volatility, and market momentum

**Your Task:**
Analyze the market and make a trading decision. You should be ACTIVE and take opportunities when you see them.

Actions available:
1. **BUY**: Open a long position with leverage (specify size_usd and leverage)
2. **SELL**: Open a short position with leverage (specify size_usd and leverage)
3. **CLOSE**: Close current position (if any)
4. **HOLD**: Wait for better opportunity (use sparingly - we need active trading!)

**Response Format (JSON only, no additional text):**
```json
{
    "action": "BUY|SELL|CLOSE|HOLD",
    "size_usd": 20.0,
    "leverage": 5,
    "reasoning": "Brief explanation of your decision (2-3 sentences)",
    "confidence": 0.75
}
```

Note: leverage field is required for BUY/SELL actions (3-10), optional for CLOSE/HOLD.

Provide your decision now:"""
        
        return prompt


class ChatGPTClient(LLMClient):
    """OpenAI ChatGPT API client"""
    
    def __init__(self):
        super().__init__("chatgpt")
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.model = "gpt-4o-mini"
    
    async def get_trading_decision(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        if self.mock_mode or not self.api_key:
            return self._mock_decision(market_data)
        
        prompt = self._build_prompt(market_data)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "You are an expert trading AI. Always respond with valid JSON only."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 500
                    }
                )
                response.raise_for_status()
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                
                decision = json.loads(content)
                logger.info(f"ChatGPT decision: {decision}")
                return decision
                
        except Exception as e:
            logger.error(f"ChatGPT API error: {str(e)}")
            return self._mock_decision(market_data)
    
    def _mock_decision(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock decision for testing"""
        import random
        actions = ["BUY", "SELL", "HOLD", "CLOSE"]
        action = random.choice(actions)
        
        return {
            "action": action,
            "size_usd": random.uniform(50, 200),
            "reasoning": f"Mock decision: Market analysis suggests {action.lower()} based on current price trends.",
            "confidence": random.uniform(0.6, 0.9)
        }


class GrokClient(LLMClient):
    """xAI Grok API client with Cloudflare bypass optimizations"""
    
    def __init__(self):
        super().__init__("grok")
        self.api_key = os.getenv("XAI_API_KEY", "")
        self.base_url = "https://api.x.ai/v1/chat/completions"
        self.model = "grok-3"
    
    async def get_trading_decision(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        if self.mock_mode or not self.api_key:
            return self._mock_decision(market_data)
        
        prompt = self._build_prompt(market_data)
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        self.base_url,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                            "Accept": "application/json",
                            "Accept-Language": "en-US,en;q=0.9",
                            "Accept-Encoding": "gzip, deflate, br",
                            "Connection": "keep-alive"
                        },
                        json={
                            "model": self.model,
                            "messages": [
                                {"role": "system", "content": "You are an expert trading AI. Always respond with valid JSON only."},
                                {"role": "user", "content": prompt}
                            ],
                            "temperature": 0.7,
                            "max_tokens": 500
                        }
                    )
                    response.raise_for_status()
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    
                    content = content.strip()
                    if content.startswith("```json"):
                        content = content[7:]
                    if content.startswith("```"):
                        content = content[3:]
                    if content.endswith("```"):
                        content = content[:-3]
                    content = content.strip()
                    
                    decision = json.loads(content)
                    logger.info(f"Grok decision: {decision}")
                    return decision
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code in [403, 429, 503]:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # 1s, 2s, 4s
                        logger.warning(f"Grok API blocked (status {e.response.status_code}), retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(wait_time)
                        continue
                logger.error(f"Grok API HTTP error: {str(e)}")
                return self._mock_decision(market_data)
            except Exception as e:
                logger.error(f"Grok API error: {str(e)}")
                return self._mock_decision(market_data)
        
        logger.error("Grok API: All retries exhausted")
        return self._mock_decision(market_data)
    
    def _mock_decision(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        import random
        actions = ["BUY", "SELL", "HOLD", "CLOSE"]
        action = random.choice(actions)
        
        return {
            "action": action,
            "size_usd": random.uniform(50, 200),
            "reasoning": f"Mock Grok decision: Technical indicators point to {action.lower()} opportunity.",
            "confidence": random.uniform(0.6, 0.9)
        }


class ClaudeClient(LLMClient):
    """Anthropic Claude API client"""
    
    def __init__(self):
        super().__init__("claude")
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.base_url = "https://api.anthropic.com/v1/messages"
        self.model = "claude-sonnet-4-5-20250929"
    
    async def get_trading_decision(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        if self.mock_mode or not self.api_key:
            return self._mock_decision(market_data)
        
        prompt = self._build_prompt(market_data)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "max_tokens": 500,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ]
                    }
                )
                response.raise_for_status()
                result = response.json()
                content = result['content'][0]['text']
                
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                
                decision = json.loads(content)
                logger.info(f"Claude decision: {decision}")
                return decision
                
        except Exception as e:
            logger.error(f"Claude API error: {str(e)}")
            return self._mock_decision(market_data)
    
    def _mock_decision(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        import random
        actions = ["BUY", "SELL", "HOLD", "CLOSE"]
        action = random.choice(actions)
        
        return {
            "action": action,
            "size_usd": random.uniform(50, 200),
            "reasoning": f"Mock Claude decision: Risk-reward analysis favors {action.lower()} position.",
            "confidence": random.uniform(0.6, 0.9)
        }


class DeepSeekClient(LLMClient):
    """DeepSeek API client"""
    
    def __init__(self):
        super().__init__("deepseek")
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        self.model = "deepseek-chat"
    
    async def get_trading_decision(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        if self.mock_mode or not self.api_key:
            return self._mock_decision(market_data)
        
        prompt = self._build_prompt(market_data)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "You are an expert trading AI. Always respond with valid JSON only."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 500
                    }
                )
                response.raise_for_status()
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                
                decision = json.loads(content)
                logger.info(f"DeepSeek decision: {decision}")
                return decision
                
        except Exception as e:
            logger.error(f"DeepSeek API error: {str(e)}")
            return self._mock_decision(market_data)
    
    def _mock_decision(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        import random
        actions = ["BUY", "SELL", "HOLD", "CLOSE"]
        action = random.choice(actions)
        
        return {
            "action": action,
            "size_usd": random.uniform(50, 200),
            "reasoning": f"Mock DeepSeek decision: Quantitative models indicate {action.lower()} signal.",
            "confidence": random.uniform(0.6, 0.9)
        }


llm_clients = {
    "chatgpt": ChatGPTClient(),
    "grok": GrokClient(),
    "claude": ClaudeClient(),
    "deepseek": DeepSeekClient()
}
