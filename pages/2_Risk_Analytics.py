import pandas as pd
import plotly.express as px
import streamlit as st

from utils.session_state import get_portfolio, initialize_session_state

initialize_session_state()

st.header("Risk Analytics")

df = get_portfolio()

if df is None:
    st.warning("Please upload a portfolio first in Portfolio Overview.")
    st.stop()

st.caption(f"Using active portfolio: {st.session_state['portfolio_filename']}")

risk_df = df.copy()

risk_df["weight_decimal"] = risk_df["PercentOfNAV"] / 100
risk_df["abs_weight_decimal"] = risk_df["weight_decimal"].abs()

hhi = (risk_df["abs_weight_decimal"] ** 2).sum()
effective_n = 1 / hhi if hhi > 0 else 0

top_5_weight = risk_df.nlargest(5, "PercentOfNAV")["PercentOfNAV"].sum()
top_10_weight = risk_df.nlargest(min(10, len(risk_df)), "PercentOfNAV")["PercentOfNAV"].sum()
largest_position = risk_df["PercentOfNAV"].max()
position_count = risk_df["Symbol"].nunique()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Positions", int(position_count))

with col2:
    st.metric("Largest Position", f"{largest_position:.2f}%")

with col3:
    st.metric("Top 5 Weight", f"{top_5_weight:.2f}%")

with col4:
    st.metric("Effective Holdings", f"{effective_n:.2f}")

col5, col6 = st.columns(2)

with col5:
    st.metric("Top 10 Weight", f"{top_10_weight:.2f}%")

with col6:
    st.metric("HHI Concentration", f"{hhi:.4f}")

st.subheader("Exposure Breakdown")

sector_df = (
    risk_df.groupby("sector", as_index=False)["PositionValue"]
    .sum()
    .sort_values("PositionValue", ascending=False)
)
fig_sector = px.bar(
    sector_df,
    x="sector",
    y="PositionValue",
    title="Sector Exposure",
    text_auto=".2s",
)
st.plotly_chart(fig_sector, use_container_width=True)

col_a, col_b = st.columns(2)

with col_a:
    currency_df = (
        risk_df.groupby("CurrencyPrimary", as_index=False)["PositionValue"]
        .sum()
        .sort_values("PositionValue", ascending=False)
    )
    fig_currency = px.pie(
        currency_df,
        values="PositionValue",
        names="CurrencyPrimary",
        title="Currency Exposure",
    )
    st.plotly_chart(fig_currency, use_container_width=True)

with col_b:
    asset_df = (
        risk_df.groupby("AssetClass", as_index=False)["PositionValue"]
        .sum()
        .sort_values("PositionValue", ascending=False)
    )
    fig_asset = px.pie(
        asset_df,
        values="PositionValue",
        names="AssetClass",
        title="Asset Class Exposure",
    )
    st.plotly_chart(fig_asset, use_container_width=True)

st.subheader("Top Holdings Risk")

top_holdings = risk_df.sort_values("PercentOfNAV", ascending=False).copy()
top_holdings["PercentOfNAV"] = top_holdings["PercentOfNAV"].map(lambda x: f"{x:.2f}%")
top_holdings["PnLPercent"] = top_holdings["PnLPercent"].map(
    lambda x: f"{x:.2f}%" if pd.notna(x) else ""
)

st.dataframe(
    top_holdings[
        [
            "Symbol",
            "Description",
            "CurrencyPrimary",
            "sector",
            "Quantity",
            "PositionValue",
            "PercentOfNAV",
            "FifoPnlUnrealized",
            "PnLPercent",
        ]
    ],
    use_container_width=True,
)

st.subheader("Risk Interpretation")

if largest_position >= 10:
    st.error("Largest position exceeds 10% of NAV: concentration risk is elevated.")
elif largest_position >= 5:
    st.warning("Largest position exceeds 5% of NAV: monitor single-name concentration.")
else:
    st.success("Largest position concentration is moderate.")

if effective_n < 10:
    st.error("Effective number of holdings is below 10: diversification is weak.")
elif effective_n < 20:
    st.warning("Effective number of holdings is below 20: diversification is moderate.")
else:
    st.success("Effective number of holdings suggests reasonable diversification.")
