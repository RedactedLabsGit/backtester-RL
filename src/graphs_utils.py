import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def format_big_number(x):
    for unit in ["", "K", "M"]:
        if abs(x) < 1000.0:
            return f"{x:6.2f}{unit}"
        x /= 1000.0
    return f"{x:6.2f}B"


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
        subplot_titles=("MTM", "Returns", "Price & Vol", "Balance"),
    )

    fig.add_trace(
        go.Scatter(
            x=res_1h.index,
            y=res_1h.mtm_quote,
            mode="lines",
            name="MTM in quote",
            marker=dict(color="blue"),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=res_1h.index,
            y=res_1h.mtm_base,
            mode="lines",
            name="MTM in base",
            marker=dict(color="orange"),
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
            name="Over holding quote",
            marker=dict(color="royalblue"),
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=res_1h.index,
            y=res_1h.returns_base,
            mode="lines",
            name="Over holding base",
            marker=dict(color="darkorange"),
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=res_1h.index,
            y=res_1h.returns_even,
            mode="lines",
            name="Over holding 50/50",
            marker=dict(color="seagreen"),
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scattergl(
            x=res_1h.index,
            y=res_1h.window_vol,
            mode="lines",
            name="Rebalance window vol",
            marker=dict(color="firebrick"),
            opacity=0.5,
        ),
        secondary_y=True,
        row=3,
        col=1,
    )
    fig.add_trace(
        go.Scattergl(
            x=res_1h.index,
            y=res_1h.exit_vol,
            mode="lines",
            name="Exit strat vol",
            marker=dict(color="red"),
            opacity=0.5,
        ),
        secondary_y=True,
        row=3,
        col=1,
    )
    fig.add_trace(
        go.Scattergl(
            x=res_1h.index,
            y=res_1h.price,
            mode="lines",
            name="Price",
            marker=dict(color="gold"),
        ),
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
            marker=dict(color="dodgerblue"),
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
            marker=dict(color="coral"),
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
            marker=dict(color="rgba(0,0,0,0)"),
            showlegend=False,
            hoverinfo="none",
        ),
        row=4,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=res_1h.index,
            y=res_1h.base,
            name="Base size",
            marker=dict(color="rgba(0,0,0,0)"),
            showlegend=False,
            hoverinfo="none",
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
    fig.update_yaxes(row=1, col=1, title_text="MTM in quote", secondary_y=False)
    fig.update_yaxes(row=1, col=1, title_text="MTM in base", secondary_y=True)

    fig.update_yaxes(row=2, col=1, tickformat=".2%", title_text="Returns")

    fig.update_yaxes(row=3, col=1, title_text="Price", secondary_y=False)
    fig.update_yaxes(row=3, col=1, title_text="Vol", secondary_y=True)

    fig.update_yaxes(
        row=4,
        col=1,
        title_text="Quote balance",
        secondary_y=False,
        tickvals=["", "", 0, max(res_1h.quote) / 2, max(res_1h.quote)],
        ticktext=[
            "",
            "",
            0,
            format_big_number(max(res_1h.quote) / 2),
            format_big_number(max(res_1h.quote)),
        ],
    )
    fig.update_yaxes(
        row=4,
        col=1,
        title_text="Base balance",
        secondary_y=True,
        tickvals=[-max(res_1h.base), -max(res_1h.base) / 2, 0, "", ""],
        ticktext=[
            format_big_number(max(res_1h.base)),
            format_big_number(max(res_1h.base) / 2),
            0,
            "",
            "",
        ],
    )

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


def kandel_evolution(
    df_order_book: pd.DataFrame,
    prices: pd.Series,
):
    fig = make_subplots(
        rows=1,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=(""),
        specs=[[{"secondary_y": True}]],
    )

    for i, ob in enumerate(df_order_book.iterrows()):
        bids = ob[1].item()["bids"]
        asks = ob[1].item()["asks"]

        fig.add_trace(
            go.Scatter(
                x=[i for _ in range(len(bids))],
                y=tuple(bids),
                mode="markers",
                name="Bids",
                showlegend=False,
                marker=dict(
                    color="green",
                    symbol="line-ew-open",
                    size=8,
                    line=dict(width=5, color="black"),
                ),
            ),
        )

        fig.add_trace(
            go.Scatter(
                x=[i for _ in range(len(asks))],
                y=tuple(asks),
                mode="markers",
                name="Asks",
                showlegend=False,
                marker=dict(
                    color="red",
                    symbol="line-ew-open",
                    size=8,
                    line=dict(width=5, color="black"),
                ),
            ),
        )

    fig.add_trace(
        go.Scatter(
            x=[i for i in range(len(df_order_book))],
            y=prices,
            mode="lines",
            name="Price",
            marker=dict(color="blue"),
            hovertext=[
                f"Price: {prices.iloc[i]:.2f}<br>Time: {prices.index[i].strftime('%b %d %H:%M')}"
                for i in range(len(prices))
            ],
        )
    )

    fig.update_layout(
        height=1000,
        width=1600,
        title_text="Position history",
    )

    fig.update_xaxes(
        tickvals=np.arange(0, len(prices), len(prices) // 6),
        ticktext=[
            prices.index[i].strftime("%b %d, %Hh")
            for i in np.arange(0, len(prices), len(prices) // 6)
        ],
    )

    fig.write_html("results/kandel_evolution.html")
