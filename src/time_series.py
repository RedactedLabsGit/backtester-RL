import numpy as np
import linecache
import pandas as pd
from typing import Tuple, Union
import datetime

"""
Files need to have the following format:
first column needs to be a string representing time up to ms
separator = ";"
dates will always be handled as timestamps
"""


class TS:
    """
    Time Series Model
    """

    row_names: pd.DatetimeIndex
    unit: Tuple[int, str]
    n_rows: int
    col_names: np.array
    n_cols: int
    values: np.array

    def __init__(
        self,
        row_names: pd.DatetimeIndex,
        unit: Tuple[int, str],
        n_rows: int,
        col_names: np.array,
        values: np.array,
    ) -> None:
        self.row_names = row_names
        self.unit = unit
        self.n_rows = n_rows
        self.col_names = col_names
        self.n_cols = len(self.col_names)
        self.values = values

    def copy(self):
        """
        Generate a copy of the Time Series Model instance.
        """
        return TS(
            row_names=self.row_names.copy(),
            unit=self.unit,
            n_rows=self.n_rows,
            col_names=self.col_names.copy(),
            values=self.values.copy(),
        )

    def to_pandas(self):
        return pd.DataFrame(
            self.values.transpose(), index=self.row_names, columns=self.col_names
        )

    def __repr__(self) -> str:
        return str(self)

    def __str__(self):
        return f"n_rows: {self.n_rows} : n_cols = {self.n_cols} : unit : {self.unit} \n {self.to_pandas()}"

    def units_in_year(self) -> int:
        """
        depending on the unit, returns the number of units in a year (for annualized vol calc)
        """
        d = {
            "y": 1,
            "b": 12,
            "w": 52,
            "d": 365,
            "h": 24 * 365,
            "m": 60 * 24 * 365,
            "s": 60 * 60 * 24 * 365,
            "ms": 60 * 60 * 60 * 24 * 365,
        }
        return int(d[self.unit[1]] / self.unit[0])

    def __getitem__(self, index: Union[int, slice, str]):
        if isinstance(index, int):
            if index == 0:
                return TS(
                    row_names=self.row_names[:1],
                    unit=self.unit,
                    n_rows=1,
                    col_names=self.col_names,
                    values=self.values[:, :1],
                )
            elif index > self.n_rows:
                index = self.n_rows

            return self.values[:, index]
        elif isinstance(index, slice):
            start, stop, step = index.indices(self.n_rows)
            temp_values = self.values[:, start:stop:step]
            return TS(
                row_names=self.row_names[start:stop:step],
                unit=self.unit,
                n_rows=stop - start,
                col_names=self.col_names,
                values=temp_values,
            )

        elif isinstance(index, str):
            assert index in self.col_names, f"Column {index} not found"
            idx = np.where(self.col_names == index)
            return TS(
                row_names=self.row_names,
                unit=self.unit,
                n_rows=self.n_rows,
                col_names=[index],
                values=self.values[idx],
            )

        else:
            raise TypeError("Index must be an integer or a slice or a str")

    def add_column(self, col_name: str, new_values: np.array):
        assert len(new_values) == self.n_rows
        res = self.copy()
        res.n_cols += 1
        res.col_names = np.concatenate((res.col_names, [col_name]))
        res.values = np.concatenate((res.values, [new_values]), axis=0)
        return res


def get_timedelta_unit(timedelta: pd.Timedelta) -> str:
    if timedelta.components.days != 0:
        return (timedelta.components.days, "d")
    elif timedelta.components.hours != 0:
        return (timedelta.components.hours, "h")
    elif timedelta.components.minutes != 0:
        return (timedelta.components.minutes, "m")
    elif timedelta.components.seconds != 0:
        return (timedelta.components.seconds, "s")
    else:
        return (
            timedelta.components.milliseconds,
            "ms",
        )  # Default unit if all others are 0


def load_csv(path: str, ffill: bool = True) -> TS:
    """
    Loads csv into a TS object.
    TO DO: not use pandas, check if there is a faster way
    """
    temp = pd.read_csv(path, index_col=0, sep=",")
    temp.index = pd.to_datetime(temp.index, unit="s")  # TO DO: what if other unit?
    # check if index has "holes"
    unit = get_timedelta_unit(temp.index.diff().dropna().min())
    if not temp.index.diff().dropna().nunique() == 1:
        if ffill:
            most_common_diff = temp.index.diff().value_counts().idxmax()
            new_index = pd.date_range(
                start=temp.index.min(), end=temp.index.max(), freq=most_common_diff
            )
            temp = temp.reindex(new_index)
            temp.ffill(inplace=True)

        else:
            raise Exception("Time series index is not uniform, please check data")
    else:
        pass
        # Find the Timedelta with most occurences which should be the timedelta of the index
        # time_delta = temp.index.diff().dropna().value_counts().idxmax()
        # unit = get_timedelta_unit(time_delta)

        # re-create index
    return TS(
        row_names=temp.index,
        unit=unit,
        n_rows=len(temp.index),
        col_names=np.array(temp.columns),
        values=np.array(temp.values).reshape(len(temp.columns), len(temp.index)),
    )


def col_concat(t: TS, s: TS) -> TS:
    if t.n_rows != s.n_rows:
        raise ("Cannot concat, not same dimensions")
    elif t.unit != s.unit:
        raise ("Cannot concat, not same unit")
    elif not (t.row_names == s.row_names).all():
        # TO DO: handle this case
        raise ("Cannot concat, different index")
    else:
        return TS(
            row_names=t.row_names,
            unit=t.unit,
            n_rows=t.n_rows,
            col_names=np.concatenate([t.col_names, s.col_names]),
            values=np.concatenate([t.values, s.values]),
        )
