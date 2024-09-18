import math


# initialisation of univ3 type to 
def concentrator(price, lower_price_bound, upper_price_bound):
    """
    Implementation of concentrator Univ3 concept / see cash_ratio.pdf
    ---------------
        Parameter
    ---------------
    lower_price_bound: float
    price: float
    upper_price_bound: float

    """
    #print(price, lower_price_bound, upper_price_bound)
    if (price < lower_price_bound or price > upper_price_bound):
        raise Exception("Price is not in range")
    inverse_concentrator = (2 * math.sqrt(price) - price/math.sqrt(upper_price_bound) - math.sqrt(lower_price_bound))
    return 1/inverse_concentrator
    

def initial_inventory_allocation(curr_price, p_min, p_max, capital):
    """ 
    Computes base_quantity(A) et quote_quantity(B) at initialisation
    depending on current price and capital provided.

    Args:
        curr_price (float): Current price
        p_min (float): Price min of the range
        p_max (float): Price max of the range
        capital (float): Capital provided in stable

    Returns:
        tuple: base
    """
    #  price in range
    if (curr_price >= p_min and curr_price <= p_max): 
        concentrator_val = capital * concentrator(curr_price,p_min,p_max)
        base_quantity = concentrator_val * (1/math.sqrt(curr_price) - 1/math.sqrt(p_max))
        quote_quantity = concentrator_val * (math.sqrt(curr_price) - math.sqrt(p_min))
        return (base_quantity, quote_quantity)
    
    # only asset, all asks on indices > 0
    if (curr_price < p_min):
        base_quantity = capital/curr_price 
        quote_quantity = 0  
        return (base_quantity, quote_quantity)   
    
    # only cash, all bids on indices < nb_slots - 1
    if (curr_price > p_max): 
        base_quantity = 0
        quote_quantity = capital 
        return (base_quantity, quote_quantity)     
