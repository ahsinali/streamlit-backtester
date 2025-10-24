# streamlit_app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
# import plotly.graph_objects as go
# Reuse your existing engine
from backtester_p2.io.csv_loader import load_ohlcv
from backtester_p2.engine.indicators import sma, rsi
from backtester_p2.sim.config import SimConfig
from backtester_p2.sim.broker import Broker
from backtester_p2.sim.orders import Order, OrderType, Side

st.set_page_config(page_title="Manual Backtester (Streamlit)", layout="wide")

def ema(x: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()

def true_range(h: np.ndarray, l: np.ndarray, c: np.ndarray) -> np.ndarray:
    prev_c = np.r_[c[0], c[:-1]]
    return np.maximum(h - l, np.maximum(np.abs(h - prev_c), np.abs(l - prev_c)))

def atr(h: np.ndarray, l: np.ndarray, c: np.ndarray, n: int = 10) -> np.ndarray:
    tr = true_range(h, l, c)
    # Wilder-like smoothing via EMA(alpha=1/n)
    return pd.Series(tr).ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()

# ---------- helpers ----------
def load_df(file) -> pd.DataFrame:
    if isinstance(file, str):
        df, _ = load_ohlcv(file)
    else:
        # Uploaded file-like object
        df = pd.read_csv(file)
        # Ensure the same schema as csv_loader requires
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date").reset_index(drop=True)
    return df

def init_state(df: pd.DataFrame):
    st.session_state.df = df
    st.session_state.i = 0
    st.session_state.cfg = SimConfig(
        cash=st.session_state.get("init_cash", 100000.0),
        fee_bps=st.session_state.get("init_fee_bps", 1.0),
        slip_bps=st.session_state.get("init_slip_bps", 2.0),
        policy=st.session_state.get("init_policy", "next_open"),
    )
    st.session_state.broker = Broker(st.session_state.cfg)
    # numpy arrays for speed
    st.session_state.open = df["Open"].to_numpy(float)
    st.session_state.high = df["High"].to_numpy(float)
    st.session_state.low  = df["Low"].to_numpy(float)
    st.session_state.close= df["Close"].to_numpy(float)
    st.session_state.vol  = df.get("Volume", pd.Series([np.nan]*len(df))).to_numpy(float)
    # indicators
    c = st.session_state.close
    # c = st.session_state.close
    h = st.session_state.high
    l = st.session_state.low

    # SMAs
    st.session_state.sma20  = sma(c, 20)
    st.session_state.sma50  = sma(c, 50)
    st.session_state.sma200 = sma(c, 200)

    # --- Keltner Channels (EMA20 ± 2*ATR10) ---
    kc_mid = ema(c, 20)
    atr10  = atr(h, l, c, 10)
    kc_mult = 2.0
    st.session_state.kc_mid = kc_mid
    st.session_state.kc_up  = kc_mid + kc_mult * atr10
    st.session_state.kc_dn  = kc_mid - kc_mult * atr10

    st.session_state.sma20  = sma(c, 20)
    st.session_state.sma50  = sma(c, 50)
    st.session_state.sma200 = sma(c, 200)
    st.session_state.rsi14  = rsi(c, 14)

def step_to(i: int):
    i = int(np.clip(i, 0, len(st.session_state.df)-1))
    # process bar i with broker
    st.session_state.broker.process_bar(
        i,
        st.session_state.open[i],
        st.session_state.high[i],
        st.session_state.low[i],
        st.session_state.close[i],
    )
    st.session_state.i = i



def plot_chart(i: int, show_volume: bool = True, show_keltner: bool = True):
    df = st.session_state.df
    sl = slice(0, i + 1)
    dfv = df.iloc[sl].copy()
    x = dfv["Date"]

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03,
        row_heights=[0.78, 0.22], specs=[[{"type": "xy"}], [{"type": "xy"}]]
    )

    # Candles (row 1)
    fig.add_trace(go.Candlestick(
        x=x,
        open=dfv["Open"], high=dfv["High"], low=dfv["Low"], close=dfv["Close"],
        increasing_line_color="rgb(0,176,116)", decreasing_line_color="rgb(235,83,80)",
        increasing_fillcolor="rgb(0,176,116)", decreasing_fillcolor="rgb(235,83,80)",
        name="OHLC", showlegend=False
    ), row=1, col=1)

    # SMAs (row 1)
    for arr, name, color in [
        (st.session_state.sma20[:i+1], "SMA20", "rgba(0,0,0,0.6)"),
        (st.session_state.sma50[:i+1], "SMA50", "rgba(31,119,180,1)"),
        (st.session_state.sma200[:i+1], "SMA200", "rgba(255,127,14,1)"),
    ]:
        fig.add_trace(go.Scatter(x=x, y=arr, mode="lines", name=name,
                                 line=dict(width=1.2, color=color)), row=1, col=1)

    # Keltner Channels (row 1)
    if show_keltner:
        up = st.session_state.kc_up[:i+1]
        mid = st.session_state.kc_mid[:i+1]
        dn = st.session_state.kc_dn[:i+1]

        # draw lower first, then upper with fill between
        fig.add_trace(go.Scatter(
            x=x, y=dn, mode="lines", name="KC Lower",
            line=dict(width=1.1, color="rgba(43,106,230,1)"), showlegend=False
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=x, y=up, mode="lines", name="KC Upper",
            line=dict(width=1.1, color="rgba(43,106,230,1)"),
            fill="tonexty", fillcolor="rgba(43,106,230,0.15)",
            showlegend=False
        ), row=1, col=1)
        # mid (optional thin line)
        fig.add_trace(go.Scatter(
            x=x, y=mid, mode="lines", name="KC Mid",
            line=dict(width=1.0, color="rgba(43,106,230,0.9)", dash="dot")
        ), row=1, col=1)

    # Volume in a separate pane (row 2)
    if show_volume:
        vols = st.session_state.vol[:i+1]
        ups  = st.session_state.close[:i+1] >= st.session_state.open[:i+1]
        colors = np.where(ups, "rgba(0,176,116,0.6)", "rgba(235,83,80,0.6)")
        fig.add_trace(go.Bar(
            x=x, y=vols, marker_color=colors, name="Volume",
            opacity=0.8
        ), row=2, col=1)

    fig.update_layout(
        height=600, template="plotly_white",
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis1=dict(rangeslider=dict(visible=False)),
        yaxis1=dict(title="Price", side="right"),
        yaxis2=dict(title="Volume", rangemode="tozero"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0.02),
    )
    return fig


# ---------- sidebar controls ----------
st.sidebar.header("Data & Simulation")
uploaded_csv = st.sidebar.file_uploader("Upload CSV (Date,Open,High,Low,Close,Volume)", type=["csv"])
use_sample = st.sidebar.checkbox("Use sample data", value=True if not uploaded_csv else False)

st.sidebar.subheader("Initial Settings")
st.session_state.init_cash = st.sidebar.number_input("Starting Cash", 1000.0, 1e9, 100000.0, step=1000.0)
st.session_state.init_fee_bps = st.sidebar.number_input("Fee (bps)", 0.0, 100.0, 1.0, step=0.5)
st.session_state.init_slip_bps = st.sidebar.number_input("Slippage (bps)", 0.0, 100.0, 2.0, step=0.5)
st.session_state.init_policy = st.sidebar.selectbox("Policy", ["next_open", "bar_inclusive"])

# Initialize state once DF is chosen
if "df" not in st.session_state or st.sidebar.button("Reset Session"):
    if uploaded_csv is not None:
        df = load_df(uploaded_csv)
    elif use_sample:
        df = load_df("backtester_p2/data/sample.csv")
    else:
        st.info("Upload a CSV or tick 'Use sample data'.")
        st.stop()
    init_state(df)

# ---------- main area ----------
df = st.session_state.df
i = st.session_state.i

col_top1, col_top2 = st.columns([3, 1], gap="large")

with col_top1:
    st.subheader("Chart")
    show_vol = st.checkbox("Show Volume", value=True, key="show_vol")
    show_kc  = st.checkbox("Show Keltner Channels", value=True, key="show_kc")
    fig = plot_chart(i, show_volume=show_vol, show_keltner=show_kc)
    st.plotly_chart(fig, use_container_width=True)
    # fig = plot_chart(i)
    # st.plotly_chart(fig, use_container_width=True)

with col_top2:
    st.subheader("Controls")
    # stepper
    step_cols = st.columns(3)
    if step_cols[0].button("⟵ Prev", use_container_width=True): step_to(i-1)
    if step_cols[1].button("Next ⟶", use_container_width=True): step_to(i+1)
    st.slider("Jump to bar", 1, len(df), i+1, key="jump", on_change=lambda: step_to(st.session_state.jump-1))

    st.divider()
    st.subheader("Order Entry (1 unit)")
    c1, c2 = st.columns(2)
    if c1.button("Buy MKT", use_container_width=True):
        st.session_state.broker.place(Order(ts_index=i, side=Side.BUY, qty=1.0, type=OrderType.MARKET))
    if c2.button("Sell MKT", use_container_width=True):
        st.session_state.broker.place(Order(ts_index=i, side=Side.SELL, qty=1.0, type=OrderType.MARKET))

    with st.expander("Limit / Stop"):
        lp = st.number_input("Limit Price", value=float(df["Close"].iloc[i]), format="%.4f")
        sp = st.number_input("Stop Price", value=float(df["Close"].iloc[i]), format="%.4f")
        lc1, lc2 = st.columns(2)
        if lc1.button("Buy LIMIT", use_container_width=True):
            st.session_state.broker.place(Order(ts_index=i, side=Side.BUY, qty=1.0, type=OrderType.LIMIT, limit_price=lp))
        if lc2.button("Sell LIMIT", use_container_width=True):
            st.session_state.broker.place(Order(ts_index=i, side=Side.SELL, qty=1.0, type=OrderType.LIMIT, limit_price=lp))
        sc1, sc2 = st.columns(2)
        if sc1.button("Buy STOP", use_container_width=True):
            st.session_state.broker.place(Order(ts_index=i, side=Side.BUY, qty=1.0, type=OrderType.STOP, stop_price=sp))
        if sc2.button("Sell STOP", use_container_width=True):
            st.session_state.broker.place(Order(ts_index=i, side=Side.SELL, qty=1.0, type=OrderType.STOP, stop_price=sp))

    if st.button("Cancel All", use_container_width=True):
        st.session_state.broker.cancel_all()

    st.divider()
    st.subheader("Account")
    s = st.session_state.broker.state
    st.metric("Equity", f"{s.equity:,.2f}")
    st.metric("Cash", f"{s.cash:,.2f}")
    st.metric("Position", f"{s.pos.qty:.4f} @ {s.pos.avg_price:.2f}")
    st.metric("Realized P&L", f"{s.pnl_realized:,.2f}")
    st.metric("Drawdown", f"{s.drawdown:,.2f}")

st.caption(f"Bar {i+1}/{len(df)}  —  O:{st.session_state.open[i]:.2f}  H:{st.session_state.high[i]:.2f}  L:{st.session_state.low[i]:.2f}  C:{st.session_state.close[i]:.2f}")
