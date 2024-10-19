from pandas import Series, DataFrame
from typing import TypedDict, Generator
from tqdm import tqdm
import numpy as np

from src.kandel_v2 import KandelConfig, Kandel
from src.order_book import OrderBook
from src.order import Order


class KandelState(TypedDict):
    """
    KandelState represents the state of a Kandel strategy.

    Attributes:
        base (float):
            The base size.
        quote (float):
            The quote size.
        order_book (OrderBook):
            The order book.
        transactions (list[Order]):
            The transactions.
    """

    base: float
    quote: float
    order_book: OrderBook
    transactions: list[Order]


class KandelBacktester:
    """
    KandelBacktester is a backtester for a the Kandel strategy.

    Attributes:
        prices (Series):
            The price time series.
        kandel (Kandel):
            The Kandel strategy.
        window_vol (Series):
            The volatility time series for the window.
        exit_vol (Series):
            The volatility time series for the exit strategy.


    Methods:
        _generate_kandel_states(loading_bar: tqdm):
            Generator of Kandel states.
        run() -> tuple[DataFrame, list[OrderBook], list[list[Order]]]:
            Run the backtest.
    """

    def __init__(
        self,
        prices: Series,
        config: KandelConfig,
        window_vol: Series,
        exit_vol: Series,
    ) -> None:
        """
        Initialize the Kandel backtester.

        Args:
            prices (Series):
                The price time series.
            config (KandelConfig):
                The configuration for the Kandel strategy.
            window_vol (Series):
                The volatility time series for the window.
            exit_vol (Series):
                The volatility time series for the exit strategy.
        """

        self.prices = prices
        self.kandel = Kandel(config, prices.iloc[0], window_vol.iloc[0])
        self.window_vol = window_vol
        self.exit_vol = exit_vol

    def _generate_kandel_states(
        self, loading_bar: tqdm
    ) -> Generator[KandelState, None, None]:
        """
        Generate the Kandel states.

        Yields:
            KandelState: The next state of the Kandel strategy.
        """

        for i, price in enumerate(self.prices):
            loading_bar.update(1)

            self.kandel.update_spot_and_vol(price, self.window_vol.iloc[i])
            transactions = self.kandel.arbitrate_order_book()
            if i % self.kandel.config["window"] == 0:
                self.kandel.rebalance()

            yield KandelState(
                base=self.kandel.base,
                quote=self.kandel.quote,
                order_book=self.kandel.order_book,
                transactions=transactions,
            )

    def run(self) -> tuple[DataFrame, list[OrderBook], list[list[Order]]]:
        """
        Run the backtest for the Kandel strategy.

        Returns:
            tuple:
                DataFrame: The results of the backtest.
                list[OrderBook]: The order book history.
                list[list[Order]]: The transactions history.
        """

        quotes = np.zeros(len(self.prices))
        bases = np.zeros(len(self.prices))
        order_book_history = np.empty(len(self.prices), dtype=OrderBook)
        transaction_history = []

        loading_bar = tqdm(total=len(self.prices))

        for i, state in enumerate(self._generate_kandel_states(loading_bar)):
            quotes[i] = state["quote"]
            bases[i] = state["base"]
            order_book_history[i] = state["order_book"]
            transaction_history.append(state["transactions"])

        res = DataFrame(
            {
                "quote": quotes,
                "base": bases,
            }
        )

        return res, order_book_history, transaction_history
