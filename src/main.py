from pandas import DataFrame

from src.utils import (
    Config,
    SampleMode,
    get_config,
    load_data,
    compute_volatilities,
    trim_df,
    get_samples,
    get_backtester,
    compute_single_results,
    run_multi_samples,
    parse_order_book_history,
)
from src.graphs_utils import (
    cumulative_generated_fees,
    strategy_evolution,
    returns_vs_final_price_diff,
    kandel_evolution,
)

def handle_single(df: DataFrame, config: Config) -> None:
    backtester = get_backtester(
        df["price"],
        df["window_vol"],
        df["exit_vol"],
        config["backtester_config"],
        config["kandel_config"],
    )

    res, order_book_history = backtester.run()
    single_results = compute_single_results(
        df, res, config["kandel_config"]["initial_capital"]
    )

    cumulative_generated_fees(
        single_results["cum_generated_fees"], config["kandel_config"]["initial_capital"]
    )

    strategy_evolution(
        single_results,
        config["kandel_config"]["exit_vol_threshold"],
    )

    if config["backtester_config"]["position_history"]:
        order_book_parsed = parse_order_book_history(order_book_history, res.index)
        kandel_evolution(order_book_parsed, single_results["price"])


def handle_multi(df: DataFrame, config) -> None:
    print("init simulation");
    print(config);
    print(df.size);
    print(config["samples_length"])
    prices_samples, window_vol_samples, exit_vol_samples = get_samples(
        df,
        config["samples_length"],
    )

    print("start simulation");
    results = run_multi_samples(
        prices_samples,
        window_vol_samples,
        exit_vol_samples,
        config["backtester_config"],
        config["kandel_config"],
    )
    print("compute simulation");
    print(len(results));
    final_price_diff_arr, final_quote_returns_arr, final_base_returns_arr = zip(
        *results
    )

    print("start graph gen");
    returns_vs_final_price_diff(
        final_price_diff_arr,
        final_quote_returns_arr,
        final_base_returns_arr,
    )


def process(config):
    print("start process");
    df = load_data(config["data_path"])
    df = compute_volatilities(
        df,
        config["kandel_config"]["window"],
        config["exit_vol_window"],
    )

    df = trim_df(
        df,
        config["kandel_config"]["window"] + config["exit_vol_window"],
        config["start_date"],
        config["end_date"],
    )

    if config["sample_mode"] == SampleMode.SINGLE:
        print("simple mode");
        handle_single(df, config)
    elif config["sample_mode"] == SampleMode.MULTI:
        print("multi mode");
        handle_multi(df, config)
    print("end process");
