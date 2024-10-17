from pandas import Series, DataFrame
from src.kandel_v2 import KandelConfig, Kandel
from src.order import Order
from src.order_book import OrderBook


class KandelBacktester:
    """Kandel Backtester Class.
    KandelBacktester is used to backtest the Kandel strategy.

    Attributes:
        prices (Series):
            The price time series.
        kandel (Kandel):
            The Kandel strategy.
        exit_vol (Series):
            The volatility time series for the exit strategy.


    Methods:
        run():
            Run the backtest.
    """

    def __init__(
        self,
        prices: Series,
        config: KandelConfig,
        exit_vol: Series,
    ) -> None:
        self.prices = prices
        self.kandel = Kandel(config, OrderBook())
        self.exit_vol = exit_vol

    def run(self) -> tuple[list[Order], DataFrame, list[OrderBook]]:
        """Run the backtest.
        Run the backtest for the Kandel strategy.

        Returns:
            Tuple of list of transactions, DataFrame of quotes|bases|mtm and a list of the order book historical states.
        """
