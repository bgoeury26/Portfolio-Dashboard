import pandas as pd
import plotly.express as px
import streamlit as st

from utils.session_state import (
    get_optimized_weights,
    get_optimization_metadata,
    get_portfolio,
    initialize_session_state,
)

initialize_session_state()

st.header("Scenario Analysis")

df = get_portfolio()

if df is None:
    st.warning("Please upload a portfolio first in Portfolio Overview.")
    st.stop()

optimized_weights_df = get_optimized_weights()
optimization_metadata = get_optimization_metadata()

st.caption(f"Using active portfolio: {st.session_state['portfolio_filename']}")

scenario_df = df.copy()
scenario_df["CurrentWeight"] = scenario_df["PositionValue"] / scenario_df["PositionValue"].sum()

preset_scenarios = {
    "Custom": {"global": -10, "sector": "None", "sector_shock": -15, "currency": "None", "currency_shock": -5},
    "Risk-off": {"global": -12, "sector": "None", "sector_shock": 0, "currency": "None", "currency_shock": 0},
    "USD selloff": {"global": 0, "sector": "None", "sector_shock": 0, "currency": "USD", "currency_shock": -8},
    "Tech drawdown": {"global": -5, "sector": "Technology", "sector_shock": -20, "currency": "None", "currency_shock": 0},
}

st.subheader("Scenario Inputs")

preset_name = st.selectbox("Scenario preset", list(preset_scenarios.keys()))
preset = preset_scenarios[preset_name]

col1, col2, col3 = st.columns(3)

with col1:
    global_shock = st.slider(
        "Global portfolio shock (%)",
        min_value=-50,
        max_value=50,
        value=int(preset["global"]),
        step=1,
    )

available_sectors = sorted([s for s in scenario_df["sector"].dropna().unique().tolist()])
sector_default_index = 0
if preset["sector"] in ["None"] + available_sectors:
    sector_default_index = (["None"] + available_sectors).index(preset["sector"])

with col2:
    selected_sector = st.selectbox(
        "Sector shock target",
        options=["None"] + available_sectors,
        index=sector_default_index,
    )

with col3:
    sector_shock = st.slider(
        "Sector shock (%)",
        min_value=-50,
        max_value=50,
        value=int(preset["sector_shock"]),
        step=1,
    )

available_currencies = sorted(
    [c for c in scenario_df["CurrencyPrimary"].dropna().unique().tolist()]
)
currency_default_index = 0
if preset["currency"] in ["None"] + available_currencies:
    currency_default_index = (["None"] + available_currencies).index(preset["currency"])

col4, col5 = st.columns(2)

with col4:
    selected_currency = st.selectbox(
        "Currency shock target",
        options=["None"] + available_currencies,
        index=currency_default_index,
    )

with col5:
    currency_shock = st.slider(
        "Currency shock (%)",
        min_value=-30,
        max_value=30,
        value=int(preset["currency_shock"]),
        step=1,
    )


def apply_scenario(base_df, use_weight_column):
    work_df = base_df.copy()

    total_portfolio_value = work_df["PositionValue"].sum()

    if use_weight_column == "CurrentWeight":
        work_df["ScenarioBaseValue"] = work_df["PositionValue"]
    else:
        work_df["ScenarioBaseValue"] = total_portfolio_value * work_df[use_weight_column]

    work_df["GlobalShockPct"] = global_shock / 100
    work_df["SectorShockPct"] = 0.0
    work_df["CurrencyShockPct"] = 0.0

    if selected_sector != "None":
        work_df.loc[work_df["sector"] == selected_sector, "SectorShockPct"] = sector_shock / 100

    if selected_currency != "None":
        work_df.loc[work_df["CurrencyPrimary"] == selected_currency, "CurrencyShockPct"] = currency_shock / 100

    work_df["TotalShockPct"] = (
        work_df["GlobalShockPct"]
        + work_df["SectorShockPct"]
        + work_df["CurrencyShockPct"]
    )

    work_df["ShockedValue"] = work_df["ScenarioBaseValue"] * (1 + work_df["TotalShockPct"])
    work_df["ScenarioPnL"] = work_df["ShockedValue"] - work_df["ScenarioBaseValue"]

    return work_df


current_case_df = apply_scenario(scenario_df, "CurrentWeight")

comparison_summary = []

current_value = current_case_df["ScenarioBaseValue"].sum()
current_shocked = current_case_df["ShockedValue"].sum()
current_pnl = current_case_df["ScenarioPnL"].sum()

comparison_summary.append({
    "Portfolio": "Current",
    "BaseValue": current_value,
    "ShockedValue": current_shocked,
    "ScenarioPnL": current_pnl,
    "ScenarioPnLPct": (current_pnl / current_value * 100) if current_value != 0 else 0,
})

optimized_case_df = None

if optimized_weights_df is not None:
    merged_df = scenario_df.merge(
        optimized_weights_df[["Symbol", "OptimizedWeight"]],
        on="Symbol",
        how="left",
    )
    merged_df["OptimizedWeight"] = merged_df["OptimizedWeight"].fillna(0.0)

    if merged_df["OptimizedWeight"].sum() > 0:
        merged_df["OptimizedWeight"] = merged_df["OptimizedWeight"] / merged_df["OptimizedWeight"].sum()
        optimized_case_df = apply_scenario(merged_df, "OptimizedWeight")

        opt_value = optimized_case_df["ScenarioBaseValue"].sum()
        opt_shocked = optimized_case_df["ShockedValue"].sum()
        opt_pnl = optimized_case_df["ScenarioPnL"].sum()

        comparison_summary.append({
            "Portfolio": "Optimized",
            "BaseValue": opt_value,
            "ShockedValue": opt_shocked,
            "ScenarioPnL": opt_pnl,
            "ScenarioPnLPct": (opt_pnl / opt_value * 100) if opt_value != 0 else 0,
        })

summary_df = pd.DataFrame(comparison_summary)

st.subheader("Scenario Comparison")

if optimization_metadata is not None:
    st.caption(
        f"Optimized portfolio available: {optimization_metadata['optimization_method']} | "
        f"{optimization_metadata['lookback_period']} | rf={optimization_metadata['risk_free_rate']:.2%}"
    )

col_a, col_b, col_c = st.columns(3)

with col_a:
    st.metric("Current Portfolio Value", f"{current_value:,.2f}")

with col_b:
    st.metric("Current Shocked Value", f"{current_shocked:,.2f}")

with col_c:
    st.metric("Current Scenario Impact", f"{current_pnl:,.2f}", delta=f"{summary_df.loc[summary_df['Portfolio']=='Current', 'ScenarioPnLPct'].iloc[0]:.2f}%")

if len(summary_df) > 1:
    col_d, col_e, col_f = st.columns(3)

    with col_d:
        st.metric("Optimized Portfolio Value", f"{opt_value:,.2f}")

    with col_e:
        st.metric("Optimized Shocked Value", f"{opt_shocked:,.2f}")

    with col_f:
        st.metric("Optimized Scenario Impact", f"{opt_pnl:,.2f}", delta=f"{summary_df.loc[summary_df['Portfolio']=='Optimized', 'ScenarioPnLPct'].iloc[0]:.2f}%")
else:
    st.info("Run Optimization first to compare current vs optimized scenario outcomes.")

fig_compare = px.bar(
    summary_df,
    x="Portfolio",
    y="ScenarioPnL",
    color="Portfolio",
    title="Scenario P/L: Current vs Optimized",
    text_auto=".2s",
)
st.plotly_chart(fig_compare, use_container_width=True)

st.dataframe(
    summary_df.style.format({
        "BaseValue": "{:,.2f}",
        "ShockedValue": "{:,.2f}",
        "ScenarioPnL": "{:,.2f}",
        "ScenarioPnLPct": "{:.2f}%",
    }),
    use_container_width=True,
)

st.subheader("Current Portfolio Impact by Position")

position_impact_df = current_case_df[
    [
        "Symbol",
        "Description",
        "sector",
        "CurrencyPrimary",
        "ScenarioBaseValue",
        "ShockedValue",
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
        "ScenarioBaseValue": "{:,.2f}",
        "ShockedValue": "{:,.2f}",
        "ScenarioPnL": "{:,.2f}",
        "TotalShockPct": "{:.2f}%",
    }),
    use_container_width=True,
)

st.subheader("Current Portfolio Impact by Sector")

sector_impact_df = (
    current_case_df.groupby("sector", as_index=False)[["ScenarioBaseValue", "ShockedValue", "ScenarioPnL"]]
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
        "ScenarioBaseValue": "{:,.2f}",
        "ShockedValue": "{:,.2f}",
        "ScenarioPnL": "{:,.2f}",
    }),
    use_container_width=True,
)

st.subheader("Current Portfolio Impact by Currency")

currency_impact_df = (
    current_case_df.groupby("CurrencyPrimary", as_index=False)[["ScenarioBaseValue", "ShockedValue", "ScenarioPnL"]]
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
        "ScenarioBaseValue": "{:,.2f}",
        "ShockedValue": "{:,.2f}",
        "ScenarioPnL": "{:,.2f}",
    }),
    use_container_width=True,
)

st.subheader("Scenario Interpretation")

current_pct = summary_df.loc[summary_df["Portfolio"] == "Current", "ScenarioPnLPct"].iloc[0]

if current_pct <= -15:
    st.error("This scenario implies a severe drawdown for the current portfolio.")
elif current_pct <= -5:
    st.warning("This scenario implies a meaningful loss for the current portfolio.")
else:
    st.success("This scenario implies a limited impact on the current portfolio.")

if len(summary_df) > 1:
    optimized_pct = summary_df.loc[summary_df["Portfolio"] == "Optimized", "ScenarioPnLPct"].iloc[0]
    if optimized_pct > current_pct:
        st.success("The optimized portfolio is more resilient than the current portfolio under this scenario.")
    elif optimized_pct < current_pct:
        st.warning("The optimized portfolio performs worse than the current portfolio under this scenario.")
    else:
        st.info("The current and optimized portfolios react similarly under this scenario.")
