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
        technical = market_data.get('technical_indicators', {})
        order_book = market_data.get('order_book', {})
        
        price_change_1h = 0
        if len(price_history) >= 2:
            price_change_1h = ((current_price - price_history[0]['price']) / price_history[0]['price']) * 100
        
        prompt = f"""You are an AI trading agent competing in a live trading competition. You have FULL AUTONOMY to manage your portfolio and make trading decisions.

**Current Market Data:**
- Symbol: {market_data.get('symbol', 'SOLUSDT')}
- Current Price: ${current_price:.2f}
- 1-Hour Price Change: {price_change_1h:+.2f}%

**Price Changes (Last 3 Minutes):**
"""
        if 'price_changes' in technical:
            pc = technical['price_changes']
            prompt += f"""- Change: {pc.get('change_percent', 0):+.2f}% (${pc.get('change_absolute', 0):+.2f})
- High: ${pc.get('high', 0):.2f}
- Low: ${pc.get('low', 0):.2f}
- Volatility: {pc.get('volatility', 0):.4f}
- Trend: {pc.get('trend', 'NEUTRAL')}
"""
        
        prompt += """
**Technical Indicators:**
"""
        if 'macd' in technical:
            macd = technical['macd']
            prompt += f"""- MACD: {macd.get('macd', 0):.4f} | Signal: {macd.get('signal', 0):.4f} | Histogram: {macd.get('histogram', 0):.4f}
- MACD Trend: {macd.get('trend', 'NEUTRAL')}
"""
        
        if 'kdj' in technical:
            kdj = technical['kdj']
            prompt += f"""- KDJ: K={kdj.get('k', 50):.2f} | D={kdj.get('d', 50):.2f} | J={kdj.get('j', 50):.2f}
- KDJ Signal: {kdj.get('signal', 'NEUTRAL')}
"""
        
        if 'rsi' in technical:
            rsi = technical['rsi']
            prompt += f"""- RSI: {rsi.get('rsi', 50):.2f}
- RSI Signal: {rsi.get('signal', 'NEUTRAL')}
"""
        
        if technical.get('summary'):
            prompt += f"""- Overall Market Signal: {technical['summary']}
"""
        
        prompt += """
**Order Book Depth:**
"""
        if order_book:
            prompt += f"""- Bid Depth: {order_book.get('bid_depth', 0):.2f} | Ask Depth: {order_book.get('ask_depth', 0):.2f}
- Bid/Ask Ratio: {order_book.get('bid_ask_ratio', 1):.4f}
- Market Pressure: {order_book.get('pressure', 'NEUTRAL')}
"""
        
        prompt += f"""
**Your Account Status:**
- Initial Capital: $500 USDT
- Available Balance: ${account.get('current_balance', 0):.2f}
- Total P&L: ${account.get('total_pnl', 0):.2f}
- Total Trades: {account.get('total_trades', 0)}
- Win Rate: {account.get('winning_trades', 0) / max(account.get('total_trades', 1), 1) * 100:.1f}%

**Current Position:**
"""
        if position:
            prompt += f"""- Side: {position['side'].upper()}
- Size: {position['size']}
- Entry Price: ${position['entry_price']:.2f}
- Current Price: ${position.get('current_price', current_price):.2f}
- Unrealized P&L: ${position.get('unrealized_pnl', 0):.2f}
- Leverage: {position.get('leverage', 1)}x
"""
        else:
            prompt += "- No open position\n"
        
        prompt += """
**TRADING RULES (MUST FOLLOW):**
1. **Tradable Assets**: ONLY BTCUSDT, ETHUSDT, BNBUSDT, ASTERUSDT - you can hold positions in any combination of these
2. **Minimum Order Size**: $50 USD (before leverage) - this is the base capital, not including leverage
3. **Available Balance Requirement**: If available balance < $100, do NOT open new positions (only close existing ones)
4. **Capital Management**: Keep at least $100 in reserve - your operable amount is limited to $400 maximum
5. **Minimum Close Size**: When closing positions (partial or full), must close at least 20% of that position's size
6. **Leverage Range**: Must be between 3x and 10x (choose based on your confidence and market conditions)
7. **Multiple Positions**: You CAN hold multiple positions across different assets simultaneously
8. **Full Autonomy**: You have complete freedom to decide:
   - Long or Short positions
   - Entry and exit timing
   - Position sizes (within rules)
   - Leverage multiplier (3-10x)
   - Partial or full position closes

**AVAILABLE ACTIONS:**
1. **BUY**: Open a LONG position (betting price will go UP)
   - Specify: size_usd (max 20% of balance), leverage (3-10x)
   - Use when: Bullish signals, upward momentum, oversold conditions

2. **SELL**: Open a SHORT position (betting price will go DOWN)
   - Specify: size_usd (max 20% of balance), leverage (3-10x)
   - Use when: Bearish signals, downward momentum, overbought conditions

3. **CLOSE**: Close your current position (partial or full)
   - Specify: close_percent (0-100, default 100 for full close)
   - Use when: Take profit, cut losses, or rebalance

4. **HOLD**: Wait for better opportunity
   - Use when: Mixed signals, unclear trend, or waiting for confirmation

**DECISION STRATEGY:**
- Analyze ALL provided data: price changes, technical indicators, order book depth
- Consider risk/reward ratio and market conditions
- Be decisive but not reckless
- Use higher leverage (7-10x) when very confident, lower (3-5x) when uncertain
- Don't be afraid to take profits or cut losses

**Response Format (JSON only, no additional text):**
```json
{
    "action": "BUY|SELL|CLOSE|HOLD",
    "size_usd": 99.99,
    "leverage": 5,
    "close_percent": 100,
    "reasoning": "Brief explanation based on technical analysis and market conditions",
    "confidence": 0.75
}
```

**Field Requirements:**
- action: REQUIRED (BUY/SELL/CLOSE/HOLD)
- size_usd: REQUIRED for BUY/SELL (max 20% of balance = ${account.get('current_balance', 0) * 0.2:.2f})
- leverage: REQUIRED for BUY/SELL (3-10)
- close_percent: OPTIONAL for CLOSE (default 100)
- reasoning: REQUIRED (explain your analysis)
- confidence: REQUIRED (0.0-1.0)

Analyze the data and provide your decision now:"""
        
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
    """xAI Grok API client with Cloudflare AI Gateway support"""
    
    def __init__(self):
        super().__init__("grok")
        from app.config import settings
        
        self.api_key = os.getenv("XAI_API_KEY", "")
        
        cf_account_id = settings.cloudflare_account_id
        cf_gateway_id = settings.cloudflare_gateway_id
        
        if cf_account_id and cf_gateway_id:
            self.base_url = f"https://gateway.ai.cloudflare.com/v1/{cf_account_id}/{cf_gateway_id}/compat"
            logger.info(f"Using Cloudflare AI Gateway for Grok API: {self.base_url}")
        else:
            self.base_url = "https://api.x.ai/v1/chat/completions"
            logger.info("Using direct Grok API (no Cloudflare Gateway configured)")
        
        self.model = "grok-3"
    
    async def get_trading_decision(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        print(f"[GROK DEBUG] get_trading_decision called: mock_mode={self.mock_mode}, has_api_key={bool(self.api_key)}, base_url={self.base_url}")
        logger.info(f"Grok.get_trading_decision called: mock_mode={self.mock_mode}, has_api_key={bool(self.api_key)}, base_url={self.base_url}, client_id={id(self)}")
        
        if self.mock_mode or not self.api_key:
            print(f"[GROK DEBUG] Early return - mock_mode={self.mock_mode}, has_api_key={bool(self.api_key)}")
            logger.warning(f"Grok early return: mock_mode={self.mock_mode}, has_api_key={bool(self.api_key)}")
            return self._mock_decision(market_data)
        
        prompt = self._build_prompt(market_data)
        logger.info(f"Grok prompt length: {len(prompt)} chars")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        self.base_url,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                            "Accept": "application/json"
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
                    logger.info(f"Grok API response status: {response.status_code}")
                    response.raise_for_status()
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    logger.info(f"Grok raw response length: {len(content)} chars, first 200: {content[:200]}")
                    
                    content = content.strip()
                    if content.startswith("```json"):
                        content = content[7:]
                    if content.startswith("```"):
                        content = content[3:]
                    if content.endswith("```"):
                        content = content[:-3]
                    content = content.strip()
                    
                    try:
                        decision = json.loads(content)
                        logger.info(f"Grok decision SUCCESS: {decision.get('action', 'UNKNOWN')}")
                        return decision
                    except json.JSONDecodeError as e:
                        logger.error(f"Grok JSON parse error: {e}. Cleaned content (first 500): {content[:500]}")
                        if attempt < max_retries - 1:
                            logger.warning(f"Retrying Grok API call (attempt {attempt + 2}/{max_retries})...")
                            await asyncio.sleep(1)
                            continue
                        logger.error("Grok: All JSON parse retries exhausted, returning mock")
                        return self._mock_decision(market_data)
                    
            except httpx.HTTPStatusError as e:
                logger.error(f"Grok HTTP error: status={e.response.status_code}, body={e.response.text[:500]}")
                if e.response.status_code in [403, 429, 503]:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.warning(f"Grok API blocked (status {e.response.status_code}), retrying in {wait_time}s... (attempt {attempt + 2}/{max_retries})")
                        await asyncio.sleep(wait_time)
                        continue
                logger.error(f"Grok: HTTP error {e.response.status_code}, returning mock")
                return self._mock_decision(market_data)
            except httpx.TimeoutException as e:
                logger.error(f"Grok timeout error: {str(e)}")
                if attempt < max_retries - 1:
                    logger.warning(f"Retrying after timeout (attempt {attempt + 2}/{max_retries})...")
                    await asyncio.sleep(2)
                    continue
                logger.error("Grok: All timeout retries exhausted, returning mock")
                return self._mock_decision(market_data)
            except Exception as e:
                logger.error(f"Grok unexpected error: {type(e).__name__}: {str(e)}")
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


class GeminiClient(LLMClient):
    """Google Gemini API client"""
    
    def __init__(self):
        super().__init__("gemini")
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"
        self.model = "gemini-2.0-flash-exp"
    
    async def get_trading_decision(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        if self.mock_mode or not self.api_key:
            return self._mock_decision(market_data)
        
        prompt = self._build_prompt(market_data)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}?key={self.api_key}",
                    headers={
                        "Content-Type": "application/json"
                    },
                    json={
                        "contents": [{
                            "parts": [{
                                "text": f"You are an expert trading AI. Always respond with valid JSON only.\n\n{prompt}"
                            }]
                        }],
                        "generationConfig": {
                            "temperature": 0.7,
                            "maxOutputTokens": 500
                        }
                    }
                )
                response.raise_for_status()
                result = response.json()
                content = result['candidates'][0]['content']['parts'][0]['text']
                
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                
                decision = json.loads(content)
                logger.info(f"Gemini decision: {decision}")
                return decision
                
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            return self._mock_decision(market_data)
    
    def _mock_decision(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        import random
        actions = ["BUY", "SELL", "HOLD", "CLOSE"]
        action = random.choice(actions)
        
        return {
            "action": action,
            "size_usd": random.uniform(50, 200),
            "reasoning": f"Mock Gemini decision: AI analysis suggests {action.lower()} based on market patterns.",
            "confidence": random.uniform(0.6, 0.9)
        }


class LLMClientsRegistry:
    _instance = None
    _clients = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def _init_clients(self):
        logger.info("Initializing LLM clients...")
        self._clients = {
            "chatgpt": ChatGPTClient(),
            "grok": GrokClient(),
            "gemini": GeminiClient(),
            "deepseek": DeepSeekClient()
        }
        self._initialized = True
        
        for name, client in self._clients.items():
            has_key = bool(getattr(client, 'api_key', None))
            mock_mode = getattr(client, 'mock_mode', False)
            logger.info(f"{name}: has_key={has_key}, mock_mode={mock_mode}")
        
        logger.info("LLM clients initialized")
    
    def __getitem__(self, key):
        if not self._initialized:
            self._init_clients()
        return self._clients[key]
    
    def __contains__(self, key):
        return key in ["chatgpt", "grok", "gemini", "deepseek"]

llm_clients = LLMClientsRegistry()
