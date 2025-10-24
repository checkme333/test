import httpx
import hmac
import hashlib
import time
import os
import uuid
from typing import Optional, Dict, Any, List
from app.config import settings
from app.models import OrderRequest, Position, Order, OrderStatus, OrderSide
import logging

logger = logging.getLogger(__name__)


class AsterClient:
    def __init__(self):
        self.base_url = settings.aster_base_url
        self.api_key = settings.aster_api_key
        self.api_secret = settings.aster_api_secret
        self.client = httpx.AsyncClient(timeout=30.0)
        self.mock_mode = os.getenv("MOCK_MODE", "false").lower() == "true"
        self._symbol_precision_cache = {}
        if self.mock_mode:
            logger.info("🎭 MOCK MODE ENABLED - Using simulated Aster API responses")
    
    def _generate_signature(self, params: Dict[str, Any]) -> str:
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        logger.info(f"Generating signature with query_string: {query_string}")
        logger.info(f"Using API key: {self.api_key[:10]}... and secret: {self.api_secret[:10]}...")
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        logger.info(f"Generated signature: {signature}")
        return signature
    
    async def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, 
                       signed: bool = True) -> Dict[str, Any]:
        if params is None:
            params = {}
        
        if signed:
            params['timestamp'] = int(time.time() * 1000)
            signature = self._generate_signature(params)
            params['signature'] = signature
        
        headers = {
            'X-MBX-APIKEY': self.api_key
        } if self.api_key else {}
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == "GET":
                response = await self.client.get(url, params=params, headers=headers)
            elif method == "POST":
                response = await self.client.post(url, data=params, headers=headers)
            elif method == "DELETE":
                response = await self.client.delete(url, data=params, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            logger.info(f"{method} {endpoint} - Status: {response.status_code}")
            
            if response.status_code >= 500:
                logger.error(f"Server error {response.status_code}: {response.text}")
                raise Exception(f"Aster API server error: {response.status_code}")
            
            response.raise_for_status()
            return response.json()
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Request error: {str(e)}")
            raise
    
    async def get_exchange_info(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        endpoint = "/fapi/v1/exchangeInfo"
        params = {}
        if symbol:
            params['symbol'] = symbol
        return await self._request("GET", endpoint, params, signed=False)
    
    async def _get_symbol_precision(self, symbol: str) -> tuple[int, int]:
        """Get quantity and price precision for a symbol. Returns (quantity_precision, price_precision)"""
        if symbol in self._symbol_precision_cache:
            return self._symbol_precision_cache[symbol]
        
        try:
            exchange_info = await self.get_exchange_info(symbol)
            for sym_info in exchange_info.get('symbols', []):
                if sym_info['symbol'] == symbol:
                    qty_precision = sym_info.get('quantityPrecision', 3)
                    price_precision = sym_info.get('pricePrecision', 2)
                    self._symbol_precision_cache[symbol] = (qty_precision, price_precision)
                    logger.info(f"Symbol {symbol} precision: qty={qty_precision}, price={price_precision}")
                    return (qty_precision, price_precision)
            
            logger.warning(f"Could not find precision for {symbol}, using defaults")
            return (3, 2)
        except Exception as e:
            logger.error(f"Error getting precision for {symbol}: {e}")
            return (3, 2)
    
    def _format_quantity(self, quantity: float, precision: int) -> str:
        """Format quantity to the correct precision"""
        return f"{quantity:.{precision}f}"
    
    async def place_order(self, order: OrderRequest) -> Dict[str, Any]:
        if self.mock_mode:
            mock_order_id = str(uuid.uuid4())[:8]
            mock_response = {
                'orderId': mock_order_id,
                'symbol': order.symbol,
                'status': 'NEW',
                'clientOrderId': order.client_order_id or f"mock_{mock_order_id}",
                'price': str(order.price) if order.price else '0',
                'origQty': str(order.qty),
                'executedQty': '0',
                'side': order.side.value.upper(),
                'type': order.order_type,
                'timeInForce': order.time_in_force,
                'updateTime': int(time.time() * 1000)
            }
            logger.info(f"🎭 MOCK: Order placed: {mock_response}")
            return mock_response
        
        qty_precision, price_precision = await self._get_symbol_precision(order.symbol)
        
        formatted_qty = self._format_quantity(order.qty, qty_precision)
        
        endpoint = "/fapi/v1/order"
        params = {
            'symbol': order.symbol,
            'side': order.side.value.upper(),
            'type': order.order_type,
            'quantity': formatted_qty,
        }
        
        if order.order_type != "MARKET":
            params['timeInForce'] = order.time_in_force
        
        if order.price:
            formatted_price = self._format_quantity(order.price, price_precision)
            params['price'] = formatted_price
        
        if order.client_order_id:
            params['newClientOrderId'] = order.client_order_id
        
        if order.reduce_only:
            params['reduceOnly'] = 'true'
        
        logger.info(f"Placing order: {order.symbol} {order.side.value.upper()} {formatted_qty} @ {params.get('price', 'MARKET')}")
        
        try:
            result = await self._request("POST", endpoint, params)
            logger.info(f"Order placed: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to place order: {str(e)}")
            if "503" in str(e) or "500" in str(e):
                if order.client_order_id:
                    return await self.query_order_by_client_id(order.symbol, order.client_order_id)
            raise
    
    async def cancel_order(self, symbol: str, order_id: Optional[str] = None, 
                          client_order_id: Optional[str] = None) -> Dict[str, Any]:
        endpoint = "/fapi/v1/order"
        params = {'symbol': symbol}
        
        if order_id:
            params['orderId'] = order_id
        elif client_order_id:
            params['origClientOrderId'] = client_order_id
        else:
            raise ValueError("Either order_id or client_order_id must be provided")
        
        return await self._request("DELETE", endpoint, params)
    
    async def query_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        endpoint = "/fapi/v1/order"
        params = {
            'symbol': symbol,
            'orderId': order_id
        }
        return await self._request("GET", endpoint, params)
    
    async def query_order_by_client_id(self, symbol: str, client_order_id: str) -> Dict[str, Any]:
        endpoint = "/fapi/v1/order"
        params = {
            'symbol': symbol,
            'origClientOrderId': client_order_id
        }
        try:
            return await self._request("GET", endpoint, params)
        except Exception as e:
            logger.warning(f"Order not found by client ID: {client_order_id}")
            return None
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        endpoint = "/fapi/v1/openOrders"
        params = {}
        if symbol:
            params['symbol'] = symbol
        return await self._request("GET", endpoint, params)
    
    async def get_all_orders(self, symbol: str, limit: int = 500) -> List[Dict[str, Any]]:
        endpoint = "/fapi/v1/allOrders"
        params = {
            'symbol': symbol,
            'limit': limit
        }
        return await self._request("GET", endpoint, params)
    
    async def get_user_trades(self, symbol: str, limit: int = 500) -> List[Dict[str, Any]]:
        """Get account trade history with realized P&L"""
        endpoint = "/fapi/v1/userTrades"
        params = {
            'symbol': symbol,
            'limit': limit
        }
        return await self._request("GET", endpoint, params)
    
    async def get_position(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        if self.mock_mode:
            mock_positions = [{
                'symbol': symbol or 'SOLUSDT',
                'positionAmt': '0',
                'entryPrice': '0',
                'markPrice': '200.50',
                'unRealizedProfit': '0',
                'liquidationPrice': '0',
                'leverage': '2',
                'maxNotionalValue': '5000',
                'marginType': 'cross',
                'isolatedMargin': '0',
                'isAutoAddMargin': 'false',
                'positionSide': 'BOTH',
                'notional': '0',
                'isolatedWallet': '0',
                'updateTime': int(time.time() * 1000)
            }]
            logger.info(f"🎭 MOCK: Returning positions: {mock_positions}")
            return mock_positions
        
        endpoint = "/fapi/v2/positionRisk"
        params = {}
        if symbol:
            params['symbol'] = symbol
        return await self._request("GET", endpoint, params)
    
    async def get_account(self) -> Dict[str, Any]:
        endpoint = "/fapi/v2/account"
        return await self._request("GET", endpoint, {})
    
    async def get_balance(self) -> List[Dict[str, Any]]:
        endpoint = "/fapi/v2/balance"
        return await self._request("GET", endpoint, {})
    
    async def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        endpoint = "/fapi/v1/fundingRate"
        params = {
            'symbol': symbol,
            'limit': 1
        }
        result = await self._request("GET", endpoint, params, signed=False)
        return result[0] if result else {}
    
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        endpoint = "/fapi/v1/ticker/24hr"
        params = {'symbol': symbol}
        return await self._request("GET", endpoint, params, signed=False)
    
    async def get_depth(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """Get order book depth"""
        endpoint = "/fapi/v1/depth"
        params = {
            'symbol': symbol,
            'limit': limit
        }
        return await self._request("GET", endpoint, params, signed=False)
    
    async def change_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """Change leverage for a symbol"""
        endpoint = "/fapi/v1/leverage"
        params = {
            'symbol': symbol,
            'leverage': leverage
        }
        return await self._request("POST", endpoint, params)
    
    async def close(self):
        await self.client.aclose()


aster_client = AsterClient()


def get_model_aster_client(model: str) -> AsterClient:
    """Get Aster client for a specific model"""
    from app.config import settings
    
    model_keys = {
        "chatgpt": (settings.chatgpt_aster_api_key, settings.chatgpt_aster_api_secret),
        "grok": (settings.grok_aster_api_key, settings.grok_aster_api_secret),
        "gemini": (settings.gemini_aster_api_key, settings.gemini_aster_api_secret),
        "deepseek": (settings.deepseek_aster_api_key, settings.deepseek_aster_api_secret),
    }
    
    if model not in model_keys:
        return aster_client
    
    api_key, api_secret = model_keys[model]
    if not api_key or not api_secret:
        return aster_client
    
    client = AsterClient()
    client.api_key = api_key
    client.api_secret = api_secret
    return client
