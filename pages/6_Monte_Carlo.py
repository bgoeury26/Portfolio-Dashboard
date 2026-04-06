import pandas as pd
import plotly.express as px
import streamlit as st

from utils.market_data import (
    compute_returns_from_prices,
    get_multi_asset_close_prices,
    prepare_portfolio_weights_from_holdings,
    run_monte_carlo_portfolio_simulation,
)
from utils.session_state import (
    get_optimized_weights,
    get_portfolio,
    initialize_session_state,
)

initialize_session_state()

st.header("Monte Carlo Simulation")

portfolio_df = get_portfolio()
optimized_weights_df = get_optimized_weights()

if portfolio_df is None:
    st.warning("Please upload a portfolio first in Portfolio Overview.")
    st.stop()

simulation_horizon = st.slider("Simulation horizon (trading days)", 21, 504, 252, 21)
n_sims = st.slider("Number of simulations", 500, 10000, 3000, 500)
initial_value = st.number_input("Initial portfolio value", min_value=1000, value=100000, step=5000)

portfolio_symbols = portfolio_df["Symbol"].dropna().astype(str).unique().tolist()

prices_df, valid_symbols, failed_symbols = get_multi_asset_close_prices(
    portfolio_symbols,
    start_date="2024-01-01",
)

if failed_symbols:
    st.warning("Excluded symbols from simulation: " + ", ".join(failed_symbols))

if prices_df.empty or len(valid_symbols) < 2:
    st.error("Not enough valid market data to run Monte Carlo simulation.")
    st.stop()

asset_returns = compute_returns_from_prices(prices_df)
current_weights = prepare_portfolio_weights_from_holdings(portfolio_df, valid_symbols)

current_paths, current_stats = run_monte_carlo_portfolio_simulation(
    asset_returns=asset_returns,
    weights_series=current_weights,
    initial_value=initial_value,
    n_days=simulation_horizon,
    n_sims=n_sims,
    seed=42,
)

if current_paths.empty:
    st.error("Current portfolio simulation failed.")
    st.stop()

summary_rows = [
    {
        "Portfolio": "Current",
        "Median Ending Value": current_stats["median_ending_value"],
        "Mean Ending Value": current_stats["mean_ending_value"],
        "5th Percentile": current_stats["p5_ending_value"],
        "95th Percentile": current_stats["p95_ending_value"],
        "Probability of Loss": current_stats["probability_of_loss"],
        "Median Return": current_stats["median_total_return"],
        "Mean Return": current_stats["mean_total_return"],
    }
]

optimized_paths = None
optimized_stats = None

if optimized_weights_df is not None:
    optimized_weights = (
        optimized_weights_df[optimized_weights_df["Symbol"].isin(valid_symbols)]
        .set_index("Symbol")["OptimizedWeight"]
    )

    if not optimized_weights.empty and optimized_weights.sum() > 0:
        optimized_weights = optimized_weights / optimized_weights.sum()

        optimized_paths, optimized_stats = run_monte_carlo_portfolio_simulation(
            asset_returns=asset_returns,
            weights_series=optimized_weights,
            initial_value=initial_value,
            n_days=simulation_horizon,
            n_sims=n_sims,
            seed=42,
        )

        if not optimized_paths.empty:
            summary_rows.append(
                {
                    "Portfolio": "Optimized",
                    "Median Ending Value": optimized_stats["median_ending_value"],
                    "Mean Ending Value": optimized_stats["mean_ending_value"],
                    "5th Percentile": optimized_stats["p5_ending_value"],
                    "95th Percentile": optimized_stats["p95_ending_value"],
                    "Probability of Loss": optimized_stats["probability_of_loss"],
                    "Median Return": optimized_stats["median_total_return"],
                    "Mean Return": optimized_stats["mean_total_return"],
                }
            )

summary_df = pd.DataFrame(summary_rows)

st.subheader("Simulation Summary")

st.dataframe(
    summary_df.style.format({
        "Median Ending Value": "{:,.2f}",
        "Mean Ending Value": "{:,.2f}",
        "5th Percentile": "{:,.2f}",
        "95th Percentile": "{:,.2f}",
        "Probability of Loss": "{:.2%}",
        "Median Return": "{:.2%}",
        "Mean Return": "{:.2%}",
    }),
    use_container_width=True,
)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Current Median Ending Value", f"{current_stats['median_ending_value']:,.0f}")

with col2:
    st.metric("Current 5th Percentile", f"{current_stats['p5_ending_value']:,.0f}")

with col3:
    st.metric("Current Probability of Loss", f"{current_stats['probability_of_loss']:.2%}")

if optimized_stats is not None:
    col4, col5, col6 = st.columns(3)

    with col4:
        st.metric("Optimized Median Ending Value", f"{optimized_stats['median_ending_value']:,.0f}")

    with col5:
        st.metric("Optimized 5th Percentile", f"{optimized_stats['p5_ending_value']:,.0f}")

    with col6:
        st.metric("Optimized Probability of Loss", f"{optimized_stats['probability_of_loss']:.2%}")
else:
    st.info("Run Optimization first to compare Monte Carlo outcomes versus the optimized portfolio.")

st.subheader("Sample Simulated Paths")

current_sample = current_paths.iloc[:, :100].copy()
current_sample["Day"] = range(1, len(current_sample) + 1)
current_long = current_sample.melt(id_vars="Day", var_name="Simulation", value_name="Portfolio Value")
current_long["Portfolio"] = "Current"

plot_df = current_long

if optimized_paths is not None and not optimized_paths.empty:
    optimized_sample = optimized_paths.iloc[:, :100].copy()
    optimized_sample["Day"] = range(1, len(optimized_sample) + 1)
    optimized_long = optimized_sample.melt(id_vars="Day", var_name="Simulation", value_name="Portfolio Value")
    optimized_long["Portfolio"] = "Optimized"
    plot_df = pd.concat([current_long, optimized_long], ignore_index=True)

fig_paths = px.line(
    plot_df,
    x="Day",
    y="Portfolio Value",
    color="Portfolio",
    line_group="Simulation",
    title="Monte Carlo Simulated Portfolio Paths",
)

fig_paths.update_traces(opacity=0.10)
st.plotly_chart(fig_paths, use_container_width=True)

st.subheader("Ending Value Distribution")

distribution_df = pd.DataFrame({
    "Ending Value": current_paths.iloc[-1, :].values,
    "Portfolio": "Current",
})

if optimized_paths is not None and not optimized_paths.empty:
    optimized_dist = pd.DataFrame({
        "Ending Value": optimized_paths.iloc[-1, :].values,
        "Portfolio": "Optimized",
    })
    distribution_df = pd.concat([distribution_df, optimized_dist], ignore_index=True)

fig_hist = px.histogram(
    distribution_df,
    x="Ending Value",
    color="Portfolio",
    nbins=50,
    barmode="overlay",
    title="Distribution of Simulated Ending Portfolio Values",
    opacity=0.60,
)
st.plotly_chart(fig_hist, use_container_width=True)

st.subheader("Interpretation")

if current_stats["probability_of_loss"] >= 0.40:
    st.warning("The current portfolio shows a relatively high probability of finishing below the starting value in this simulation setup.")
else:
    st.success("The current portfolio shows a relatively moderate probability of loss in this simulation setup.")

if optimized_stats is not None:
    if optimized_stats["probability_of_loss"] < current_stats["probability_of_loss"]:
        st.success("The optimized portfolio appears more resilient than the current portfolio in the Monte Carlo simulation.")
    elif optimized_stats["probability_of_loss"] > current_stats["probability_of_loss"]:
        st.warning("The optimized portfolio appears less resilient than the current portfolio in the Monte Carlo simulation.")
    else:
        st.info("The current and optimized portfolios show similar loss probabilities in the Monte Carlo simulation.")
