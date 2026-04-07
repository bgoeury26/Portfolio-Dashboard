import plotly.express as px
import streamlit as st

from utils.macro_data import get_macro_bundle
from utils.session_state import initialize_session_state

initialize_session_state()

st.header("Macro Dashboard")

macro_df = get_macro_bundle(start_date="2018-01-01")

if macro_df.empty:
    st.error("No FRED data available. Check that FRED_API_KEY is set correctly.")
    st.stop()

st.subheader("Latest Macro Snapshot")

latest = macro_df.dropna(how="all").iloc[-1]

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("10Y Yield", f"{latest['10Y Treasury Yield']:.2f}" if "10Y Treasury Yield" in macro_df.columns else "N/A")

with col2:
    st.metric("2Y Yield", f"{latest['2Y Treasury Yield']:.2f}" if "2Y Treasury Yield" in macro_df.columns else "N/A")

with col3:
    st.metric("Fed Funds", f"{latest['Fed Funds Rate']:.2f}" if "Fed Funds Rate" in macro_df.columns else "N/A")

with col4:
    st.metric("Unemployment", f"{latest['Unemployment Rate']:.2f}" if "Unemployment Rate" in macro_df.columns else "N/A")

with col5:
    st.metric("10Y-2Y Spread", f"{latest['10Y-2Y Spread']:.2f}" if "10Y-2Y Spread" in macro_df.columns else "N/A")

if "10Y Treasury Yield" in macro_df.columns:
    fig_10y = px.line(macro_df, x="date", y="10Y Treasury Yield", title="10Y Treasury Yield")
    st.plotly_chart(fig_10y, width="stretch")

if "Fed Funds Rate" in macro_df.columns:
    fig_ff = px.line(macro_df, x="date", y="Fed Funds Rate", title="Fed Funds Rate")
    st.plotly_chart(fig_ff, width="stretch")

if "CPI" in macro_df.columns:
    fig_cpi = px.line(macro_df, x="date", y="CPI", title="Consumer Price Index")
    st.plotly_chart(fig_cpi, width="stretch")

if "Unemployment Rate" in macro_df.columns:
    fig_un = px.line(macro_df, x="date", y="Unemployment Rate", title="Unemployment Rate")
    st.plotly_chart(fig_un, width="stretch")

if "10Y-2Y Spread" in macro_df.columns:
    fig_spread = px.line(macro_df, x="date", y="10Y-2Y Spread", title="10Y-2Y Yield Spread")
    st.plotly_chart(fig_spread, width="stretch")

st.subheader("Macro Data Table")
st.dataframe(macro_df.tail(20), width="stretch")
