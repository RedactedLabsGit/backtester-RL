from math import isclose
import uuid

TOLERANCE = 1e-7
DECIMALS = 6


class Order:
    order_type: str
    qty: float
    price: float
    uuid: uuid.UUID

    def __init__(self, order_type: str, qty: float, price: float) -> None:
        if order_type not in ["bid", "ask"]:
            raise ("order_type not bid nor ask")
        self.order_type = order_type
        self.qty = round(qty, DECIMALS)
        self.price = round(price, DECIMALS)
        self.uuid = uuid.uuid4()

    def copy(self):
        return Order(self.order_type, self.qty, self.price)

    def test(self, obj):
        if not isinstance(obj, Order):
            print("not an order")

    def __str__(self) -> str:
        return "{type} {quantity}@{price}".format(
            type=self.order_type, quantity=self.qty, price=self.price
        )

    def __repr__(self):
        return str(self)

    def __eq__(self, obj):
        return (
            isinstance(obj, Order)
            and obj.order_type == self.order_type
            and isclose(obj.price, self.price, rel_tol=TOLERANCE)
            and isclose(obj.qty, self.qty, rel_tol=TOLERANCE)
        )  # and obj.uuid == self.uuid

    def __lt__(self, obj):
        if not isinstance(obj, Order):
            return False
        if self.order_type == obj.order_type:
            return (self.price < obj.price) ^ (self.order_type == "bid")
        else:
            return self.price < obj.price
