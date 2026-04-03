import streamlit as st
from utils.session_state import get_portfolio, initialize_session_state

initialize_session_state()

st.header("Scenario Analysis")

df = get_portfolio()

if df is None:
    st.warning("Please upload a portfolio first in Portfolio Overview.")
    st.stop()

st.success(f"Using active portfolio: {st.session_state['portfolio_filename']}")
st.write("Portfolio data is loaded and available for scenario analysis.")
st.dataframe(df[["Symbol", "Description", "PositionValue", "FifoPnlUnrealized"]], use_container_width=True)
