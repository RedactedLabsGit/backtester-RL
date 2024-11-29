import numpy as np
from typing import TypedDict

from src.order_book import OrderBook, price_to_tick
from src.order import OrderType


class KandelConfig(TypedDict):
    """
    KandelConfig is used to store the configuration of the Kandel strategy.

    Attributes:
        initial_capital (float):
            The initial capital size.
        decimals_diff (int):
            The difference between base decimals & quote decimals.
        performance_fees (float):
            The performance fees.
        vol_mult (float):
            The volatility multiplier, used to make the position range dynamic based on vol.
        range_mult (float):
            The range multiplier, used to make the position range dynamic based on price.
        n_points (int):
            The number of bids and asks on each side of the price.
        step_size (int):
            The number of points that the kandel should skip when adding new order.
        window (int):
            The time window to rebalance strategy, will also compute the volatility for the range on it.
        exit_vol_threshold (float):
            The exit volatility threshold.
        asymmetric_exit_threshold (float):
            The threshold at which the strategy will not exit in 50/50.
    """

    initial_capital: float
    decimals_diff: int
    performance_fees: float
    vol_mult: float
    range_mult: float
    n_points: int
    step_size: int
    window: int
    exit_vol_threshold: float
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
        ticks_grid (list[int]):
            The ticks grid.
        order_book (OrderBook):
            The order book.
        is_active (bool):
            The flag to check if the strategy is active.

    Methods:
        _update_ticks_grid(self) -> None:
            Update the geometrical ticks grid for orders distribution.
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
        self.base = config["initial_capital"] / 2 / spot_price
        self.quote = config["initial_capital"] / 2
        self.open_price = spot_price
        self.open_capital = config["initial_capital"]
        self.vol = vol
        self.ticks_grid = []
        self._update_ticks_grid()
        self.order_book = OrderBook(
            initial_price=spot_price,
            decimals_diff=config["decimals_diff"],
        )
        self.order_book.build_book(
            capital=config["initial_capital"],
            ticks_grid=self.ticks_grid,
        )
        self.is_active = True
        if self.should_exit(exit_vol):
            self.exit()

    def _update_ticks_grid(self) -> None:
        """
        Compute the geometrical ticks grid for orders distribution based on the current spot price, vol and config.
        """
        if self.config["vol_mult"] != 0:
            range_multiplier = np.exp(self.config["vol_mult"] * self.vol)
            gridstep = range_multiplier ** (1 / self.config["n_points"])
        else:
            gridstep = self.config["range_mult"] ** (1 / self.config["n_points"])
        min_tick = price_to_tick(
            self.spot_price / gridstep ** self.config["n_points"],
            self.config["decimals_diff"],
        )
        max_tick = price_to_tick(
            self.spot_price * gridstep ** self.config["n_points"],
            self.config["decimals_diff"],
        )

        self.ticks_grid = np.unique(
            np.linspace(
                min_tick,
                max_tick,
                self.config["n_points"] * 2 + 1,
                dtype=int,
            )
        ).tolist()

        if len(self.ticks_grid) % 2 != 1:
            self.ticks_grid = self.ticks_grid[:-1]

    def rebalance(self) -> float:
        """
        Rebalance the orderbook on the current spot price.

        Returns:
            float: The generated fees.
        """
        self._update_ticks_grid()
        capital = self.quote + self.base * self.spot_price
        generated_fees = (
            (capital - self.open_capital) * self.config["performance_fees"]
            if capital > self.open_capital
            else 0
        )
        capital -= generated_fees

        self.order_book.current_price = self.spot_price
        self.order_book.build_book(capital=capital, ticks_grid=self.ticks_grid)

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

        self.order_book.build_book(capital=0, ticks_grid=[])
        self.is_active = False

    def should_exit(self, exit_vol: float) -> bool:
        """
        Check if the strategy should exit based on the volatility.

        Args:
            exit_vol (float):
                The volatility for the exit strategy.
        """
        return exit_vol > self.config["exit_vol_threshold"]

    def update_kandel_state(
        self, spot_price: float, window_vol: float, exit_vol: float
    ) -> None:
        """


        Args:
            spot_price (float):
                The new spot price.
        """
        self.spot_price = spot_price
        self.vol = window_vol

        if self.is_active:
            transactions = self.order_book.arbitrate(self.spot_price)
            if transactions:
                quote_change, base_change = self.order_book.place_dual_offers(
                    transactions
                )
                self.quote += quote_change
                self.base += base_change
            if self.should_exit(exit_vol):
                self.exit()
