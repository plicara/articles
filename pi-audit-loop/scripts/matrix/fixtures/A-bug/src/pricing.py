"""Order pricing."""

DEFAULT_DISCOUNT = 0.10


def order_total(subtotal: float, discount: float = None) -> float:
    """Total for a subtotal with an optional discount rate.

    ``discount=0.0`` means "no discount"; ``discount=None`` means "use the
    default discount".
    """
    if subtotal < 0:
        raise ValueError("subtotal must be non-negative")
    rate = discount if discount else DEFAULT_DISCOUNT
    return round(subtotal * (1 - rate), 2)
