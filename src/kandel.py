from typing import List, Tuple, Callable, Union
import numpy as np
from sortedcontainers import SortedList
from tqdm import tqdm

from src.time_series import TS, col_concat
from src.order_book import (
    Order,
    OrderBook,
    add_limit_order,
    build_book,
    arbitrage_order_book,
)
from src.fin_stats import bollinger_bands_, vol_, log_ret_

DECIMALS = 6


def kandel_reset(
    quote: float,
    base: float,
    price: float,
    price_grid: np.array,
    step_size: int,
    transactions: List = [],
    order_book: OrderBook = OrderBook(),
    init: bool = False,
) -> Tuple[Tuple[float, float], OrderBook]:

    bids_map = {
        round(price, DECIMALS): round(price_grid[i + step_size], DECIMALS)
        for i, price in enumerate(price_grid[:(-step_size)])
    }
    asks_map = {
        round(price, DECIMALS): round(price_grid[i - step_size], DECIMALS)
        for i, price in enumerate(price_grid[step_size:], start=step_size)
    }

    if init:
        order_book = build_book(
            capital=quote + base * price, price_grid=price_grid, initial_price=price
        )

        return ((quote, base), order_book)

    if (not transactions) and (not init):
        # If nothing happened and not initialization the do nothing return order book
        return ((quote, base), order_book)

    # Update quote and base amounts and update order_book
    for transaction in transactions:
        side = transaction.order_type
        if side == "bid":
            # I bought
            quote -= transaction.price * transaction.qty
            base += transaction.qty
            new_order = Order("ask", transaction.qty, bids_map[transaction.price])
            order_book = add_limit_order(new_order, order_book)
        if side == "ask":
            # I sold
            quote = quote + (transaction.price * transaction.qty)
            base = base - transaction.qty
            new_order = Order(
                "bid",
                transaction.qty * transaction.price / asks_map[transaction.price],
                asks_map[transaction.price],
            )
            order_book = add_limit_order(new_order, order_book)

    return (quote, base), order_book


def geom_price_grid(
    ts: TS, window: int, spot_price: float, vol_mult: float = 1.645, n_points: int = 10
) -> List:

    # Take window to calculate vol for price_grid
    sig = vol_(log_ret_(ts[-window:])) / np.sqrt(365)
    range_multiplier = np.exp(vol_mult * sig)
    gridstep = range_multiplier ** (1 / n_points)
    bids = [spot_price / gridstep**i for i in range(1, n_points + 1)]
    asks = [spot_price * gridstep**i for i in range(1, n_points + 1)]

    return bids[::-1] + [spot_price] + asks


def kandel_simulator(
    ts: Union[TS, List[str]],
    quote: float,
    base: float,
    vol_mult: float,
    n_points: int,
    step_size: int,
    window: int,
) -> TS:

    # Results Initialization
    quotes = np.zeros(ts.n_rows)
    bases = np.zeros(ts.n_rows)
    volume = np.zeros(ts.n_rows)
    uptime = np.zeros(ts.n_rows)
    tot_transactions = []
    order_book_history = []
    spot_price = ts.values[0][window]

    base = base / spot_price
    quotes[: (1 if window == 0 else window + 1)] = quote
    bases[: (1 if window == 0 else window + 1)] = base
    volume[: (1 if window == 0 else window + 1)] = 0
    uptime[: (1 if window == 0 else window + 1)] = 0

    price_grid = geom_price_grid(ts[:window], window, spot_price, vol_mult, n_points)

    (quote, base), order_book = kandel_reset(
        quote, base, spot_price, price_grid, step_size, init=True
    )
    order_book_history.append(order_book)

    # For every unit of time starting at window
    for i in tqdm(range(window, ts.n_rows)):
        spot_price = ts.values[0][i]
        # if spot_price > price_grid[-1]:
        #     up_exit = up_exit[i - 1] + 1
        # if spot_price < price_grid[0]:
        #     down_exit = down_exit[i - 1] + 1

        transactions, order_book = arbitrage_order_book(
            price=spot_price, order_book=order_book
        )

        uptime[i] = (
            0
            if (
                not order_book.asks
                or spot_price > order_book.asks[-1].price
                or not order_book.bids
                or spot_price < order_book.bids[-1].price
            )
            else 1
        )

        tot_transactions.append(transactions)
        (quote, base), order_book = kandel_reset(
            quote,
            base,
            spot_price,
            price_grid,
            step_size,
            transactions,
            order_book,
            init=False,
        )
        order_book_history.append(order_book)

        if i % window == 0:

            # if reset time then reset price_grid
            # print('Reset')
            price_grid = geom_price_grid(
                ts[i - window : i], window, spot_price, vol_mult, n_points
            )

            # Sell all base before rebalancing
            quote = quote + base * spot_price
            base = 0
            (quote, base), order_book = kandel_reset(
                quote,
                base,
                spot_price,
                price_grid,
                step_size,
                transactions=[],
                order_book=OrderBook(),
                init=True,
            )

        quotes[i] = quote
        bases[i] = base
        volume[i] = sum([t.price * t.qty for t in transactions])

    mtm = quotes + bases * ts.values[0]

    res = TS(
        row_names=ts.row_names,
        unit=ts.unit,
        n_rows=ts.n_rows,
        col_names=["quote", "base", "mtm", "volume", "uptime"],
        values=np.array((quotes, bases, mtm, volume, uptime)),
    )
    res = col_concat(ts, res)
    return tot_transactions, res, order_book_history
