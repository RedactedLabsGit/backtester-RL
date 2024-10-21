from sortedcontainers import SortedList
from typing import TypedDict
import numpy as np

from src.order_book import OrderBook, build_book, add_limit_order
from src.order import Order


class KandelConfig(TypedDict):
    """
    KandelConfig is used to store the configuration of the Kandel strategy.

    Attributes:
        initial_base (float):
            The initial base size.
        initial_quote (float):
            The initial quote size.
        vol_mult (float):
            The volatility multiplier, used to make the position range dynamic.
        n_points (int):
            The number of bids and asks on each side of the price.
        step_size (int):
            The number of points that the kandel should skip when adding new order.
        window (int):
            The time window to rebalance strategy, will also compute the volatility for the range on it.
        vol_threshold (float):
            The volatility threshold.
        asymmetric_exit_threshold (float):
            The threshold at which the strategy will not exit in 50/50.
    """

    initial_base: float
    initial_quote: float
    vol_mult: float
    n_points: int
    step_size: int
    window: int
    vol_threshold: float
    asymmetric_exit_threshold: float


class Kandel:
    """
    Kandel is an implementation of a Kandel strategy.

    Attributes:
        config (KandelConfig):
            The configuration for the Kandel strategy.
        spot_price (float):
            The current spot price.
        base (float):
            The base size.
        quote (float):
            The quote size.
        open_price (float):
            The spot price at the beginning of the current position.
        open_capital (float):
            The capital at the beginning of the current position.
        vol (float):
            The volatility on past window.
        price_grid (list[float]):
            The price grid.
        order_book (OrderBook):
            The order book.
        is_active (bool):
            The flag to check if the strategy is active.

    Methods:
        _update_price_grid(self) -> None:
            Update the geometrical price grid for orders distribution.
        rebalance(self) -> float:
            Rebalance the order book on the current spot price.
        exit(self) -> None:
            Exit the Kandel strategy.
        should_exit(self, exit_vol: float) -> bool:
            Check if the strategy should exit based on the volatility
        update_spot_and_vol(self, spot_price: float, vol: float) -> None:
            Update the Kandel strategy with new spot price and volatility.
        _place_dual_offers(self, transactions: list[Order]) -> None:
            Place dual offers on the order book.
        arbitrate_order_book(self) -> list[Order]:
            Arbitrate the order book based on the current spot price.
    """

    def __init__(
        self, config: KandelConfig, spot_price: float, vol: float, exit_vol: float
    ) -> None:
        """
        Initialize the Kandel strategy.

        Args:
            config (KandelConfig):
                The configuration for the Kandel strategy.
            spot_price (float):
                The current spot price.
            vol (float):
                The volatility on past window.
            exit_vol (float):
                The volatility for the exit strategy.
        """

        self.config = config
        self.spot_price = spot_price
        self.base = config["initial_base"]
        self.quote = config["initial_quote"]
        self.open_price = spot_price
        self.open_capital = (
            config["initial_base"] * spot_price + config["initial_quote"]
        )
        self.vol = vol
        self.price_grid = []
        self._update_price_grid()
        self.order_book = build_book(
            capital=config["initial_quote"] + config["initial_base"] * spot_price,
            price_grid=self.price_grid,
            initial_price=spot_price,
        )
        self.is_active = True
        if self.should_exit(exit_vol):
            self.exit()

    def _update_price_grid(self) -> None:
        """
        Compute the geometrical price grid for orders distribution based on the current spot price, vol and config.
        """
        range_multiplier = np.exp(self.config["vol_mult"] * self.vol)
        gridstep = range_multiplier ** (1 / self.config["n_points"])
        bids = [
            self.spot_price / gridstep**i for i in range(1, self.config["n_points"] + 1)
        ]
        asks = [
            self.spot_price * gridstep**i for i in range(1, self.config["n_points"] + 1)
        ]

        self.price_grid = bids[::-1] + [self.spot_price] + asks

    def rebalance(self) -> float:
        """
        Rebalance the orderbook on the current spot price.

        Returns:
            float: The generated fees.
        """
        self._update_price_grid()
        capital = self.quote + self.base * self.spot_price
        generated_fees = (
            (capital - self.open_capital) * 0.1 if capital > self.open_capital else 0
        )
        capital -= generated_fees
        self.order_book = build_book(
            capital=capital,
            price_grid=self.price_grid,
            initial_price=self.spot_price,
        )
        self.quote = capital / 2
        self.base = self.quote / self.spot_price
        self.open_price = self.spot_price
        self.open_capital = capital

        self.is_active = True

        return generated_fees

    def exit(self) -> None:
        """
        Exit the Kandel strategy.
        """
        open_close_ratio = self.spot_price / self.open_price - 1
        if open_close_ratio > self.config["asymmetric_exit_threshold"]:
            self.quote = (self.quote + self.base * self.spot_price) * 0.25
            self.base = (self.quote * 3) / self.spot_price
        elif open_close_ratio < -self.config["asymmetric_exit_threshold"]:
            self.quote = (self.quote + self.base * self.spot_price) * 0.75
            self.base = (self.quote / 3) / self.spot_price
        else:
            self.quote = (self.quote + self.base * self.spot_price) / 2
            self.base = self.quote / self.spot_price

        self.order_book = OrderBook()
        self.is_active = False

    def should_exit(self, exit_vol: float) -> bool:
        """
        Check if the strategy should exit based on the volatility.

        Args:
            exit_vol (float):
                The volatility for the exit strategy.
        """
        return exit_vol > self.config["vol_threshold"]

    def update_spot_and_vol(self, spot_price: float, vol: float) -> None:
        """
        Update the Kandel strategy with new spot price and volatility.

        Args:
            spot_price (float):
                The new spot price.
            vol (float):
                The new volatility.
        """
        self.spot_price = spot_price
        self.vol = vol

    def _place_dual_offers(self, transactions: list[Order]) -> None:
        """
        Place dual offers on the order book.

        Args:
            transactions (list[Order]):
                The executed transactions from arbitrage.
        """
        bids_map = {
            round(price, 6): round(self.price_grid[i + self.config["step_size"]], 6)
            for i, price in enumerate(self.price_grid[: (-self.config["step_size"])])
        }
        asks_map = {
            round(price, 6): round(self.price_grid[i - self.config["step_size"]], 6)
            for i, price in enumerate(
                self.price_grid[self.config["step_size"] :],
                start=self.config["step_size"],
            )
        }

        for transaction in transactions:
            side = transaction.order_type
            if side == "bid":
                self.quote -= transaction.price * transaction.qty
                self.base += transaction.qty
                new_order = Order("ask", transaction.qty, bids_map[transaction.price])
                self.order_book = add_limit_order(new_order, self.order_book)
            if side == "ask":
                self.quote += transaction.price * transaction.qty
                self.base -= transaction.qty
                new_order = Order(
                    "bid",
                    transaction.qty * transaction.price / asks_map[transaction.price],
                    asks_map[transaction.price],
                )
                self.order_book = add_limit_order(new_order, self.order_book)

    def arbitrate_order_book(self) -> list[Order]:
        """
        Arbitrate the order book based on the current spot price.

        Returns:
            list[Order]: List of transactions executed.
        """
        transactions = []

        if self.order_book.bids:
            transactions.extend(
                order
                for order in self.order_book.bids
                if self.spot_price <= order.price
            )
            self.order_book.bids = SortedList(
                [
                    order
                    for order in self.order_book.bids
                    if self.spot_price > order.price
                ]
            )

        if self.order_book.asks:
            transactions.extend(
                order
                for order in self.order_book.asks
                if self.spot_price >= order.price
            )
            self.order_book.asks = SortedList(
                [
                    order
                    for order in self.order_book.asks
                    if self.spot_price < order.price
                ]
            )

        if transactions:
            self._place_dual_offers(transactions)

        return transactions
