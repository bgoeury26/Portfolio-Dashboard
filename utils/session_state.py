import streamlit as st


def initialize_session_state():
    defaults = {
        "portfolio_df": None,
        "portfolio_filename": None,
        "portfolio_loaded": False,
        "optimized_weights_df": None,
        "optimization_metadata": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def save_portfolio(df, filename):
    st.session_state["portfolio_df"] = df
    st.session_state["portfolio_filename"] = filename
    st.session_state["portfolio_loaded"] = True


def clear_portfolio():
    st.session_state["portfolio_df"] = None
    st.session_state["portfolio_filename"] = None
    st.session_state["portfolio_loaded"] = False
    st.session_state["optimized_weights_df"] = None
    st.session_state["optimization_metadata"] = None


def get_portfolio():
    return st.session_state.get("portfolio_df")


def save_optimized_weights(df, metadata=None):
    st.session_state["optimized_weights_df"] = df
    st.session_state["optimization_metadata"] = metadata


def get_optimized_weights():
    return st.session_state.get("optimized_weights_df")


def get_optimization_metadata():
    return st.session_state.get("optimization_metadata")
