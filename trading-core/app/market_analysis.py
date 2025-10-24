"""
Market Analysis Module
Provides technical indicators and market data analysis for AI trading decisions
"""
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def calculate_price_changes(price_history: List[Dict[str, Any]], minutes: int = 3) -> Dict[str, Any]:
    """
    Calculate price changes over the specified time window
    
    Args:
        price_history: List of price records with 'price' and 'timestamp' fields
        minutes: Time window in minutes (default: 3)
    
    Returns:
        Dict containing price statistics
    """
    if not price_history or len(price_history) < 2:
        return {
            "change_percent": 0,
            "change_absolute": 0,
            "high": 0,
            "low": 0,
            "volatility": 0,
            "trend": "NEUTRAL"
        }
    
    cutoff_time = datetime.now() - timedelta(minutes=minutes)
    recent_prices = [
        p for p in price_history 
        if datetime.fromisoformat(str(p['timestamp'])) >= cutoff_time
    ]
    
    if not recent_prices:
        recent_prices = price_history[-10:]
    
    prices = [float(p['price']) for p in recent_prices]
    
    if len(prices) < 2:
        return {
            "change_percent": 0,
            "change_absolute": 0,
            "high": prices[0] if prices else 0,
            "low": prices[0] if prices else 0,
            "volatility": 0,
            "trend": "NEUTRAL"
        }
    
    first_price = prices[0]
    last_price = prices[-1]
    high_price = max(prices)
    low_price = min(prices)
    
    change_absolute = last_price - first_price
    change_percent = (change_absolute / first_price) * 100 if first_price > 0 else 0
    
    volatility = np.std(prices) if len(prices) > 1 else 0
    
    if change_percent > 0.5:
        trend = "BULLISH"
    elif change_percent < -0.5:
        trend = "BEARISH"
    else:
        trend = "NEUTRAL"
    
    return {
        "change_percent": round(change_percent, 4),
        "change_absolute": round(change_absolute, 4),
        "high": round(high_price, 4),
        "low": round(low_price, 4),
        "volatility": round(volatility, 4),
        "trend": trend,
        "data_points": len(prices)
    }


def calculate_macd(prices: List[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Dict[str, Any]:
    """
    Calculate MACD (Moving Average Convergence Divergence) indicator
    
    Args:
        prices: List of prices
        fast_period: Fast EMA period (default: 12)
        slow_period: Slow EMA period (default: 26)
        signal_period: Signal line period (default: 9)
    
    Returns:
        Dict containing MACD values
    """
    if len(prices) < slow_period:
        return {
            "macd": 0,
            "signal": 0,
            "histogram": 0,
            "trend": "NEUTRAL"
        }
    
    prices_array = np.array(prices)
    
    ema_fast = _calculate_ema(prices_array, fast_period)
    ema_slow = _calculate_ema(prices_array, slow_period)
    
    macd_line = ema_fast - ema_slow
    signal_line = _calculate_ema(macd_line, signal_period)
    histogram = macd_line - signal_line
    
    macd_value = macd_line[-1] if len(macd_line) > 0 else 0
    signal_value = signal_line[-1] if len(signal_line) > 0 else 0
    histogram_value = histogram[-1] if len(histogram) > 0 else 0
    
    if histogram_value > 0 and macd_value > signal_value:
        trend = "BULLISH"
    elif histogram_value < 0 and macd_value < signal_value:
        trend = "BEARISH"
    else:
        trend = "NEUTRAL"
    
    return {
        "macd": round(float(macd_value), 4),
        "signal": round(float(signal_value), 4),
        "histogram": round(float(histogram_value), 4),
        "trend": trend
    }


def calculate_kdj(prices: List[float], highs: List[float], lows: List[float], period: int = 9) -> Dict[str, Any]:
    """
    Calculate KDJ indicator (Stochastic Oscillator with J line)
    
    Args:
        prices: List of closing prices
        highs: List of high prices
        lows: List of low prices
        period: Period for calculation (default: 9)
    
    Returns:
        Dict containing KDJ values
    """
    if len(prices) < period:
        return {
            "k": 50,
            "d": 50,
            "j": 50,
            "signal": "NEUTRAL"
        }
    
    rsv_values = []
    for i in range(period - 1, len(prices)):
        period_high = max(highs[i - period + 1:i + 1])
        period_low = min(lows[i - period + 1:i + 1])
        
        if period_high == period_low:
            rsv = 50
        else:
            rsv = ((prices[i] - period_low) / (period_high - period_low)) * 100
        rsv_values.append(rsv)
    
    k_values = [50]
    d_values = [50]
    
    for rsv in rsv_values:
        k = (2 / 3) * k_values[-1] + (1 / 3) * rsv
        k_values.append(k)
        d = (2 / 3) * d_values[-1] + (1 / 3) * k
        d_values.append(d)
    
    k_value = k_values[-1]
    d_value = d_values[-1]
    j_value = 3 * k_value - 2 * d_value
    
    if k_value > d_value and k_value < 80:
        signal = "BUY"
    elif k_value < d_value and k_value > 20:
        signal = "SELL"
    elif k_value > 80:
        signal = "OVERBOUGHT"
    elif k_value < 20:
        signal = "OVERSOLD"
    else:
        signal = "NEUTRAL"
    
    return {
        "k": round(k_value, 2),
        "d": round(d_value, 2),
        "j": round(j_value, 2),
        "signal": signal
    }


def _calculate_ema(prices: np.ndarray, period: int) -> np.ndarray:
    """Calculate Exponential Moving Average"""
    if len(prices) < period:
        return np.array([np.mean(prices)] * len(prices))
    
    ema = np.zeros(len(prices))
    ema[period - 1] = np.mean(prices[:period])
    
    multiplier = 2 / (period + 1)
    
    for i in range(period, len(prices)):
        ema[i] = (prices[i] - ema[i - 1]) * multiplier + ema[i - 1]
    
    return ema


def calculate_rsi(prices: List[float], period: int = 14) -> Dict[str, Any]:
    """
    Calculate RSI (Relative Strength Index)
    
    Args:
        prices: List of prices
        period: Period for calculation (default: 14)
    
    Returns:
        Dict containing RSI value and signal
    """
    if len(prices) < period + 1:
        return {
            "rsi": 50,
            "signal": "NEUTRAL"
        }
    
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    if avg_loss == 0:
        rsi = 100
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    
    if rsi > 70:
        signal = "OVERBOUGHT"
    elif rsi < 30:
        signal = "OVERSOLD"
    elif rsi > 50:
        signal = "BULLISH"
    else:
        signal = "BEARISH"
    
    return {
        "rsi": round(rsi, 2),
        "signal": signal
    }


async def get_order_book_depth(aster_client, symbol: str) -> Dict[str, Any]:
    """
    Get order book depth from Aster API
    
    Args:
        aster_client: Aster API client
        symbol: Trading symbol
    
    Returns:
        Dict containing order book depth analysis
    """
    try:
        depth = await aster_client.get_depth(symbol, limit=20)
        
        if not depth or 'bids' not in depth or 'asks' not in depth:
            return {
                "bid_depth": 0,
                "ask_depth": 0,
                "bid_ask_ratio": 1,
                "pressure": "NEUTRAL"
            }
        
        bids = depth['bids'][:10]
        asks = depth['asks'][:10]
        
        bid_volume = sum(float(bid[1]) for bid in bids)
        ask_volume = sum(float(ask[1]) for ask in asks)
        
        bid_ask_ratio = bid_volume / ask_volume if ask_volume > 0 else 1
        
        if bid_ask_ratio > 1.5:
            pressure = "BUYING"
        elif bid_ask_ratio < 0.67:
            pressure = "SELLING"
        else:
            pressure = "NEUTRAL"
        
        return {
            "bid_depth": round(bid_volume, 2),
            "ask_depth": round(ask_volume, 2),
            "bid_ask_ratio": round(bid_ask_ratio, 4),
            "pressure": pressure,
            "best_bid": float(bids[0][0]) if bids else 0,
            "best_ask": float(asks[0][0]) if asks else 0
        }
    except Exception as e:
        logger.error(f"Error getting order book depth: {str(e)}")
        return {
            "bid_depth": 0,
            "ask_depth": 0,
            "bid_ask_ratio": 1,
            "pressure": "NEUTRAL"
        }


def analyze_market_data(price_history: List[Dict[str, Any]], symbol: str) -> Dict[str, Any]:
    """
    Comprehensive market data analysis
    
    Args:
        price_history: List of price records
        symbol: Trading symbol
    
    Returns:
        Dict containing all technical indicators and analysis
    """
    if not price_history:
        return {
            "price_changes": {},
            "macd": {},
            "kdj": {},
            "rsi": {},
            "summary": "Insufficient data for analysis"
        }
    
    prices = [float(p['price']) for p in price_history]
    
    price_changes = calculate_price_changes(price_history, minutes=3)
    
    macd = calculate_macd(prices)
    
    highs = prices
    lows = prices
    kdj = calculate_kdj(prices, highs, lows)
    
    rsi = calculate_rsi(prices)
    
    bullish_signals = 0
    bearish_signals = 0
    
    if price_changes['trend'] == 'BULLISH':
        bullish_signals += 1
    elif price_changes['trend'] == 'BEARISH':
        bearish_signals += 1
    
    if macd['trend'] == 'BULLISH':
        bullish_signals += 1
    elif macd['trend'] == 'BEARISH':
        bearish_signals += 1
    
    if kdj['signal'] in ['BUY', 'OVERSOLD']:
        bullish_signals += 1
    elif kdj['signal'] in ['SELL', 'OVERBOUGHT']:
        bearish_signals += 1
    
    if rsi['signal'] in ['BULLISH', 'OVERSOLD']:
        bullish_signals += 1
    elif rsi['signal'] in ['BEARISH', 'OVERBOUGHT']:
        bearish_signals += 1
    
    if bullish_signals > bearish_signals:
        summary = f"BULLISH ({bullish_signals}/4 indicators)"
    elif bearish_signals > bullish_signals:
        summary = f"BEARISH ({bearish_signals}/4 indicators)"
    else:
        summary = "NEUTRAL (mixed signals)"
    
    return {
        "price_changes": price_changes,
        "macd": macd,
        "kdj": kdj,
        "rsi": rsi,
        "summary": summary,
        "bullish_signals": bullish_signals,
        "bearish_signals": bearish_signals
    }
