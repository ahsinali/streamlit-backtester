from PySide6 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
import numpy as np
import pandas as pd

from backtester_p2.engine.cursor import BarCursor
from backtester_p2.engine.indicators import sma
from backtester_p2.sim.orders import Order, OrderType, Side
from backtester_p2.sim.broker import Broker
from backtester_p2.store.manifest import anonymize_frame

class TimeAxisItem(pg.AxisItem):
    def __init__(self, dates):
        super().__init__(orientation="bottom")
        self._dates = dates
    def tickStrings(self, values, scale, spacing):
        return [pd.Timestamp(self._dates[int(v)]).strftime("%b %d") if 0 <= int(v) < len(self._dates) else "" for v in values]

class CandleItem(pg.GraphicsObject):
    def __init__(self):
        super().__init__()
        self._data = None
        self._up = None
        self._bounds = QtCore.QRectF()
        self._up_color = pg.mkColor(0,176,116)
        self._down_color = pg.mkColor(235,83,80)
    def setData(self, ohlc, up_mask):
        self._data = ohlc
        self._up = up_mask.astype(bool)
        xs = np.arange(len(ohlc))
        if len(ohlc):
            lows = ohlc[:,2]; highs = ohlc[:,1]
            self._bounds = QtCore.QRectF(float(xs.min())-1,float(np.nanmin(lows))-1,
                                         float(xs.max()-xs.min())+2,float(np.nanmax(highs)-np.nanmin(lows))+2)
        self.prepareGeometryChange(); self.update()
    def paint(self, p, *args):
        if self._data is None: return
        body_w = 0.6
        for i,(o,h,l,c) in enumerate(self._data):
            x=float(i); color=self._up_color if self._up[i] else self._down_color
            pen=QtGui.QPen(color); pen.setCosmetic(True)
            p.setPen(pen)
            p.drawLine(QtCore.QPointF(x,l), QtCore.QPointF(x,h))  # wick
            rect=QtCore.QRectF(x-body_w/2, min(o,c), body_w, abs(c-o))
            p.fillRect(rect, color)
            p.drawRect(rect)
    def boundingRect(self): return self._bounds

class ChartWindow(QtWidgets.QMainWindow):
    def __init__(self, df, manifest, cfg):
        super().__init__()
        self.df = df; self.manifest = manifest; self.cfg=cfg
        self.cursor=BarCursor(len(df)); self.broker=Broker(cfg)
        self._prep_arrays(); self._build_ui(); self._connect(); self._render(0)

    def _prep_arrays(self):
        self.ts=self.df["Date"].to_numpy()
        self.open=self.df["Open"].to_numpy(float)
        self.high=self.df["High"].to_numpy(float)
        self.low=self.df["Low"].to_numpy(float)
        self.close=self.df["Close"].to_numpy(float)
        self.vol=self.df["Volume"].to_numpy(float)
        self.sma20=sma(self.close,20); self.sma50=sma(self.close,50); self.sma200=sma(self.close,200)

    def _build_ui(self):
        cw=QtWidgets.QWidget(); layout=QtWidgets.QVBoxLayout(cw); self.setCentralWidget(cw)
        tb=QtWidgets.QToolBar(); self.addToolBar(tb)
        self.a_next=QtGui.QAction("Next",self); self.a_prev=QtGui.QAction("Prev",self)
        self.a_buy=QtGui.QAction("Buy Mkt",self); self.a_sell=QtGui.QAction("Sell Mkt",self)
        for a in (self.a_next,self.a_prev,self.a_buy,self.a_sell): tb.addAction(a)

        self.plot=pg.PlotWidget(axisItems={"bottom": TimeAxisItem(self.ts)})
        self.candles=CandleItem(); self.plot.addItem(self.candles)
        self.curve20=self.plot.plot(pen=pg.mkPen("k")); self.curve50=self.plot.plot(pen=pg.mkPen("b")); self.curve200=self.plot.plot(pen=pg.mkPen("orange"))
        layout.addWidget(self.plot)

        self.hud=QtWidgets.QLabel(""); layout.addWidget(self.hud)
        self.lbl_cash=QtWidgets.QLabel("Cash:"); self.lbl_pos=QtWidgets.QLabel("Pos:")
        dock=QtWidgets.QDockWidget("Account",self); w=QtWidgets.QWidget(); f=QtWidgets.QFormLayout(w)
        f.addRow("Cash",self.lbl_cash); f.addRow("Pos",self.lbl_pos); dock.setWidget(w); self.addDockWidget(QtCore.Qt.RightDockWidgetArea,dock)

    def _connect(self):
        self.a_next.triggered.connect(self._advance); self.a_prev.triggered.connect(self._retreat)
        self.a_buy.triggered.connect(self._buy); self.a_sell.triggered.connect(self._sell)

    def _advance(self): self.cursor.next(); self.broker.process_bar(self.cursor.i,self.open[self.cursor.i],self.high[self.cursor.i],self.low[self.cursor.i],self.close[self.cursor.i]); self._render(self.cursor.i)
    def _retreat(self): self.cursor.prev(); self._render(self.cursor.i)
    def _buy(self): self.broker.place(Order(ts_index=self.cursor.i, side=Side.BUY, qty=1.0, type=OrderType.MARKET))
    def _sell(self): self.broker.place(Order(ts_index=self.cursor.i, side=Side.SELL, qty=1.0, type=OrderType.MARKET))

    def _render(self,i):
        sl=slice(0,i+1); x=np.arange(i+1); ohlc=np.vstack([self.open[sl],self.high[sl],self.low[sl],self.close[sl]]).T
        self.candles.setData(ohlc,self.close[sl]>=self.open[sl])
        self.curve20.setData(x,self.sma20[:i+1]); self.curve50.setData(x,self.sma50[:i+1]); self.curve200.setData(x,self.sma200[:i+1])
        self.hud.setText(f"Bar {i+1}/{len(self.df)} O:{self.open[i]:.2f} C:{self.close[i]:.2f}")
        self.lbl_cash.setText(f"{self.broker.state.cash:.2f}"); self.lbl_pos.setText(f"{self.broker.state.pos.qty:.2f}@{self.broker.state.pos.avg_price:.2f}")
