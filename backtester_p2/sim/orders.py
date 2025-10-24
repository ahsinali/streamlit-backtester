from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

class Side(Enum):
    BUY = auto()
    SELL = auto()

class OrderType(Enum):
    MARKET = auto()
    LIMIT = auto()
    STOP = auto()

@dataclass
class Order:
    ts_index: int                 # bar index when the order is placed
    side: Side                    # BUY or SELL
    qty: float                    # quantity (units/shares)
    type: OrderType = OrderType.MARKET
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    id: int = field(default_factory=lambda: id(object()))
    status: str = "OPEN"          # OPEN, FILLED, CANCELED
    filled_qty: float = 0.0
    avg_price: float = 0.0
