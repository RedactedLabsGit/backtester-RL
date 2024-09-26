import uuid
from math import isclose
from sortedcontainers import SortedList
import numpy as np
import pandas as pd
from typing import Tuple, List
import copy
from tabulate import tabulate
from termcolor import colored


from src.order import Order
from src.utils_inventory import initial_inventory_allocation
from src.utils_grid import cursor


TOLERANCE = 1e-7
DECIMALS = 6


class OrderBook:
    bids: SortedList
    asks: SortedList

    def __init__(
        self, bids: SortedList = SortedList(), asks: SortedList = SortedList()
    ) -> None:
        self.bids = bids
        self.asks = asks

    def __repr__(self):
        return str(self)

    def __str__(self):
        # Combine bids and asks into a single list
        orders = sorted(self.asks + self.bids, key=lambda x: x.price, reverse=True)

        # Initialize table data
        table_data = []

        # Format each order and add to table data
        for i, order in enumerate(orders):
            qty = order.qty
            price = order.price
            total = qty
            side_color = "green" if order.order_type == "bid" else "red"
            table_data.append(
                [
                    i,
                    colored(qty, side_color),
                    colored(price, side_color),
                    colored(qty * price, side_color),
                ]
            )

        # Print the table with color
        headers = ["Index", "Size", "Price", "Total"]
        table = tabulate(table_data, headers=headers, tablefmt="simple_outline")

        return table

    def to_pandas(self):
        orders = sorted(self.bids + self.asks, key=lambda x: x.price)

        # Initialize table data
        return pd.DataFrame(
            [(o.order_type, o.qty, o.price, o.qty * o.price) for o in orders],
            columns=["Side", "Size", "Price", "Total"],
        ).sort_values(["Side", "Price"], ascending=(True, False))

    def to_dict(self):
        if not self.bids and not self.asks:
            return {"bids": [], "asks": []}
        if not self.bids:
            return {
                "bids": [],
                "asks": [a.price for a in self.asks],
            }
        if not self.asks:
            return {
                "bids": [b.price for b in self.bids],
                "asks": [],
            }
        return {
            "bids": [b.price for b in self.bids],
            "asks": [a.price for a in self.asks],
        }

    def copy(self):
        return OrderBook(self.bids, self.asks)

    def get_prices(self) -> List[float]:
        if not self.asks:
            return [i.price for i in self.bids]
        if not self.bids:
            return [i.price for i in self.asks]
        return [i.price for i in self.bids.update(self.asks)]

    def get_orders(self) -> SortedList:
        if not self.asks:
            return [i for i in self.bids]
        if not self.bids:
            return [i for i in self.asks]
        return [i for i in self.bids.update(self.asks)]


def add_limit_order(order: Order, order_book: OrderBook) -> OrderBook:

    bids = (
        copy.deepcopy(order_book.bids)
        if (order_book and order_book.bids)
        else SortedList()
    )
    asks = (
        copy.deepcopy(order_book.asks)
        if (order_book and order_book.asks)
        else SortedList()
    )

    res = OrderBook(bids, asks)
    order.price = round(order.price, DECIMALS)
    order.qty = round(order.qty, DECIMALS)

    if order.order_type == "bid":
        try:
            idx_bid = next(
                (i for i, o in enumerate(bids) if order.price == o.price), None
            )

        except StopIteration:
            # Need to check if bid I'm inserting crosses best ask
            if asks:
                if order.price >= asks[0].price and order.price < TOLERANCE:
                    raise ("bid order crosses best ask, not possible")
            idx_bid = None

        if idx_bid is not None:
            res.bids[idx_bid].qty += round(order.qty, DECIMALS)
        else:
            bids.add(order)

    elif order.order_type == "ask":
        try:
            idx_ask = next(
                (i for i, o in enumerate(asks) if order.price == o.price), None
            )
        except StopIteration:
            if bids:
                if order.price <= bids[0].price and order.price < TOLERANCE:
                    raise ("bid order crosses best ask, not possible")
            idx_ask = None

        if idx_ask is not None:
            res.asks[idx_ask].qty += round(order.qty, DECIMALS)
        else:
            asks.add(order)
    else:
        raise ("order_type not recognized")

    return res


def execute_market_order(
    price: float, qty: float, order_book: OrderBook
) -> Tuple[List[Order], OrderBook]:
    """
    Market order needs to buy/sell all up to the price in the order or to qty executed
    returns ([(price, qty) for each executed order], new_order_book)
    """

    to_trade = qty
    trades = []
    bids = order_book.bids.copy() if (order_book and order_book.bids) else SortedList()
    asks = order_book.asks.copy() if (order_book and order_book.asks) else SortedList()
    # if bids
    if len(bids) > 0:
        # if price greater than best bid nothind
        if price > bids[0].price:
            pass
        else:
            bid = bids[0]
            while bid and price <= bid.price and to_trade > TOLERANCE:
                # If not enough then all order is executed
                if to_trade >= bid.qty:
                    executed_order = bids.pop(0)
                    executed_order = (executed_order.price, executed_order.qty)
                    to_trade -= executed_order[1]
                else:
                    # If enough then to_trade is qty at this price
                    executed_order = Order("bid", bid.price, to_trade)
                    bids[0].qty -= to_trade
                    to_trade = 0

                bid = bids[0] if len(bids) > 0 else None
                trades.append(executed_order)
    if len(asks) > 0:
        # if price greater than best bid nothind
        if price < asks[0].price:
            pass
        else:
            ask = asks[0]
            while ask and price >= asks[0].price and to_trade > TOLERANCE:
                # If not enough then all order is executed
                if to_trade >= ask.qty:
                    executed_order = asks.pop(0)
                    executed_order = (executed_order.price, executed_order.qty)
                    to_trade -= executed_order[1]
                else:
                    # If enough then to_trade is qty at this price
                    executed_order = Order("ask", ask.price, to_trade)
                    asks[0].qty -= to_trade
                    to_trade = 0

                ask = asks[0] if len(asks) > 0 else None
                trades.append(executed_order)

    return (trades, (bids, asks))


def arbitrage_order_book(
    price: float, order_book: OrderBook
) -> Tuple[List[Order], OrderBook]:
    """
    Function in charge of arbitraging order_book based on price
    Pops all asks or bids up until to price
    returns (transactions, order_book)
    """
    transactions = []

    if order_book.bids:
        transactions.extend(order for order in order_book.bids if price <= order.price)
        order_book.bids = SortedList(
            [order for order in order_book.bids if price > order.price]
        )

    if order_book.asks:
        transactions.extend(order for order in order_book.asks if price >= order.price)
        order_book.asks = SortedList(
            [order for order in order_book.asks if price < order.price]
        )

    return transactions, order_book


def build_book(capital: float, price_grid: List, initial_price: float) -> OrderBook:
    """
    Function that inits our book of orders when the strategy is inited

    Args:
        capital (int, optional): capital in stable. Defaults to 1.
        price_grid (list, optional): Offers price grid. Defaults to [1000,5000].
        initial_price (int, optional): Current price at initialisation. Defaults to 1000.

    Raises:
        Exception: Capital positivity constraint
        Exception: Price grid min two points constraint
        Exception: Current Price positivity
        Exception: Initial Positivity constraint

    Returns:
        Tuple: Return a tuple (bids, asks)
    """
    nb_price_points = len(price_grid)

    if capital <= 0:
        raise Exception("Capital must be positive.")

    if nb_price_points < 2:
        raise Exception("Price grid must contains at least two points.")

    if initial_price <= 0:
        raise Exception("Current price need to be superior to 0")

    initial_capital_A, initial_capital_B = initial_inventory_allocation(
        initial_price, price_grid[0], price_grid[-1], capital
    )

    order_book = OrderBook()

    # Initial price is left of range, we only have asks !
    if initial_price <= price_grid[0]:
        # To check with nb_price_points -1
        list_quantity_A = [initial_capital_A / (nb_price_points - 1)] * (
            nb_price_points - 1
        )
        asks = SortedList(
            [Order("ask", q, p) for p, q in zip(price_grid[1:], list_quantity_A)]
        )
        return OrderBook(asks=asks)

    # Initial price right of range, we only have bids !
    if initial_price >= price_grid[-1]:
        # Since its quote we divide with each price grid value.
        sliced_price_grid = price_grid[:-1]
        list_quantity_B = np.array(
            [initial_capital_B / (nb_price_points - 1)] * (nb_price_points - 1)
        ) / np.array(sliced_price_grid)
        bids = SortedList(
            [
                Order("bid", q, p)
                for p, q in zip(sliced_price_grid, list(list_quantity_B))
            ]
        )
        return Order(bids=bids)

    floor_price0_index, floor_price0 = cursor(initial_price, price_grid)
    # print("floorprice", floor_price0_index, floor_price0)
    # Checking floor price index is None even if it's not possible with two previous ifs  (we never know)
    if floor_price0_index is None:
        raise Exception("Floor price index is None")

    nb_bids = floor_price0_index  # > 0
    # FIXME: Change with vectorized version
    for i in range(floor_price0_index - 1, -1, -1):
        # caveat: we buy a fixed value of A with initial_capital_B/price_grid[i] * 1/nb_bids
        # we could also buy a fixed amount of A at each bid; this is one way to do it
        list_quantity_B = initial_capital_B / nb_bids * 1 / price_grid[i]
        order_book = add_limit_order(
            Order("bid", list_quantity_B, price_grid[i]), order_book=order_book
        )

    # we fill asks above floor_price and leave no hole
    nb_asks = nb_price_points - nb_bids - 1  # should check > 0
    for i in range(floor_price0_index + 1, nb_price_points):
        list_quantity_A = initial_capital_A / nb_asks
        order_book = add_limit_order(
            Order("ask", list_quantity_A, price_grid[i]), order_book=order_book
        )

    # print(nb_asks, nb_bids)

    return order_book
