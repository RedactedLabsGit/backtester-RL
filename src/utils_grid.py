import math
import numpy as np
from numpy import linspace


def price_grid_gen(price_grid_type="ari", price_range=(1, 100), price_increment=0.1):
    """Price Grid selector
    Execute the right price grid and checks for errors

    Args:
        price_grid_type (str, optional): Type of the price grid. Defaults to 'ari'.
        price_range (tuple, optional): Tuple of size 2 that contains (p_min,p_max).
        price_increment (float, optional): Price increment.

    Returns:
        _type_: _description_
    """
    p_min, p_max = price_range

    # Error Handling
    if price_increment <= 0:
        raise Exception("Price increment need to be strictly superior than 0")
    if p_min > p_max:
        raise Exception("P_min need to need to be higher than p_max")

    # Looking for the grid
    if price_grid_type == "ari":
        return ari_price_grid_gen(p_min, p_max, price_increment)
    elif price_grid_type == "geo":
        return geo_price_grid_gen(p_min, p_max, price_increment)
    else:
        raise Exception("Price grid type is not recognized.")


def geo_price_grid_gen(entry_price, end_price, ratio):
    # TODO: Handle entry_price < end_price.
    if ratio <= 1:
        raise Exception("Can't be negative or inferior to one")

    if entry_price < end_price:
        mylist = [entry_price]
        new_value = entry_price
        while round(new_value, 10) < round(end_price, 10):
            new_value = mylist[-1] * ratio
            mylist.append(new_value)
        # edit list elt minimum between end_price and last_elt
        mylist[-1] = end_price
        return mylist


def geo_price_grid_gen_old(p_min, p_max, price_increment=0.1):
    """Geometric price grid generator

    Args:
        p_min (float): Lower price grid bound
        p_max (float): Upper price grid bound
        price_increment (float, optional): Increment of the . Defaults to 0.1.

    Returns:
        _type_: _description_
    """
    if p_max < (1 + price_increment) * p_min:
        raise Exception("Price grid is too small to create a two points grid")

    nb_price_points = (
        math.floor(math.log(p_max / p_min) / math.log(1 + price_increment)) + 1
    )
    price_grid_log = np.linspace(math.log(p_min), math.log(p_max), nb_price_points)
    price_grid = list(map(lambda x: math.exp(x), price_grid_log))

    return nb_price_points, price_grid, price_grid[0], price_grid[-1]


def ari_price_grid_gen(p_min, p_max, price_increment=1):
    """Arithmetic price grid generator

    Args:
        p_min (float): price mind lower bound
        p_max (float): price grid upper bound
        price_increment (int, optional): price grid increment. Defaults to 1.

    Raises:
        Exception: Too small range defined.

    Returns:
        Tuple: Elements
    """

    if p_max - p_min < price_increment:
        raise Exception("Range is too small to create a two points grid.")

    nb_price_points = math.floor((p_max - p_min) / price_increment) + 1
    price_grid_raw = linspace(p_min, p_max, nb_price_points)
    price_grid = list(map(lambda x: x, price_grid_raw))

    # TODO: Too many arguments, better to reduce it to only 2.
    return nb_price_points, price_grid, price_grid[0], price_grid[-1]


def inverse_price_grid(price_grid):
    """Transform price grid list to a map
    price -> index

    Args:
        price_grid (list): Price grid lists

    Returns:
       Dict: Dict of ({price: index}) values
    """
    return {k: i for i, k in enumerate(price_grid)}


def cursor(specific_price, price_grid):
    """
    Look for a specific price on the price that exists
    such that price_grid[i] <= price < price_grid[i+1]

    Args:
        price (float): Price
        price_grid (float): _description_

    Returns:
        (int, float):  returns floor_price on grid, and floor_price_index
    """
    # look for price, index in the grid such that
    # iff there exists i such that price_grid[i] <= price < price_grid[i+1]

    if len(price_grid) < 2:
        raise Exception("Price grid need to have at least two points")

    if specific_price < price_grid[0]:
        print("Current price is inferior to p_min")  # price is below range
        return (None, 0.0)

    if specific_price > price_grid[-1]:
        print("Current price is > p_max")  # price is above range
        return (None, np.inf)

    floor_price = None
    floor_price_index = None

    # TODO: Ameliorate by doing a research
    for index, price_point in enumerate(price_grid):
        if specific_price > price_point:
            floor_price = price_point
            floor_price_index = index

        elif specific_price < price_point:
            return floor_price_index, floor_price

        elif specific_price == price_point:
            return (index, price_point)


"""
Generates a prices series with random brownian jumps
return: a price series
"""


def brownian_price_series_generator(
    duration=10, initial_price=2000.0, volatility=1.0, seed=12
):
    np.random.seed(seed)
    price_jumps = np.random.randn(duration) * volatility
    price_jumps = list(map(lambda x: x, price_jumps))
    # adding to brownian jumps list initial price.
    price_series = initial_price + np.cumsum(price_jumps)
    return list(map(lambda x: abs(x), price_series))
