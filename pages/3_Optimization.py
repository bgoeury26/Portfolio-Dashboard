import utils.openbb_patch  # noqa: F401
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import cvxpy as cp
from datetime import date, timedelta

from openbb import obb

from utils.session_state import (
    get_portfolio,
    initialize_session_state,
    save_optimized_weights,
)

initialize_session_state()

st.header("Optimization")

df = get_portfolio()

if df is None:
    st.warning("Please upload a portfolio first in Portfolio Overview.")
    st.stop()

st.caption(f"Using active portfolio: {st.session_state['portfolio_filename']}")

portfolio_df = df.copy()
portfolio_df["CurrentWeight"] = (
    portfolio_df["PositionValue"] / portfolio_df["PositionValue"].sum()
)

# ── Settings ────────────────────────────────────────────────────────────────
st.subheader("Optimization Settings")

col1, col2, col3 = st.columns(3)

with col1:
    lookback_period = st.selectbox(
        "Historical window",
        options=["6mo", "1y", "2y", "5y"],
        index=1,
    )

with col2:
    optimization_method = st.selectbox(
        "Objective",
        options=["Minimum Variance", "Maximum Sharpe"],
    )

with col3:
    risk_free_rate = st.number_input(
        "Risk-free rate",
        min_value=0.0,
        max_value=0.15,
        value=0.04,
        step=0.005,
    )

# ── Period → dates ───────────────────────────────────────────────────────────
PERIOD_DAYS = {"6mo": 183, "1y": 365, "2y": 730, "5y": 1825}
end_date   = date.today()
start_date = end_date - timedelta(days=PERIOD_DAYS[lookback_period])

# ── Symbol mapping: IBKR → OpenBB/Yahoo compatible ──────────────────────────
SYMBOL_MAP = {
    "SXR8":    ["SXR8.DE", "SXR8.L"],
    "ISF":     ["ISF.L"],
    "BTCWUSD": ["BTC-USD"],
    "PHAG":    ["PHAG.L"],
    "ARMR":    ["ARMR.L", "ARMR"],
    "ENT":     ["ENT.L"],
    "2RR":     ["2RR.L"],
}

tickers_raw = portfolio_df["Symbol"].dropna().astype(str).unique().tolist()
st.write("IBKR symbols detected:", tickers_raw)


# ── OpenBB price fetch ───────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_prices_openbb(tickers_raw, start_str, end_str):
    valid_data     = {}
    failed_tickers = []

    for raw in tickers_raw:
        # Build candidate list: mapped first, then raw, then common exchange suffixes
        candidates = list(SYMBOL_MAP.get(raw, []))
        if raw not in candidates:
            candidates.append(raw)
        for suffix in [".L", ".DE", ".PA", ".AS", ".MI"]:
            candidate = f"{raw}{suffix}"
            if candidate not in candidates:
                candidates.append(candidate)

        success = False
        for candidate in candidates:
            try:
                result = obb.equity.price.historical(
                    candidate,
                    start_date=start_str,
                    end_date=end_str,
                    provider="yfinance",
                    interval="1d",
                )
                df_raw = result.to_dataframe()
                if df_raw is None or df_raw.empty:
                    continue
                df_raw.columns = [c.lower() for c in df_raw.columns]
                if "close" not in df_raw.columns:
                    continue
                series = pd.to_numeric(df_raw["close"], errors="coerce").dropna()
                series.index = pd.to_datetime(series.index, errors="coerce")
                series = series[~series.index.isna()].sort_index()
                if len(series) < 30:
                    continue
                # Store under the original IBKR symbol name
                valid_data[raw] = series.rename(raw)
                success = True
                break
            except Exception:
                continue

        if not success:
            failed_tickers.append(raw)

    if not valid_data:
        return pd.DataFrame(), [], failed_tickers

    # Concat WITHOUT forcing alignment — each ticker keeps its own trading days
    prices = pd.concat(valid_data.values(), axis=1, sort=True)
    prices = prices.dropna(how="all")   # only drop rows where ALL tickers are NaN

    valid_tickers  = list(prices.columns)
    failed_tickers = [s for s in tickers_raw if s not in valid_tickers]

    return prices, valid_tickers, failed_tickers


if st.button("🔄 Refresh market data"):
    fetch_prices_openbb.clear()
    st.rerun()

with st.spinner("Fetching price data via OpenBB…"):
    prices, valid_tickers, failed_tickers = fetch_prices_openbb(
        tuple(tickers_raw),
        start_date.isoformat(),
        end_date.isoformat(),
    )

# ── Ticker Validation ────────────────────────────────────────────────────────
st.subheader("Ticker Validation")

col_a, col_b = st.columns(2)
with col_a:
    st.metric("Valid tickers", len(valid_tickers))
with col_b:
    st.metric("Excluded tickers", len(failed_tickers))

if valid_tickers:
    st.success("✅ Valid tickers: " + ", ".join(valid_tickers))

if failed_tickers:
    st.warning("⚠️ Excluded (no data found): " + ", ".join(failed_tickers))

if prices.empty or len(valid_tickers) < 2:
    st.error(
        "Not enough valid historical price data to run optimization. "
        "Need at least 2 valid tickers."
    )
    st.stop()

# ── Per-ticker returns (each uses its own full history) ──────────────────────
returns_dict = {}
for col in prices.columns:
    s = prices[col].dropna()               # each ticker: only its own trading days
    if len(s) < 30:
        continue
    r = s.pct_change().dropna()
    r = r.replace([np.inf, -np.inf], np.nan).dropna()
    if not r.empty:
        returns_dict[col] = r

if not returns_dict:
    st.error("No usable return series after cleaning price data.")
    st.stop()

# Annualised mean return per ticker — uses each ticker's own full history
mean_returns = pd.Series({
    ticker: r.mean() * 252
    for ticker, r in returns_dict.items()
})

# Covariance: align on shared dates, ffill exchange holiday gaps
returns_df = pd.DataFrame(returns_dict)
returns_df = returns_df.ffill().bfill()
returns_df = returns_df.dropna(how="all")
cov_matrix = returns_df.cov() * 252

# Re-align everything to tickers that survived returns cleaning
valid_tickers = list(mean_returns.index)
prices        = prices[valid_tickers]

if len(valid_tickers) < 2:
    st.error("Not enough tickers with valid return data. Try a longer historical window.")
    st.stop()

# ── Current weights ──────────────────────────────────────────────────────────
opt_df = portfolio_df[portfolio_df["Symbol"].isin(valid_tickers)].copy()

current_weights_series = (
    opt_df.groupby("Symbol", as_index=False)["CurrentWeight"]
    .sum()
    .set_index("Symbol")
    .reindex(valid_tickers)
    .fillna(0)["CurrentWeight"]
)

current_weights = current_weights_series.values
w_sum = current_weights.sum()
current_weights = (
    current_weights / w_sum
    if w_sum > 0
    else np.ones(len(valid_tickers)) / len(valid_tickers)
)

# ── Optimisation (cvxpy) ─────────────────────────────────────────────────────
n = len(valid_tickers)
w = cp.Variable(n)

portfolio_return   = mean_returns.values @ w
portfolio_variance = cp.quad_form(w, cov_matrix.values)

constraints = [cp.sum(w) == 1, w >= 0]

if optimization_method == "Minimum Variance":
    objective = cp.Minimize(portfolio_variance)
else:
    objective = cp.Maximize(portfolio_return - risk_free_rate * cp.sum(w))

problem = cp.Problem(objective, constraints)

try:
    problem.solve()
except Exception as e:
    st.error(f"Optimisation solver error: {e}")
    st.stop()

if w.value is None:
    st.error("Solver returned no solution. Try a different window or objective.")
    st.stop()

optimized_weights = np.array(w.value).flatten()

# ── Save results ─────────────────────────────────────────────────────────────
comparison_df = pd.DataFrame({
    "Symbol":          valid_tickers,
    "CurrentWeight":   current_weights,
    "OptimizedWeight": optimized_weights,
})

save_optimized_weights(
    comparison_df[["Symbol", "CurrentWeight", "OptimizedWeight"]].copy(),
    metadata={
        "lookback_period":     lookback_period,
        "optimization_method": optimization_method,
        "risk_free_rate":      risk_free_rate,
        "valid_tickers":       valid_tickers,
    },
)

comparison_df["CurrentWeightPct"]   = comparison_df["CurrentWeight"]   * 100
comparison_df["OptimizedWeightPct"] = comparison_df["OptimizedWeight"] * 100
comparison_df["WeightChangePct"]    = (
    comparison_df["OptimizedWeightPct"] - comparison_df["CurrentWeightPct"]
)
comparison_df = comparison_df.sort_values("OptimizedWeightPct", ascending=False)

# ── Portfolio statistics ─────────────────────────────────────────────────────
current_return = float(mean_returns.values @ current_weights)
current_vol    = float(np.sqrt(current_weights @ cov_matrix.values @ current_weights))
opt_return     = float(mean_returns.values @ optimized_weights)
opt_vol        = float(np.sqrt(optimized_weights @ cov_matrix.values @ optimized_weights))

current_sharpe = (
    (current_return - risk_free_rate) / current_vol if current_vol > 0 else np.nan
)
opt_sharpe = (
    (opt_return - risk_free_rate) / opt_vol if opt_vol > 0 else np.nan
)

# ── Display ──────────────────────────────────────────────────────────────────
st.subheader("Optimization Summary")

m1, m2, m3 = st.columns(3)
with m1:
    st.metric(
        "Current Return", f"{current_return:.2%}",
        delta=f"{opt_return - current_return:.2%}",
    )
with m2:
    st.metric(
        "Current Volatility", f"{current_vol:.2%}",
        delta=f"{opt_vol - current_vol:.2%}",
    )
with m3:
    st.metric(
        "Current Sharpe", f"{current_sharpe:.2f}",
        delta=f"{opt_sharpe - current_sharpe:.2f}",
    )

m4, m5, m6 = st.columns(3)
with m4:
    st.metric("Optimized Return",     f"{opt_return:.2%}")
with m5:
    st.metric("Optimized Volatility", f"{opt_vol:.2%}")
with m6:
    st.metric("Optimized Sharpe",     f"{opt_sharpe:.2f}")

st.subheader("Current vs Optimized Weights")

chart_df = comparison_df.melt(
    id_vars="Symbol",
    value_vars=["CurrentWeightPct", "OptimizedWeightPct"],
    var_name="Portfolio",
    value_name="WeightPct",
)

fig_weights = px.bar(
    chart_df,
    x="Symbol",
    y="WeightPct",
    color="Portfolio",
    barmode="group",
    title="Current vs Optimized Allocation (%)",
    labels={"WeightPct": "Weight (%)", "Symbol": ""},
)
st.plotly_chart(fig_weights, use_container_width=True)

st.dataframe(
    comparison_df[
        ["Symbol", "CurrentWeightPct", "OptimizedWeightPct", "WeightChangePct"]
    ].style.format({
        "CurrentWeightPct":   "{:.2f}%",
        "OptimizedWeightPct": "{:.2f}%",
        "WeightChangePct":    "{:+.2f}%",
    }),
    use_container_width=True,
)

st.subheader("Historical Prices Used")
st.dataframe(prices.tail(10), use_container_width=True)
