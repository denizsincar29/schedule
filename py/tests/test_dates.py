"""Week-boundary and weekday tests for the date helpers."""
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from schedule.dates import (  # noqa: E402
    monday_of,
    next_monday,
    ru_date,
    weekday_ru,
)


class TestWeekHelpers(unittest.TestCase):
    def test_monday_of(self):
        self.assertEqual(monday_of(date(2026, 9, 7)), date(2026, 9, 7))  # Mon
        self.assertEqual(monday_of(date(2026, 9, 10)), date(2026, 9, 7))  # Thu
        self.assertEqual(monday_of(date(2026, 9, 13)), date(2026, 9, 7))  # Sun

    def test_next_monday(self):
        self.assertEqual(next_monday(date(2026, 9, 7)), date(2026, 9, 7))  # Mon
        self.assertEqual(next_monday(date(2026, 9, 10)), date(2026, 9, 14))  # Thu
        self.assertEqual(next_monday(date(2026, 9, 13)), date(2026, 9, 14))  # Sun

    def test_weekday_ru(self):
        self.assertEqual(weekday_ru(date(2026, 9, 7)), "понедельник")
        self.assertEqual(weekday_ru(date(2026, 9, 12)), "суббота")

    def test_ru_date(self):
        self.assertEqual(ru_date(date(2026, 9, 7)), "7 сентября")


if __name__ == "__main__":
    unittest.main()
