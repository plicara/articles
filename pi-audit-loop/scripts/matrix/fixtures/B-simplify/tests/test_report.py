import unittest
from datetime import date

from src.report import summarize_daily, summarize_monthly, summarize_quarterly

RECORDS = [
    (date(2024, 1, 1), 10.0),
    (date(2024, 1, 1), 5.0),
    (date(2024, 1, 2), 2.5),
    (date(2024, 2, 15), 7.5),
    (date(2024, 4, 1), 1.0),
]


class TestSummaries(unittest.TestCase):
    def test_daily(self):
        self.assertEqual(
            summarize_daily(RECORDS),
            [
                {"period": date(2024, 1, 1), "total": 15.0, "count": 2},
                {"period": date(2024, 1, 2), "total": 2.5, "count": 1},
                {"period": date(2024, 2, 15), "total": 7.5, "count": 1},
                {"period": date(2024, 4, 1), "total": 1.0, "count": 1},
            ],
        )

    def test_monthly(self):
        self.assertEqual(
            summarize_monthly(RECORDS),
            [
                {"period": (2024, 1), "total": 17.5, "count": 3},
                {"period": (2024, 2), "total": 7.5, "count": 1},
                {"period": (2024, 4), "total": 1.0, "count": 1},
            ],
        )

    def test_quarterly(self):
        self.assertEqual(
            summarize_quarterly(RECORDS),
            [
                {"period": (2024, 1), "total": 25.0, "count": 4},
                {"period": (2024, 2), "total": 1.0, "count": 1},
            ],
        )

    def test_empty(self):
        self.assertEqual(summarize_daily([]), [])
        self.assertEqual(summarize_monthly([]), [])
        self.assertEqual(summarize_quarterly([]), [])


if __name__ == "__main__":
    unittest.main()
