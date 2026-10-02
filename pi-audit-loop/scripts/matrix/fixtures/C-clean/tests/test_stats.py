import unittest

from src.stats import mean, median, spread


class TestMean(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(mean([1, 2, 3]), 2.0)

    def test_empty_is_zero(self):
        self.assertEqual(mean([]), 0.0)


class TestMedian(unittest.TestCase):
    def test_odd(self):
        self.assertEqual(median([3, 1, 2]), 2)

    def test_even(self):
        self.assertEqual(median([4, 1, 3, 2]), 2.5)

    def test_empty_is_zero(self):
        self.assertEqual(median([]), 0.0)


class TestSpread(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(spread([5, 1, 9]), 8)

    def test_empty_is_zero(self):
        self.assertEqual(spread([]), 0.0)


if __name__ == "__main__":
    unittest.main()
