import json
import numpy as np
import pandas as pd
from enum import Enum
from typing import TypedDict
from multiprocessing import Pool
from datetime import datetime, timezone

from src.kandel import KandelConfig
from src.kandel_backtester import KandelBacktesterConfig, KandelBacktester


class SampleMode(Enum):
    SINGLE = "single"
    MULTI = "multi"


class Config(TypedDict):
    sample_mode: SampleMode
    data_path: str
    start_date: datetime
    end_date: datetime
    samples_length: int
    exit_vol_window: int
    backtester_config: KandelBacktesterConfig
    kandel_config: KandelConfig


def get_config(raw_config: dict) -> Config:
    config = Config(
        sample_mode=SampleMode(raw_config["sample_mode"]),
        data_path=raw_config["data_path"],
        start_date=datetime.strptime(raw_config["start_date"], "%Y-%m-%d").astimezone(
            tz=timezone.utc
        ),
        end_date=datetime.strptime(raw_config["end_date"], "%Y-%m-%d").astimezone(
            tz=timezone.utc
        ),
        samples_length=raw_config["samples_length"] * 24 * 3600,
        exit_vol_window=raw_config["exit_vol_window"] * 3600,
        backtester_config=KandelBacktesterConfig(raw_config["backtester_config"]),
        kandel_config=KandelConfig(
            window=raw_config["kandel_config"]["window"] * 3600,
            initial_capital=raw_config["kandel_config"]["initial_capital"],
            vol_mult=raw_config["kandel_config"]["vol_mult"],
            n_points=raw_config["kandel_config"]["n_points"],
            step_size=raw_config["kandel_config"]["step_size"],
            exit_vol_threshold=raw_config["kandel_config"]["exit_vol_threshold"],
            asymmetric_exit_threshold=raw_config["kandel_config"][
                "asymmetric_exit_threshold"
            ],
        ),
    )

    return config


def load_data(data_path: str) -> pd.DataFrame:
    df = pd.read_csv(data_path, header=0, index_col=0)
    df.index = pd.to_datetime(df.index, unit="s", utc=True)

    return df


def compute_volatilities(
    df: pd.DataFrame, window: int, exit_vol_window: int
) -> pd.DataFrame:
    df["log_return"] = np.log(df["price"] / df["price"].shift(1))

    df["exit_vol"] = df["log_return"].rolling(exit_vol_window).std() * np.sqrt(
        exit_vol_window
    )
    df["exit_vol"] = df["exit_vol"].fillna(0)

    df["window_vol"] = df["log_return"].rolling(window).std() * np.sqrt(window)
    df["window_vol"] = df["window_vol"].fillna(0)

    df = df.drop(columns=["log_return"])

    return df


def trim_df(
    df: pd.DataFrame, windows_length: int, start_date: datetime, end_date: datetime
) -> pd.DataFrame:
    df = df.iloc[windows_length:]

    df = df.loc[start_date:end_date]

    return df


def get_samples(
    df: pd.DataFrame, samples_length: int
) -> tuple[list[pd.Series], list[pd.Series], list[pd.Series]]:
    prices_samples = []
    window_vol_samples = []
    exit_vol_samples = []

    for i in range(samples_length // 3600 // 24):
        prices_samples += [
            df["price"][j : j + samples_length]
            for j in range(i * 3600 * 24, len(df["price"]), samples_length)
        ][:-1]
        window_vol_samples += [
            df["window_vol"][j : j + samples_length]
            for j in range(i * 3600 * 24, len(df["window_vol"]), samples_length)
        ][:-1]
        exit_vol_samples += [
            df["exit_vol"][j : j + samples_length]
            for j in range(i * 3600 * 24, len(df["exit_vol"]), samples_length)
        ][:-1]

    return prices_samples, window_vol_samples, exit_vol_samples


def get_backtester(
    prices: pd.Series,
    window_vol: pd.Series,
    exit_vol: pd.Series,
    backtester_config: KandelBacktesterConfig,
    kandel_config: KandelConfig,
) -> KandelBacktester:
    return KandelBacktester(
        prices, backtester_config, kandel_config, window_vol, exit_vol
    )


def run_sample(
    prices: pd.Series,
    window_vol: pd.Series,
    exit_vol: pd.Series,
    backtester_config: KandelBacktesterConfig,
    kandel_config: KandelConfig,
) -> tuple[float, float, float]:
    backtester = get_backtester(
        prices, window_vol, exit_vol, backtester_config, kandel_config
    )
    res, _ = backtester.run(loading=False)
    price_diff, quote_returns, base_returns = compute_sample_results(prices, res)

    return price_diff, quote_returns, base_returns


def run_multi_samples(
    prices_samples: list[pd.Series],
    window_vol_samples: list[pd.Series],
    exit_vol_samples: list[pd.Series],
    backtester_config: KandelBacktesterConfig,
    kandel_config: KandelConfig,
) -> list[pd.DataFrame]:
    with Pool() as pool:
        results = pool.starmap(
            run_sample,
            zip(
                prices_samples,
                window_vol_samples,
                exit_vol_samples,
                [backtester_config] * len(prices_samples),
                [kandel_config] * len(prices_samples),
            ),
        )

    return results


def compute_sample_results(
    prices: pd.Series,
    res: pd.DataFrame,
) -> tuple[float, float, float]:
    res.index = prices.index
    res["price"] = prices
    res["mtm_quote"] = res["quote"] + res["base"] * res["price"]
    res["mtm_base"] = res["base"] + res["quote"] / res["price"]

    price_diff = res["price"].iloc[-1] - res["price"].iloc[0]
    quote_returns = res["mtm_quote"].iloc[-1] / res["mtm_quote"].iloc[0] - 1
    base_returns = res["mtm_base"].iloc[-1] / res["mtm_base"].iloc[0] - 1

    return price_diff, quote_returns, base_returns


def compute_single_results(
    df: pd.DataFrame,
    res: pd.DataFrame,
    initial_capital: float,
) -> pd.DataFrame:
    res.index = df.index
    res["price"] = df["price"]
    res["window_vol"] = df["window_vol"]
    res["exit_vol"] = df["exit_vol"]
    res["mtm_quote"] = res["quote"] + res["base"] * res["price"]
    res["mtm_base"] = res["base"] + res["quote"] / res["price"]
    res["returns_quote"] = res["mtm_quote"] / initial_capital - 1
    res["returns_base"] = res["mtm_base"] / (initial_capital / df["price"].iloc[0]) - 1
    res["returns_even"] = (
        res["mtm_quote"]
        / (
            initial_capital / 2
            + (initial_capital / 2 / df["price"].iloc[0] * res["price"])
        )
        - 1
    )
    res["cum_generated_fees"] = res["generated_fees"].cumsum()

    res_1h = res.resample("1H").last()

    return res_1h


def parse_order_book_history(
    order_book_history: list[dict], indexes: pd.Index
) -> pd.DataFrame:
    df = pd.DataFrame(order_book_history)
    df.index = indexes
    df_1h = df.resample("1H").last()

    return df_1h
