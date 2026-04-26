import utils.openbb_patch  # noqa: F401
import pandas as pd
import plotly.express as px
import streamlit as st

from utils.market_data import build_rebalance_table, compute_turnover_from_rebalance
from utils.session_state import (
    get_optimized_weights,
    get_portfolio,
    initialize_session_state,
)

initialize_session_state()

st.header("Rebalancing Planner")

portfolio_df = get_portfolio()
optimized_weights_df = get_optimized_weights()

if portfolio_df is None:
    st.warning("Please upload a portfolio first in Portfolio Overview.")
    st.stop()

if optimized_weights_df is None:
    st.warning("Please run Optimization first so target weights are available.")
    st.stop()

total_portfolio_value = portfolio_df["PositionValue"].sum()

current_weights = (
    portfolio_df.groupby("Symbol")["PositionValue"]
    .sum()
)
current_weights = current_weights / current_weights.sum()

target_weights = (
    optimized_weights_df.groupby("Symbol")["OptimizedWeight"]
    .sum()
)
target_weights = target_weights / target_weights.sum()

rebalance_df = build_rebalance_table(
    current_weights=current_weights,
    target_weights=target_weights,
    total_portfolio_value=total_portfolio_value,
)

turnover_value = compute_turnover_from_rebalance(rebalance_df)
turnover_pct = turnover_value / total_portfolio_value if total_portfolio_value != 0 else 0.0

buy_value = rebalance_df.loc[rebalance_df["TradeValue"] > 0, "TradeValue"].sum()
sell_value = -rebalance_df.loc[rebalance_df["TradeValue"] < 0, "TradeValue"].sum()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Portfolio Value", f"{total_portfolio_value:,.2f}")

with col2:
    st.metric("Estimated Buys", f"{buy_value:,.2f}")

with col3:
    st.metric("Estimated Sells", f"{sell_value:,.2f}")

with col4:
    st.metric("Turnover", f"{turnover_pct:.2%}")

st.subheader("Rebalancing Table")

st.dataframe(
    rebalance_df.style.format({
        "CurrentWeight": "{:.2%}",
        "TargetWeight": "{:.2%}",
        "ActiveWeight": "{:+.2%}",
        "CurrentValue": "{:,.2f}",
        "TargetValue": "{:,.2f}",
        "TradeValue": "{:+,.2f}",
    }),
    use_container_width=True,
)

st.subheader("Largest Required Trades")

largest_trades = rebalance_df.reindex(
    rebalance_df["TradeValue"].abs().sort_values(ascending=False).index
).head(15)

fig_trades = px.bar(
    largest_trades,
    x="Symbol",
    y="TradeValue",
    color="TradeAction",
    title="Largest Required Trades to Reach Target Weights",
    text_auto=".2s",
)
st.plotly_chart(fig_trades, use_container_width=True)

st.subheader("Weight Drift")

fig_drift = px.bar(
    rebalance_df,
    x="Symbol",
    y="ActiveWeight",
    color="TradeAction",
    title="Target Minus Current Weight by Position",
    text_auto=".2%",
)
st.plotly_chart(fig_drift, use_container_width=True)

st.subheader("Rebalancing Notes")

if turnover_pct > 0.30:
    st.warning("This rebalance implies high turnover versus the current portfolio.")
elif turnover_pct > 0.10:
    st.info("This rebalance implies moderate turnover.")
else:
    st.success("This rebalance implies relatively limited turnover.")

largest_buy = rebalance_df.loc[rebalance_df["TradeValue"].idxmax()]
largest_sell = rebalance_df.loc[rebalance_df["TradeValue"].idxmin()]

st.write(
    f"Largest buy candidate: {largest_buy['Symbol']} ({largest_buy['TradeValue']:,.2f})."
)
st.write(
    f"Largest sell candidate: {largest_sell['Symbol']} ({largest_sell['TradeValue']:,.2f})."
)
