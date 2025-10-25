from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from enum import Enum


class SpacingType(str, Enum):
    ARITHMETIC = "arithmetic"
    GEOMETRIC = "geometric"


class EntryMode(str, Enum):
    MAKER_FIRST = "maker_first"
    TAKER = "taker"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    NEW = "new"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"


class GridStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    TRIPPED = "tripped"


class LevelState(str, Enum):
    PLANNED = "planned"
    PLACED = "placed"
    FILLED = "filled"
    CANCELED = "canceled"
    ERROR = "error"


class GridSignal(BaseModel):
    model: Literal["chatgpt", "grok"]
    strategy: str = "grid"
    symbol: str
    lower: float
    upper: float
    grids: int
    spacing: SpacingType = SpacingType.ARITHMETIC
    base_allocation: float
    leverage: int
    entry_mode: EntryMode = EntryMode.MAKER_FIRST
    tp_pct: float = 0.03
    sl_pct: float = 0.05
    rebalance: bool = False
    notes: Optional[str] = None


class OrderRequest(BaseModel):
    symbol: str
    side: OrderSide
    price: Optional[float] = None
    qty: float
    order_type: Literal["LIMIT", "MARKET"] = "LIMIT"
    client_order_id: Optional[str] = None
    reduce_only: bool = False
    time_in_force: str = "GTC"


class Position(BaseModel):
    symbol: str
    side: str
    size: float
    entry_price: float
    mark_price: float
    leverage: int
    unrealized_pnl: float
    margin: float


class Order(BaseModel):
    order_id: str
    client_order_id: Optional[str] = None
    symbol: str
    side: OrderSide
    price: float
    qty: float
    filled_qty: float
    status: OrderStatus
    fee: float = 0.0
    created_at: datetime
    updated_at: datetime


class GridConfig(BaseModel):
    id: Optional[int] = None
    model: str
    symbol: str
    lower: float
    upper: float
    grids: int
    spacing: str
    base_allocation: float
    leverage: int
    tp_pct: float
    sl_pct: float
    rebalance: bool
    status: GridStatus = GridStatus.ACTIVE
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class GridLevel(BaseModel):
    id: Optional[int] = None
    config_id: int
    level_idx: int
    price: float
    side: OrderSide
    qty: float
    client_order_id: str
    state: LevelState = LevelState.PLANNED
    last_error: Optional[str] = None
    updated_at: Optional[datetime] = None


class PnLMetrics(BaseModel):
    model: str
    symbol: str
    pnl: float
    daily_pnl: float
    win_rate: float
    max_drawdown: float
    exposure: float
    timestamp: datetime


class PnLSnapshot(BaseModel):
    id: Optional[int] = None
    model: str
    pnl: float
    timestamp: datetime
