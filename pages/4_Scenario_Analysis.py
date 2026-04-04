import pandas as pd
import plotly.express as px
import streamlit as st

from utils.session_state import get_portfolio, initialize_session_state

initialize_session_state()

st.header("Scenario Analysis")

df = get_portfolio()

if df is None:
    st.warning("Please upload a portfolio first in Portfolio Overview.")
    st.stop()

st.caption(f"Using active portfolio: {st.session_state['portfolio_filename']}")

scenario_df = df.copy()

st.subheader("Scenario Inputs")

col1, col2, col3 = st.columns(3)

with col1:
    global_shock = st.slider(
        "Global portfolio shock (%)",
        min_value=-50,
        max_value=50,
        value=-10,
        step=1,
    )

with col2:
    available_sectors = sorted([s for s in scenario_df["sector"].dropna().unique().tolist()])
    selected_sector = st.selectbox("Sector shock target", options=["None"] + available_sectors)

with col3:
    sector_shock = st.slider(
        "Sector shock (%)",
        min_value=-50,
        max_value=50,
        value=-15,
        step=1,
    )

col4, col5 = st.columns(2)

with col4:
    available_currencies = sorted(
        [c for c in scenario_df["CurrencyPrimary"].dropna().unique().tolist()]
    )
    selected_currency = st.selectbox(
        "Currency shock target",
        options=["None"] + available_currencies,
    )

with col5:
    currency_shock = st.slider(
        "Currency shock (%)",
        min_value=-30,
        max_value=30,
        value=-5,
        step=1,
    )

scenario_df["GlobalShockPct"] = global_shock / 100
scenario_df["SectorShockPct"] = 0.0
scenario_df["CurrencyShockPct"] = 0.0

if selected_sector != "None":
    scenario_df.loc[scenario_df["sector"] == selected_sector, "SectorShockPct"] = sector_shock / 100

if selected_currency != "None":
    scenario_df.loc[
        scenario_df["CurrencyPrimary"] == selected_currency, "CurrencyShockPct"
    ] = currency_shock / 100

scenario_df["TotalShockPct"] = (
    scenario_df["GlobalShockPct"]
    + scenario_df["SectorShockPct"]
    + scenario_df["CurrencyShockPct"]
)

scenario_df["ShockedPositionValue"] = scenario_df["PositionValue"] * (1 + scenario_df["TotalShockPct"])
scenario_df["ScenarioPnL"] = scenario_df["ShockedPositionValue"] - scenario_df["PositionValue"]

current_portfolio_value = scenario_df["PositionValue"].sum()
shocked_portfolio_value = scenario_df["ShockedPositionValue"].sum()
portfolio_impact = shocked_portfolio_value - current_portfolio_value
portfolio_impact_pct = portfolio_impact / current_portfolio_value * 100 if current_portfolio_value != 0 else 0

col_a, col_b, col_c = st.columns(3)

with col_a:
    st.metric("Current Portfolio Value", f"{current_portfolio_value:,.2f}")

with col_b:
    st.metric("Shocked Portfolio Value", f"{shocked_portfolio_value:,.2f}")

with col_c:
    st.metric("Scenario Impact", f"{portfolio_impact:,.2f}", delta=f"{portfolio_impact_pct:.2f}%")

st.subheader("Impact by Position")

position_impact_df = scenario_df[
    [
        "Symbol",
        "Description",
        "sector",
        "CurrencyPrimary",
        "PositionValue",
        "ShockedPositionValue",
        "ScenarioPnL",
        "TotalShockPct",
    ]
].copy()

position_impact_df["TotalShockPct"] = position_impact_df["TotalShockPct"] * 100
position_impact_df = position_impact_df.sort_values("ScenarioPnL", ascending=True)

fig_positions = px.bar(
    position_impact_df.head(15),
    x="Symbol",
    y="ScenarioPnL",
    color="sector",
    title="Largest Negative Position Impacts",
    text_auto=".2s",
)
st.plotly_chart(fig_positions, use_container_width=True)

st.dataframe(
    position_impact_df.style.format({
        "PositionValue": "{:,.2f}",
        "ShockedPositionValue": "{:,.2f}",
        "ScenarioPnL": "{:,.2f}",
        "TotalShockPct": "{:.2f}%",
    }),
    use_container_width=True,
)

st.subheader("Impact by Sector")

sector_impact_df = (
    scenario_df.groupby("sector", as_index=False)[["PositionValue", "ShockedPositionValue", "ScenarioPnL"]]
    .sum()
    .sort_values("ScenarioPnL", ascending=True)
)

fig_sector = px.bar(
    sector_impact_df,
    x="sector",
    y="ScenarioPnL",
    title="Scenario P/L by Sector",
    text_auto=".2s",
)
st.plotly_chart(fig_sector, use_container_width=True)

st.dataframe(
    sector_impact_df.style.format({
        "PositionValue": "{:,.2f}",
        "ShockedPositionValue": "{:,.2f}",
        "ScenarioPnL": "{:,.2f}",
    }),
    use_container_width=True,
)

st.subheader("Impact by Currency")

currency_impact_df = (
    scenario_df.groupby("CurrencyPrimary", as_index=False)[["PositionValue", "ShockedPositionValue", "ScenarioPnL"]]
    .sum()
    .sort_values("ScenarioPnL", ascending=True)
)

fig_currency = px.bar(
    currency_impact_df,
    x="CurrencyPrimary",
    y="ScenarioPnL",
    title="Scenario P/L by Currency",
    text_auto=".2s",
)
st.plotly_chart(fig_currency, use_container_width=True)

st.dataframe(
    currency_impact_df.style.format({
        "PositionValue": "{:,.2f}",
        "ShockedPositionValue": "{:,.2f}",
        "ScenarioPnL": "{:,.2f}",
    }),
    use_container_width=True,
)

st.subheader("Scenario Interpretation")

if portfolio_impact_pct <= -15:
    st.error("This scenario implies a severe portfolio drawdown.")
elif portfolio_impact_pct <= -5:
    st.warning("This scenario implies a meaningful portfolio loss.")
else:
    st.success("This scenario implies a limited portfolio impact.")
