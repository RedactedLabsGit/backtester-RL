import json
import numpy as np
import pandas as pd
from typing import TypedDict
from enum import Enum

from src.kandel import KandelConfig
from src.kandel_backtester import KandelBacktesterConfig, KandelBacktester


class SampleMode(Enum):
    SINGLE = "single"
    MULTI = "multi"


class Config(TypedDict):
    sample_mode: SampleMode
    data_path: str
    start_date: str
    end_date: str
    samples_length: int
    exit_vol_window: int
    backtester_config: KandelBacktesterConfig
    kandel_config: KandelConfig


def get_config(config_path: str) -> Config:
    with open(config_path) as f:
        raw_config = json.load(f)

    config = Config(
        sample_mode=SampleMode(raw_config["sample_mode"]),
        data_path=raw_config["data_path"],
        start_date=raw_config["start_date"],
        end_date=raw_config["end_date"],
        samples_length=raw_config["samples_length"],
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


# TODO: handle start/end date.
def trim_df(df: pd.DataFrame, windows_length: int) -> pd.DataFrame:
    df = df.iloc[windows_length:]

    return df


def get_backtester(
    df: pd.DataFrame,
    backtester_config: KandelBacktesterConfig,
    kandel_config: KandelConfig,
) -> KandelBacktester:
    prices = df["price"]
    window_vol = df["window_vol"]
    exit_vol = df["exit_vol"]

    return KandelBacktester(
        prices, backtester_config, kandel_config, window_vol, exit_vol
    )


def compute_results(
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
    res["cum_generated_fees"] = res["generated_fees"].cumsum()

    res_1h = res.resample("1H").last()

    return res_1h
