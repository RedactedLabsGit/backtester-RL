from src.utils import (
    get_config,
    load_data,
    compute_volatilities,
    trim_df,
    get_backtester,
    compute_results,
)
from src.graphs_utils import cumulative_generated_fees, strategy_evolution


def main():
    config = get_config("config.json")

    df = load_data(config["data_path"])
    df = compute_volatilities(
        df,
        config["kandel_config"]["window"],
        config["exit_vol_window"],
    )

    df = trim_df(
        df,
        config["kandel_config"]["window"] + config["exit_vol_window"],
    )

    backtester = get_backtester(
        df,
        config["backtester_config"],
        config["kandel_config"],
    )

    res, _ = backtester.run()
    res_1h = compute_results(df, res, config["kandel_config"]["initial_capital"])

    cumulative_generated_fees(
        res_1h["cum_generated_fees"], config["kandel_config"]["initial_capital"]
    )

    strategy_evolution(
        res_1h,
        config["kandel_config"]["exit_vol_threshold"],
    )


if __name__ == "__main__":
    main()
