from enum import Enum


class OrderType(Enum):
    """Order type enum class"""

    BID = 1
    ASK = 2


class Order:
    """Order class

    Attributes:
        order_type (OrderType): Order type
        tick (int): Tick
        qty (float): Quantity
        price (float): Price
    """

    def __init__(
        self, order_type: OrderType, tick: int, qty: float, price: float
    ) -> None:
        """Initialize an order.

        Args:
            order_type (OrderType): Order type
            tick (int): Tick
            qty (float): Quantity
            price (float): Price
        """

        self.order_type = order_type
        self.tick = tick
        self.qty = qty
        self.price = price

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return f"{str(self.order_type)} | {self.tick} | {self.qty} | {self.price}"
