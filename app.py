import streamlit as st
from utils.session_state import initialize_session_state, get_portfolio

st.set_page_config(
    page_title="Portfolio Analysis by Goeury_Investments",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

initialize_session_state()
df = get_portfolio()

st.markdown("""
    <style>
        .hero-box {
            padding: 2.6rem 2.8rem 2.2rem 2.8rem;
            border-radius: 18px;
            background: linear-gradient(135deg, #10284B 0%, #16345C 100%);
            border: 1px solid rgba(232, 222, 210, 0.16);
            margin-bottom: 1.8rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.14);
        }

        .hero-content {
            max-width: 1400px;
        }

        .hero-title {
            font-size: 2.7rem;
            font-weight: 700;
            color: #F3ECE4;
            margin-bottom: 0.8rem;
            letter-spacing: 0.01em;
            line-height: 1.15;
        }

        .hero-subtitle {
            font-size: 1.12rem;
            color: #E8DED2;
            line-height: 1.85;
            margin-bottom: 0.9rem;
            max-width: 1280px;
        }

        .section-title {
            font-size: 1.2rem;
            font-weight: 700;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
            color: #F3ECE4;
        }

        .feature-card {
            padding: 1.25rem;
            border-radius: 16px;
            background: #1A3760;
            border: 1px solid rgba(232, 222, 210, 0.12);
            min-height: 180px;
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.08);
        }

        .feature-title {
            font-size: 1.05rem;
            font-weight: 700;
            margin-bottom: 0.45rem;
            color: #F3ECE4;
        }

        .feature-text {
            font-size: 0.95rem;
            color: #D9CDBF;
            line-height: 1.6;
        }

        .status-box {
            padding: 1rem 1.2rem;
            border-radius: 14px;
            background: #2A4065;
            border: 1px solid rgba(232, 222, 210, 0.16);
            margin-top: 0.5rem;
            margin-bottom: 1rem;
            color: #F3ECE4;
        }

        .info-box {
            padding: 1rem 1.2rem;
            border-radius: 14px;
            background: #2A4065;
            border: 1px solid rgba(232, 222, 210, 0.14);
            margin-top: 0.5rem;
            margin-bottom: 1rem;
            color: #F3ECE4;
        }

        .small-muted {
            color: #D9CDBF;
            font-size: 0.94rem;
        }

        div[data-testid="stMarkdownContainer"] p {
            color: inherit;
        }

        div[data-testid="stInfo"] {
            background-color: #234472;
            border: 1px solid rgba(232, 222, 210, 0.12);
        }

        div[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1D2230 0%, #232837 100%);
        }

        div[data-testid="stSidebar"] * {
            color: #E8DED2;
        }

        div[data-testid="stSidebarNav"] {
            padding-top: 1rem;
        }

        div[data-testid="stSidebarNav"]::before {
            content: "Goeury_Investments";
            display: block;
            font-size: 1.15rem;
            font-weight: 700;
            color: #F3ECE4;
            padding: 0.2rem 0.8rem 1rem 0.8rem;
            margin-bottom: 0.4rem;
            border-bottom: 1px solid rgba(232, 222, 210, 0.10);
        }

        div[data-testid="stSidebarNav"] ul {
            gap: 0.35rem;
        }

        div[data-testid="stSidebarNav"] li div {
            border-radius: 10px;
        }

        div[data-testid="stSidebarNav"] li a {
            border-radius: 10px;
            padding-top: 0.35rem;
            padding-bottom: 0.35rem;
            color: #E8DED2;
        }

        div[data-testid="stSidebarNav"] li a:hover {
            background-color: rgba(232, 222, 210, 0.08);
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero-box">
    <div class="hero-content">
        <div class="hero-title">Portfolio Analysis by Goeury_Investments</div>
        <div class="hero-subtitle">
            A professional portfolio dashboard designed to review holdings, monitor risk, test allocation ideas, and run scenario stress analysis from IBKR portfolio data.
        </div>
        <div class="small-muted">
            Built for structured portfolio monitoring and investment decision support.
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("## Platform Modules")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-title">Portfolio Overview</div>
        <div class="feature-text">
            Review allocation, total value, unrealized P/L, top holdings, and portfolio composition.
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-title">Risk Analytics</div>
        <div class="feature-text">
            Analyze concentration, diversification, sector and currency exposure, and P/L attribution.
        </div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-title">Optimization</div>
        <div class="feature-text">
            Compare current allocations with optimized portfolio weights using historical market data.
        </div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-title">Scenario Analysis</div>
        <div class="feature-text">
            Apply downside scenarios and compare current versus optimized portfolio resilience.
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("## Workflow")

w1, w2, w3, w4 = st.columns(4)

with w1:
    st.info("1. Upload your IBKR holdings file in Portfolio Overview.")

with w2:
    st.info("2. Review concentration and exposure in Risk Analytics.")

with w3:
    st.info("3. Run optimization to generate alternative allocations.")

with w4:
    st.info("4. Stress test both current and optimized portfolios in Scenario Analysis.")

st.markdown("## Current Session")

if df is not None and st.session_state.get("portfolio_loaded", False):
    st.markdown(f"""
    <div class="status-box">
        <strong>Portfolio loaded successfully.</strong><br>
        Active file: {st.session_state.get("portfolio_filename", "Unknown file")}<br>
        Positions currently available in memory: {len(df)}
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="info-box">
        <strong>No active portfolio loaded.</strong><br>
        Start in <strong>Portfolio Overview</strong> and upload your latest IBKR Flex Query holdings CSV.
    </div>
    """, unsafe_allow_html=True)

st.markdown("## Suggested Next Improvements")

st.markdown("""
- Apply the same navy / ivory box styling across the other pages for full visual consistency.
- Create an app-wide Streamlit theme file for sidebar, typography, and control consistency.
- Improve button, dataframe, and chart colors so all modules follow the same palette.
- Add a lightweight brand block at the top of the sidebar.
- Later, improve asset classification and ticker mapping for cleaner analytics and optimization outputs.
""")
