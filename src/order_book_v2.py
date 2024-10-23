import numpy as np
from tabulate import tabulate
from termcolor import colored
import copy


from src.order_v2 import Order, OrderType


class OrderBook:
    price_grid: list[float]

    def __init__(self, initial_price: float) -> None:
        self.orders = np.array([])
        self.current_price = initial_price

    def __repr__(self):
        return str(self)

    def __str__(self):
        table_data = []
        for i, order in enumerate(self.orders[::-1]):
            qty = order.qty
            price = order.price
            side_color = "green" if order.order_type == OrderType.BID else "red"
            table_data.append(
                [
                    i,
                    colored(qty, side_color),
                    colored(price, side_color),
                    colored(qty * price, side_color),
                ]
            )

        headers = ["Index", "Size", "Price", "Total"]
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

    def build_book(self, capital: float, price_grid: list[float]) -> None:
        self.price_grid = price_grid

        if len(price_grid) == 0:
            self.orders = np.array([])
            return

        nb_price_points = len(price_grid) - 1
        self.orders = np.empty(nb_price_points, dtype=Order)

        self.orders[: nb_price_points // 2] = np.array(
            [
                Order(OrderType.BID, capital / price / nb_price_points, price)
                for price in price_grid[: nb_price_points // 2]
            ]
        )
        self.orders[nb_price_points // 2 :] = np.array(
            [
                Order(
                    OrderType.ASK, capital / self.current_price / nb_price_points, price
                )
                for price in price_grid[nb_price_points // 2 + 1 :]
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
                order_price = self.price_grid[
                    self.price_grid.index(transaction.price) + 1
                ]
                self.add_order(
                    Order(
                        OrderType.ASK,
                        transaction.qty,
                        order_price,
                    )
                )
            elif side == OrderType.ASK:
                quote_change += transaction.price * transaction.qty
                base_change -= transaction.qty
                order_price = self.price_grid[
                    self.price_grid.index(transaction.price) - 1
                ]
                self.add_order(
                    Order(
                        OrderType.BID,
                        transaction.qty * transaction.price / order_price,
                        order_price,
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
