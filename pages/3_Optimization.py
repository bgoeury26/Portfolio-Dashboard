import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf
import cvxpy as cp

from utils.session_state import get_portfolio, initialize_session_state

initialize_session_state()

st.header("Optimization")

df = get_portfolio()

if df is None:
    st.warning("Please upload a portfolio first in Portfolio Overview.")
    st.stop()

st.caption(f"Using active portfolio: {st.session_state['portfolio_filename']}")

portfolio_df = df.copy()

portfolio_df["CurrentWeight"] = portfolio_df["PositionValue"] / portfolio_df["PositionValue"].sum()

st.subheader("Optimization Settings")

col1, col2, col3 = st.columns(3)

with col1:
    lookback_period = st.selectbox(
        "Historical window",
        options=["6mo", "1y", "2y", "5y"],
        index=1
    )

with col2:
    optimization_method = st.selectbox(
        "Objective",
        options=["Minimum Variance", "Maximum Sharpe"]
    )

with col3:
    risk_free_rate = st.number_input(
        "Risk-free rate",
        min_value=0.0,
        max_value=0.15,
        value=0.02,
        step=0.005
    )

tickers = portfolio_df["Symbol"].dropna().astype(str).unique().tolist()

st.write("Tickers used for optimization:", tickers)

@st.cache_data
def download_prices(tickers, period):
    prices = yf.download(tickers, period=period, auto_adjust=True, progress=False)["Close"]
    if isinstance(prices, pd.Series):
        prices = prices.to_frame()
    prices = prices.dropna(axis=1, how="all").dropna(how="any")
    return prices

try:
    prices = download_prices(tickers, lookback_period)
except Exception as e:
    st.error(f"Failed to download historical data: {e}")
    st.stop()

if prices.empty or prices.shape[1] < 2:
    st.error("Not enough valid historical price data to run optimization.")
    st.stop()

returns = prices.pct_change().dropna()

mean_returns = returns.mean() * 252
cov_matrix = returns.cov() * 252

valid_tickers = prices.columns.tolist()
opt_df = portfolio_df[portfolio_df["Symbol"].isin(valid_tickers)].copy()

current_weights = (
    opt_df.groupby("Symbol", as_index=False)["CurrentWeight"]
    .sum()
    .set_index("Symbol")
    .reindex(valid_tickers)
    .fillna(0)["CurrentWeight"]
    .values
)

n = len(valid_tickers)
w = cp.Variable(n)

portfolio_return = mean_returns.values @ w
portfolio_variance = cp.quad_form(w, cov_matrix.values)
portfolio_volatility = cp.sqrt(portfolio_variance)

constraints = [
    cp.sum(w) == 1,
    w >= 0,
]

if optimization_method == "Minimum Variance":
    objective = cp.Minimize(portfolio_variance)
else:
    objective = cp.Maximize((portfolio_return - risk_free_rate))

    constraints.append(portfolio_variance <= 1.0)

problem = cp.Problem(objective, constraints)

try:
    problem.solve()
except Exception as e:
    st.error(f"Optimization failed: {e}")
    st.stop()

if w.value is None:
    st.error("No optimization solution found.")
    st.stop()

optimized_weights = np.array(w.value).flatten()

comparison_df = pd.DataFrame({
    "Symbol": valid_tickers,
    "CurrentWeight": current_weights,
    "OptimizedWeight": optimized_weights,
})

comparison_df["CurrentWeightPct"] = comparison_df["CurrentWeight"] * 100
comparison_df["OptimizedWeightPct"] = comparison_df["OptimizedWeight"] * 100
comparison_df["WeightChangePct"] = (
    comparison_df["OptimizedWeightPct"] - comparison_df["CurrentWeightPct"]
)

comparison_df = comparison_df.sort_values("OptimizedWeightPct", ascending=False)

current_return = float(mean_returns.values @ current_weights)
current_vol = float(np.sqrt(current_weights.T @ cov_matrix.values @ current_weights))

opt_return = float(mean_returns.values @ optimized_weights)
opt_vol = float(np.sqrt(optimized_weights.T @ cov_matrix.values @ optimized_weights))

current_sharpe = (current_return - risk_free_rate) / current_vol if current_vol > 0 else np.nan
opt_sharpe = (opt_return - risk_free_rate) / opt_vol if opt_vol > 0 else np.nan

st.subheader("Optimization Summary")

m1, m2, m3 = st.columns(3)

with m1:
    st.metric("Current Return", f"{current_return:.2%}", delta=f"{opt_return - current_return:.2%}")

with m2:
    st.metric("Current Volatility", f"{current_vol:.2%}", delta=f"{opt_vol - current_vol:.2%}")

with m3:
    st.metric("Current Sharpe", f"{current_sharpe:.2f}", delta=f"{opt_sharpe - current_sharpe:.2f}")

m4, m5, m6 = st.columns(3)

with m4:
    st.metric("Optimized Return", f"{opt_return:.2%}")

with m5:
    st.metric("Optimized Volatility", f"{opt_vol:.2%}")

with m6:
    st.metric("Optimized Sharpe", f"{opt_sharpe:.2f}")

st.subheader("Current vs Optimized Weights")

chart_df = comparison_df.melt(
    id_vars="Symbol",
    value_vars=["CurrentWeightPct", "OptimizedWeightPct"],
    var_name="Portfolio",
    value_name="WeightPct"
)

fig_weights = px.bar(
    chart_df,
    x="Symbol",
    y="WeightPct",
    color="Portfolio",
    barmode="group",
    title="Current vs Optimized Allocation"
)
st.plotly_chart(fig_weights, use_container_width=True)

st.dataframe(
    comparison_df[
        ["Symbol", "CurrentWeightPct", "OptimizedWeightPct", "WeightChangePct"]
    ].style.format({
        "CurrentWeightPct": "{:.2f}%",
        "OptimizedWeightPct": "{:.2f}%",
        "WeightChangePct": "{:+.2f}%"
    }),
    use_container_width=True,
)

st.subheader("Historical Prices Used")
st.dataframe(prices.tail(), use_container_width=True)
