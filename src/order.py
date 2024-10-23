from enum import Enum


class OrderType(Enum):
    """Order type enum class"""

    BID = 1
    ASK = 2


class Order:
    """Order class

    Attributes:
        order_type (OrderType): Order type
        qty (float): Quantity
        price (float): Price
    """

    def __init__(self, order_type: OrderType, qty: float, price: float) -> None:
        """Initialize an order.

        Args:
            order_type (OrderType): Order type
            qty (float): Quantity
            price (float): Price
        """

        self.order_type = order_type
        self.qty = qty
        self.price = price
