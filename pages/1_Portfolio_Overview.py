import streamlit as st
import plotly.express as px

from utils.data_loader import load_ibkr_positions
from utils.session_state import (
    clear_portfolio,
    get_portfolio,
    initialize_session_state,
    save_portfolio,
)

initialize_session_state()

st.header("📊 Portfolio Overview")

uploaded_file = st.file_uploader("Upload IBKR Positions CSV", type=["csv"])

if uploaded_file is not None:
    df = load_ibkr_positions(uploaded_file)
    save_portfolio(df, uploaded_file.name)
    st.success(f"Loaded portfolio file: {uploaded_file.name}")

df = get_portfolio()

if st.session_state["portfolio_loaded"] and df is not None:
    col_a, col_b = st.columns([4, 1])

    with col_a:
        st.caption(f"Active portfolio file: {st.session_state['portfolio_filename']}")

    with col_b:
        if st.button("Clear portfolio"):
            clear_portfolio()
            st.rerun()

    total_value = df["PositionValue"].sum()
    total_unrealized = df["FifoPnlUnrealized"].sum()
    largest_position = df["PercentOfNAV"].max()
    total_positions = int(df["Symbol"].nunique())

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Portfolio Value", f"{total_value:,.2f}")

    with col2:
        st.metric("Unrealized P/L", f"{total_unrealized:,.2f}")

    with col3:
        st.metric("Positions", total_positions)

    with col4:
        st.metric("Largest Position %", f"{largest_position:,.2f}%")

    pie_df = df.groupby("Symbol", as_index=False)["PositionValue"].sum()
    fig_pie = px.pie(
        pie_df,
        values="PositionValue",
        names="Symbol",
        title="Holdings Allocation",
    )
    st.plotly_chart(fig_pie, use_container_width=True)

    sector_df = df.groupby("sector", as_index=False)["PositionValue"].sum()
    fig_sector = px.bar(
        sector_df,
        x="sector",
        y="PositionValue",
        title="Sector Exposure",
    )
    st.plotly_chart(fig_sector, use_container_width=True)

    currency_df = df.groupby("CurrencyPrimary", as_index=False)["PositionValue"].sum()
    fig_currency = px.bar(
        currency_df,
        x="CurrencyPrimary",
        y="PositionValue",
        title="Currency Exposure",
    )
    st.plotly_chart(fig_currency, use_container_width=True)

    st.subheader("Positions")

    display_df = df[
        [
            "Symbol",
            "Description",
            "CurrencyPrimary",
            "AssetClass",
            "SubCategory",
            "Quantity",
            "MarkPrice",
            "PositionValue",
            "PercentOfNAV",
            "CostBasisPrice",
            "CostBasisMoney",
            "FifoPnlUnrealized",
            "PnLPercent",
            "ISIN",
        ]
    ].copy()

    display_df["PercentOfNAV"] = display_df["PercentOfNAV"].map(lambda x: f"{x:.2f}%")
    display_df["PnLPercent"] = display_df["PnLPercent"].map(
        lambda x: f"{x:.2f}%" if x == x else ""
    )

    st.dataframe(display_df, use_container_width=True)

else:
    st.info("Upload your IBKR Flex Query CSV to begin.")
