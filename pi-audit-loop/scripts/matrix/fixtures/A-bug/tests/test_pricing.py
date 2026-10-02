import unittest

from src.pricing import DEFAULT_DISCOUNT, order_total


class TestOrderTotal(unittest.TestCase):
    def test_missing_discount_uses_default(self):
        self.assertEqual(
            order_total(100.0),
            round(100.0 * (1 - DEFAULT_DISCOUNT), 2),
        )

    def test_explicit_discount(self):
        self.assertEqual(order_total(100.0, 0.25), 75.0)

    def test_negative_subtotal_rejected(self):
        with self.assertRaises(ValueError):
            order_total(-1.0)


if __name__ == "__main__":
    unittest.main()
