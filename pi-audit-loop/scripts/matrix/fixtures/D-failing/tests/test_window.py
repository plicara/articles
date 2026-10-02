import unittest

from src.window import last_n


class TestLastN(unittest.TestCase):
    def test_returns_tail(self):
        self.assertEqual(last_n([1, 2, 3, 4], 2), [3, 4])

    def test_zero_returns_empty(self):
        self.assertEqual(last_n([1, 2, 3, 4], 0), [])

    def test_more_than_length(self):
        self.assertEqual(last_n([1, 2], 5), [1, 2])

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            last_n([1, 2], -1)


if __name__ == "__main__":
    unittest.main()
