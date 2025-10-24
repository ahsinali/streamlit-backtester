from dataclasses import dataclass, field
from typing import List
from .orders import Order, OrderType, Side
from .config import SimConfig

@dataclass
class Position:
    qty: float = 0.0
    avg_price: float = 0.0

@dataclass
class BrokerState:
    cash: float
    pos: Position = field(default_factory=Position)
    equity: float = 0.0
    pnl_realized: float = 0.0
    max_equity: float = 0.0
    drawdown: float = 0.0

class Broker:
    def __init__(self, cfg: SimConfig):
        self.cfg = cfg
        self.orders: List[Order] = []
        self.state = BrokerState(cash=cfg.cash)

    def place(self, order: Order):
        self.orders.append(order)
        order.status = "OPEN"
        return order

    def cancel_all(self):
        for o in self.orders:
            if o.status == "OPEN":
                o.status = "CANCELED"

    # --- helpers ---
    def _apply_slip(self, price: float, side: Side) -> float:
        bps = self.cfg.slip_bps / 10000.0
        return price * (1 + bps) if side == Side.BUY else price * (1 - bps)

    def _apply_fee(self, notional: float) -> float:
        return abs(notional) * (self.cfg.fee_bps / 10000.0)

    def _fill(self, o: Order, price: float, i: int):
        price = self._apply_slip(price, o.side)
        fee = self._apply_fee(price * o.qty)
        notional = price * o.qty

        if o.side == Side.BUY:
            # increase/flip to long
            self.state.cash -= (notional + fee)
            new_qty = self.state.pos.qty + o.qty
            if new_qty != 0:
                self.state.pos.avg_price = (
                    self.state.pos.avg_price * self.state.pos.qty + notional
                ) / new_qty
            self.state.pos.qty = new_qty
        else:
            # SELL: close long first, then go/add short
            if self.state.pos.qty > 0:
                closed = min(self.state.pos.qty, o.qty)
                self.state.pnl_realized += (price - self.state.pos.avg_price) * closed
                self.state.pos.qty -= closed
                remain = o.qty - closed
                if remain > 0:
                    # flip to short on the remainder
                    self.state.pos.avg_price = price
                    self.state.pos.qty -= remain
            elif self.state.pos.qty < 0:
                # add to short
                new_qty = self.state.pos.qty - o.qty
                self.state.pos.avg_price = (
                    (self.state.pos.avg_price * abs(self.state.pos.qty)) + price * o.qty
                ) / abs(new_qty) if new_qty != 0 else price
                self.state.pos.qty = new_qty
            else:
                # start short from flat
                self.state.pos.avg_price = price
                self.state.pos.qty -= o.qty

            self.state.cash += (notional - fee)

        o.status = "FILLED"
        o.filled_qty = o.qty
        o.avg_price = price

    # --- main bar processor ---
    def process_bar(self, i: int, o: float, h: float, l: float, c: float):
        remaining: List[Order] = []
        for od in self.orders:
            if od.status != "OPEN":
                continue
            if od.type == OrderType.MARKET:
                ref = o if self.cfg.policy == "next_open" else c
                self._fill(od, ref, i)
            elif od.type == OrderType.LIMIT:
                if od.side == Side.BUY and l <= od.limit_price:
                    self._fill(od, od.limit_price, i)
                elif od.side == Side.SELL and h >= od.limit_price:
                    self._fill(od, od.limit_price, i)
                else:
                    remaining.append(od)
            elif od.type == OrderType.STOP:
                if od.side == Side.BUY and h >= od.stop_price:
                    self._fill(od, max(od.stop_price, o), i)
                elif od.side == Side.SELL and l <= od.stop_price:
                    self._fill(od, min(od.stop_price, o), i)
                else:
                    remaining.append(od)

        self.orders = remaining

        # Mark-to-market on close
        self.state.equity = self.state.cash + self.state.pos.qty * c
        self.state.max_equity = max(self.state.max_equity, self.state.equity)
        self.state.drawdown = self.state.max_equity - self.state.equity
