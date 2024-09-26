import numpy as np
import linecache
import pandas as pd
from src.time_series import TS
from typing import Tuple, List, Union

"""
Files need to have the following format:
first column needs to be a string representing time up to ms
separator = ";"
dates will always be handled as timestamps
"""

NA_VAL = -9999999


def log_ret_(ts: TS) -> TS:
    """
    returns a copy of ts with the log-returns as values
    """
    res = ts.copy()
    # TO DO : Parallelize this
    for i, col in enumerate(res.values):
        res.values[i] = np.insert(np.log(col[1:] / col[:-1]), 0, None)

    return res


def mean_(ts: TS) -> List:
    """
    returns annualized volatility of time series
    TO DO: how to handle if multiple time series
    """
    res = []
    # TO DO: Parallelize
    for i, col in enumerate(ts.values):
        res.append(np.nanmean(col))
    return res if len(res) > 1 else res[0]


def vol_(ts: Union[TS, pd.DataFrame], multiplier: float = None) -> list | float:
    """
    returns annualized volatility of time series
    TO DO: how to handle if multiple time series
    """
    if isinstance(ts, TS):
        res = []
        # TO DO: Parallelize
        for i, col in enumerate(ts.values):
            res.append(np.nanstd(col) * np.sqrt(ts.units_in_year()))
        return res if len(res) > 1 else res[0]
    elif isinstance(ts, pd.DataFrame):
        if not multiplier:
            raise ("I need a multiplier to annualize the vol")
        else:
            return
    else:
        raise ("Don't know that type of input")


def std_(ts: TS) -> List:
    """
    returns annualized volatility of time series
    TO DO: how to handle if multiple time series
    """
    res = []
    # TO DO: Parallelize
    for i, col in enumerate(ts.values):
        res.append(np.nanstd(col))
    return res if len(res) > 1 else res[0]


def one_(ts: TS) -> TS:
    res = ts.copy()
    # TO DO : Parallelize this
    for i, col in enumerate(res.values):
        res.values[i] = res.values[i] / res.values[i][0]

    return res


def cumsum_(ts: TS) -> TS:
    res = ts.copy()
    # TO DO : Parallelize this
    for i, col in enumerate(res.values):
        res.values[i] = np.cumsum(res.values[i])

    return res


def bollinger_bands_(ts: TS, num_std: int) -> List:

    res = []
    means = mean_(ts)
    vols = std_((ts))
    if ts.n_cols == 1:
        return [means, means - num_std * vols, means + num_std * vols]
    for mean, vol in zip(means, vols):
        res.append([mean, mean - num_std * vol, mean + num_std * vol])
    return res
