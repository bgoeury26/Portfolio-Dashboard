import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import date, timedelta

from openbb import obb

from utils.session_state import (
    get_portfolio,
    initialize_session_state,
)

st.set_page_config(page_title="Monte Carlo", page_icon="🎲", layout="wide")
initialize_session_state()

st.title("Monte Carlo Simulation")

# ── Load portfolio (identical pattern to Optimization page) ──────────────────
df = get_portfolio()
if df is None or df.empty:
    st.warning("No portfolio loaded. Please upload your IBKR CSV on the **Portfolio Overview** page first.")
    st.stop()

st.caption(f"Using active portfolio: {st.session_state['portfolio_filename']}")

# ── Simulation Settings ──────────────────────────────────────────────────────
st.subheader("Simulation Settings")
col1, col2, col3 = st.columns(3)
with col1:
    horizon = st.slider("Simulation horizon (trading days)", 21, 504, 252)
with col2:
    n_sims = st.slider("Number of simulations", 500, 10000, 3000, step=500)
with col3:
    init_val = st.number_input("Initial portfolio value ($)", value=100000, step=1000)

window = st.selectbox("Historical window", ["1Y", "2Y", "3Y", "5Y"], index=1)
st.checkbox("Refresh market data", value=True)

WINDOW_MAP = {"1Y": "1year", "2Y": "2year", "3Y": "3year", "5Y": "5year"}

# ── Extract tickers (identical pattern to Optimization page) ─────────────────
tickers = df["Symbol"].dropna().unique().tolist()

# ── Fetch prices via OpenBB per-ticker (identical to Optimization page) ───────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_prices_openbb(tickers_tuple: tuple, window: str) -> tuple:
    period = WINDOW_MAP.get(window, "1year")
    frames = []
    excluded = []
    for ticker in tickers_tuple:
        try:
            raw = obb.equity.price.historical(
                symbol=ticker,
                period=period,
                provider="yfinance",
            )
            tmp = raw.to_df()
            if tmp.empty:
                excluded.append(ticker)
                continue
            tmp = tmp[["close"]].rename(columns={"close": ticker})
            frames.append(tmp)
        except Exception:
            excluded.append(ticker)
    if not frames:
        return pd.DataFrame(), excluded
    prices = pd.concat(frames, axis=1).dropna(how="all")
    return prices, excluded

with st.spinner("Fetching price data via OpenBB…"):
    prices, excluded = fetch_prices_openbb(tuple(tickers), window)

if excluded:
    st.info(f"**Excluded symbols** (no data from OpenBB/yfinance): {', '.join(excluded)}")

valid_tickers = [t for t in tickers if t in prices.columns]

if len(valid_tickers) < 2:
    st.error(f"Only {len(valid_tickers)} ticker(s) could be resolved. Need at least 2 to run simulation.")
    st.info(
        "**Tip:** European ETFs (ISF, SXR8, PHAG, etc.) are not listed on Yahoo Finance. "
        "Try appending an exchange suffix in your holdings CSV, e.g. `SXR8.DE`, `ISF.L`, `PHAG.L`."
    )
    st.stop()

prices = prices[valid_tickers].ffill().dropna()

# ── Build weights from portfolio ─────────────────────────────────────────────
port = df[df["Symbol"].isin(valid_tickers)].copy()
port["_w"] = port["PositionValue"].abs() / port["PositionValue"].abs().sum()
weights = port.set_index("Symbol")["_w"].reindex(valid_tickers).fillna(0).values
weights = weights / weights.sum()

# ── Monte Carlo engine ────────────────────────────────────────────────────────
returns = prices.pct_change().dropna()
mu  = returns.mean().values
cov = returns.cov().values

np.random.seed(42)
sims = np.zeros((horizon, n_sims))
for i in range(n_sims):
    daily_rets = np.random.multivariate_normal(mu, cov, horizon)
    port_rets  = daily_rets @ weights
    sims[:, i] = init_val * np.cumprod(1 + port_rets)

final_vals = sims[-1]
p5  = np.percentile(final_vals, 5)
p50 = np.percentile(final_vals, 50)
p95 = np.percentile(final_vals, 95)

# ── KPI row ───────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Median outcome",         f"${p50:,.0f}", f"{(p50/init_val-1)*100:+.1f}%")
k2.metric("5th pct (downside VaR)", f"${p5:,.0f}",  f"{(p5/init_val-1)*100:+.1f}%")
k3.metric("95th pct (upside)",      f"${p95:,.0f}", f"{(p95/init_val-1)*100:+.1f}%")
k4.metric("Prob. of loss",          f"{(final_vals < init_val).mean()*100:.1f}%")

# ── Simulation fan chart ──────────────────────────────────────────────────────
sample_idx = np.random.choice(n_sims, min(300, n_sims), replace=False)
fig = go.Figure()
for i in sample_idx:
    fig.add_trace(go.Scatter(
        y=sims[:, i], mode="lines",
        line=dict(width=0.5, color="rgba(180,180,255,0.12)"),
        showlegend=False, hoverinfo="skip",
    ))
for val, name, color in [(p5, "5th pct", "tomato"), (p50, "Median", "white"), (p95, "95th pct", "limegreen")]:
    fig.add_hline(y=val, line_dash="dash", line_color=color,
                  annotation_text=f"{name}: ${val:,.0f}",
                  annotation_font_color=color)
fig.update_layout(
    title=f"Monte Carlo — {n_sims:,} simulations × {horizon} trading days ({len(valid_tickers)} tickers)",
    xaxis_title="Trading Days", yaxis_title="Portfolio Value ($)",
    template="plotly_dark", height=500,
)
st.plotly_chart(fig, use_container_width=True)

# ── Distribution of final values ─────────────────────────────────────────────
fig2 = go.Figure()
fig2.add_trace(go.Histogram(x=final_vals, nbinsx=80,
                            marker_color="steelblue", opacity=0.85))
fig2.add_vline(x=init_val, line_dash="dash", line_color="gold",
               annotation_text="Initial Value", annotation_font_color="gold")
fig2.add_vline(x=p5,  line_dash="dash", line_color="tomato",
               annotation_text="5th pct", annotation_font_color="tomato")
fig2.add_vline(x=p50, line_dash="dash", line_color="white",
               annotation_text="Median",  annotation_font_color="white")
fig2.update_layout(
    title="Distribution of Final Portfolio Values",
    xaxis_title="Portfolio Value ($)", yaxis_title="Frequency",
    template="plotly_dark", height=400,
)
st.plotly_chart(fig2, use_container_width=True)
