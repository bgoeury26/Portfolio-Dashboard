import streamlit as st
from utils.market_data import get_available_history, get_company_profile
from utils.session_state import get_portfolio, initialize_session_state

initialize_session_state()

st.header("Ticker Research")

portfolio_df = get_portfolio()

symbol = st.text_input("Enter a ticker to research", value="MSFT").strip().upper()

if symbol:
    price_df, provider_used = get_available_history(symbol)

    if provider_used:
        st.success(f"Loaded market data for {symbol} using provider: {provider_used}")
        st.dataframe(price_df.tail(), use_container_width=True)
    else:
        st.warning("No market data found for this ticker.")

    profile_df = get_company_profile(symbol)

    if not profile_df.empty:
        st.subheader("Company Profile")
        st.dataframe(profile_df, use_container_width=True)

if portfolio_df is not None:
    st.subheader("Future portfolio impact module")
    st.info(
        "Next step: allow a selected ticker to be added hypothetically to the current portfolio and show the impact on allocation, concentration, and sector exposure."
    )
else:
    st.info("Upload a portfolio first if you want future portfolio impact analysis.")
