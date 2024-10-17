import numpy as np
from typing import TypedDict
from sortedcontainers import SortedList

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
    """

    initial_base: float
    initial_quote: float
    vol_mult: float
    n_points: int
    step_size: int
    window: int
    vol_threshold: float


class Kandel:
    """
    Kandel is an implementation of a Kandel strategy.

    Attributes:
        config (KandelConfig):
            The configuration for the Kandel strategy.
        spot_price (float):
            The current spot price.
        vol (float):
            The volatility on past window.
        base (float):
            The base size.
        quote (float):
            The quote size.
        price_grid (list[float]):
            The price grid.
        order_book (OrderBook):
            The order book.

    Methods:
        _compute_price_grid(self) -> list[float]:
            Compute the geometrical price grid for orders distribution.
    """

    def __init__(self, config: KandelConfig, spot_price: float, vol: float) -> None:
        self.config = config
        self.spot_price = spot_price
        self.vol = vol
        self.base = config["initial_base"]
        self.quote = config["initial_quote"]
        self.price_grid = []
        self._update_price_grid()
        self.order_book = build_book(
            capital=config["initial_quote"] + config["initial_base"] * spot_price,
            price_grid=self.price_grid,
            initial_price=spot_price,
        )

    def _update_price_grid(self) -> list[float]:
        """
        Compute the geometrical price grid for orders distribution.

        Args:
            vol (float):
                The volatility.

        Returns:
            List of floats representing the price grid.
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

    def rebalance(self) -> None:
        """
        Rebalance the Kandel orderbook.
        """
        self._update_price_grid()
        self.order_book = build_book(
            capital=self.quote + self.base * self.spot_price,
            price_grid=self.price_grid,
            initial_price=self.spot_price,
        )

    def update(self, spot_price: float, vol: float) -> None:
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

    def place_dual_offers(self, transactions: list[Order]) -> None:
        """
        Place dual offers on the order book.

        Args:
            transactions (List[Order]):
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

    def arbitrate_orderbook(self) -> None:
        """
        Arbitrate the orderbook base on the current price.

        Returns:
            List of transactions.
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
            self.place_dual_offers(transactions)
