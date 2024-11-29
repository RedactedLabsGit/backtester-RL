import math
import numpy as np
from tabulate import tabulate
from termcolor import colored


from src.order import Order, OrderType


class OrderBook:
    ticks_grid: list[float]

    def __init__(self, initial_price: float, decimals_diff: int) -> None:
        self.orders = np.array([])
        self.current_price = initial_price
        self.decimals_diff = decimals_diff

    def __repr__(self):
        return str(self)

    def __str__(self):
        table_data = []
        for i, order in enumerate(self.orders[::-1]):
            tick = order.tick
            qty = order.qty
            price = order.price
            side_color = "green" if order.order_type == OrderType.BID else "red"
            table_data.append(
                [
                    i,
                    colored(str(order.order_type)[10:], side_color),
                    colored(tick, side_color),
                    colored(qty, side_color),
                    colored(price, side_color),
                    colored(qty * price, side_color),
                ]
            )

        headers = ["Index", "Type", "Tick", "Size", "Price", "Total"]
        table = tabulate(table_data, headers=headers, tablefmt="simple_outline")

        return table

    def to_dict(self) -> dict:
        return {
            "bids": [
                order.price
                for order in self.orders
                if order.order_type == OrderType.BID
            ],
            "asks": [
                order.price
                for order in self.orders
                if order.order_type == OrderType.ASK
            ],
        }

    def get_state(self):
        return self.to_dict()

    def get_first_ask_index(self) -> int:
        mid_tick = price_to_tick(self.current_price, self.decimals_diff)

        for first_ask_index in range(len(self.ticks_grid)):
            if self.ticks_grid[first_ask_index] > mid_tick:
                break

        return first_ask_index

    def build_book(self, capital: float, ticks_grid: list[int]) -> None:
        self.ticks_grid = ticks_grid

        if len(ticks_grid) == 0:
            self.orders = np.array([])
            return

        n_points = len(ticks_grid) - 1
        first_ask_index = self.get_first_ask_index()
        self.orders = np.empty(n_points, dtype=Order)

        if first_ask_index > 1:
            self.orders[:first_ask_index] = np.array(
                [
                    Order(
                        OrderType.BID,
                        tick,
                        capital / tick_to_price(tick, self.decimals_diff) / n_points,
                        tick_to_price(tick, self.decimals_diff),
                    )
                    for tick in ticks_grid[:first_ask_index]
                ]
            )
        if first_ask_index < n_points:
            self.orders[first_ask_index - 1 :] = np.array(
                [
                    Order(
                        OrderType.ASK,
                        tick,
                        capital / self.current_price / n_points,
                        tick_to_price(tick, self.decimals_diff),
                    )
                    for tick in ticks_grid[first_ask_index:]
                ]
            )

    def add_order(self, new_order: Order) -> None:
        if new_order.price < self.orders[0].price:
            self.orders = np.insert(self.orders, 0, new_order)
            return

        for i in range(len(self.orders)):
            if (
                new_order.price == self.orders[i].price
                and new_order.order_type == self.orders[i].order_type
            ):
                self.orders[i].qty += new_order.qty
                return
            # Same price, different type
            if new_order.price == self.orders[i].price:
                self.orders = np.insert(self.orders, i, new_order)
                return

            if self.orders[i].price < new_order.price and i == len(self.orders) - 1:
                self.orders = np.append(self.orders, new_order)
                return

            if self.orders[i].price < new_order.price < self.orders[i + 1].price:
                self.orders = np.insert(self.orders, i + 1, new_order)
                return

    def place_dual_offers(self, transactions: list[Order]) -> tuple[float, float]:
        side = transactions[0].order_type
        quote_change = 0
        base_change = 0

        for transaction in transactions:
            if side == OrderType.BID:
                quote_change -= transaction.price * transaction.qty
                base_change += transaction.qty
                order_tick = self.ticks_grid[
                    self.ticks_grid.index(transaction.tick) + 1
                ]
                self.add_order(
                    Order(
                        OrderType.ASK,
                        order_tick,
                        transaction.qty,
                        tick_to_price(order_tick, self.decimals_diff),
                    )
                )
            elif side == OrderType.ASK:
                quote_change += transaction.price * transaction.qty
                base_change -= transaction.qty
                order_tick = self.ticks_grid[
                    self.ticks_grid.index(transaction.tick) - 1
                ]
                self.add_order(
                    Order(
                        OrderType.BID,
                        order_tick,
                        transaction.qty
                        * transaction.price
                        / tick_to_price(order_tick, self.decimals_diff),
                        tick_to_price(order_tick, self.decimals_diff),
                    )
                )

        return quote_change, base_change

    def arbitrate(self, spot_price: float) -> list[Order]:
        transactions = []

        if spot_price < self.current_price:
            transactions.extend(
                order
                for order in self.orders
                if order.order_type == OrderType.BID and spot_price <= order.price
            )
            self.orders = np.array(
                [
                    order
                    for order in self.orders
                    if (order.order_type == OrderType.BID and spot_price > order.price)
                    or order.order_type == OrderType.ASK
                ]
            )

        elif spot_price > self.current_price:
            transactions.extend(
                order
                for order in self.orders
                if order.order_type == OrderType.ASK and spot_price >= order.price
            )
            self.orders = np.array(
                [
                    order
                    for order in self.orders
                    if (order.order_type == OrderType.ASK and spot_price < order.price)
                    or order.order_type == OrderType.BID
                ]
            )

        self.current_price = spot_price

        return transactions


def price_to_tick(price: float, decimals_diff: int) -> int:
    return math.floor(math.log(price / 10**decimals_diff) / math.log(1.0001))


def tick_to_price(tick: int, decimals_diff: int) -> float:
    return 1.0001**tick * 10 ** (decimals_diff)
