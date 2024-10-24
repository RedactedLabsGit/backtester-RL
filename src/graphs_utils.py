import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def cumulative_generated_fees(
    cum_generated_fees: pd.Series, initial_capital: float
) -> None:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cum_generated_fees.index, y=cum_generated_fees))
    fig.update_layout(
        title=f"Cumulative generated fees - ${initial_capital:,} AUM",
        xaxis_title="Time",
        yaxis_title="Generated fees",
    )

    fig.write_html("results/generated_fees.html")


def strategy_evolution(res_1h: pd.DataFrame, exit_vol_threshold: float):
    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        specs=[
            [{"secondary_y": True}],
            [{}],
            [{"secondary_y": True}],
            [{"secondary_y": True}],
        ],
        vertical_spacing=0.05,
        subplot_titles=("MTM", "Returns", "Price", "Balance"),
    )
    fig.add_trace(
        go.Scatter(
            x=res_1h.index,
            y=res_1h.mtm_quote,
            mode="lines",
            name="MTM in USDC",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=res_1h.index,
            y=res_1h.mtm_base,
            mode="lines",
            name="MTM in ETH",
        ),
        row=1,
        col=1,
        secondary_y=True,
    )

    fig.add_trace(
        go.Scatter(
            x=res_1h.index,
            y=res_1h.returns_quote,
            mode="lines",
            name="Over holding USDC",
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=res_1h.index,
            y=res_1h.returns_base,
            mode="lines",
            name="Over holding ETH",
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=res_1h.index,
            y=res_1h.price,
            mode="lines",
            name="Price",
        ),
        row=3,
        col=1,
    )

    fig.add_trace(
        go.Scatter(x=res_1h.index, y=res_1h.window_vol, mode="lines", name="HV"),
        secondary_y=True,
        row=3,
        col=1,
    )

    fig.add_trace(
        go.Scatter(x=res_1h.index, y=res_1h.exit_vol, mode="lines", name="Exit vol"),
        secondary_y=True,
        row=3,
        col=1,
    )

    fig.add_hline(
        y=exit_vol_threshold,
        line_dash="dot",
        line_color="black",
        secondary_y=True,
        row=3,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=res_1h.index,
            y=res_1h.quote,
            name="Quote size",
            legendgroup="Quote",
            stackgroup="1",
        ),
        row=4,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=res_1h.index,
            y=-res_1h.base,
            name="Base size",
            legendgroup="Base",
            stackgroup="1",
        ),
        row=4,
        col=1,
        secondary_y=True,
    )

    fig.add_trace(
        go.Scatter(
            x=res_1h.index,
            y=-res_1h.quote,
            name="Quote size",
            legendgroup="Quote",
            marker=dict(color="rgba(0,0,0,0)"),
        ),
        row=4,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=res_1h.index,
            y=res_1h.base,
            name="Base size",
            legendgroup="Base",
            marker=dict(color="rgba(0,0,0,0)"),
        ),
        row=4,
        col=1,
        secondary_y=True,
    )

    fig.update_layout(
        height=1200,
        width=1600,
        title_text="Backtesting results",
    )

    fig.update_yaxes(row=2, col=1, tickformat=".2%")

    fig.write_html("results/strategy_evolution.html")


def returns_vs_final_price_diff(
    final_price_diff_arr, quote_returns_arr, base_returns_arr
):
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        specs=[[{}], [{}]],
        vertical_spacing=0.05,
        subplot_titles=("Over holding quote", "Hover holding base"),
    )

    quote_negative_returns = [
        [price, ret]
        for price, ret in zip(final_price_diff_arr, quote_returns_arr)
        if ret < 0
    ]
    quote_positive_returns = [
        [price, ret]
        for price, ret in zip(final_price_diff_arr, quote_returns_arr)
        if ret >= 0
    ]

    base_negative_returns = [
        [price, ret]
        for price, ret in zip(final_price_diff_arr, base_returns_arr)
        if ret < 0
    ]
    base_positive_returns = [
        [price, ret]
        for price, ret in zip(final_price_diff_arr, base_returns_arr)
        if ret >= 0
    ]

    fig.add_trace(
        go.Scatter(
            x=[row[0] for row in quote_negative_returns],
            y=[row[1] for row in quote_negative_returns],
            name="Returns",
            mode="markers",
            marker=dict(color="red"),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=[row[0] for row in quote_positive_returns],
            y=[row[1] for row in quote_positive_returns],
            name="Returns",
            mode="markers",
            marker=dict(color="green"),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=[row[0] for row in base_negative_returns],
            y=[row[1] for row in base_negative_returns],
            name="Returns",
            mode="markers",
            marker=dict(color="red"),
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=[row[0] for row in base_positive_returns],
            y=[row[1] for row in base_positive_returns],
            name="Returns",
            mode="markers",
            marker=dict(color="green"),
        ),
        row=2,
        col=1,
    )

    fig.update_xaxes(title_text="Price difference on period", row=2, col=1)
    fig.update_yaxes(title_text="Returns", row=1, col=1)
    fig.update_yaxes(title_text="Returns", row=2, col=1)

    fig.update_layout(
        title="Returns vs Final Price Difference",
        showlegend=False,
        height=800,
        width=1200,
    )

    fig.write_html("results/returns_vs_final_price_diff.html")
