"""Parser tests against the frozen spec/fixtures snapshots (no network)."""
import re
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from schedule.ruz import parse_page  # noqa: E402

FIX = Path(__file__).resolve().parents[2] / "spec" / "fixtures"
TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class TestOneDay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        html = (FIX / "ruz_one_day.html").read_text(encoding="utf-8")
        cls.days = parse_page(html)

    def test_one_day(self):
        self.assertEqual(len(self.days), 1)
        day = self.days[0]
        self.assertEqual(day.date, "2026-09-07")
        self.assertEqual(day.weekday, "понедельник")

    def test_two_lessons_sorted(self):
        self.assertEqual([l.num for l in self.days[0].lessons], ["1", "2"])

    def test_lesson_fields(self):
        l = self.days[0].lessons[0]
        self.assertEqual(l.time_start, "08:20")
        self.assertEqual(l.time_end, "09:55")
        self.assertEqual(l.kind, "Лекция")
        self.assertEqual(l.teacher, "Абрамова Л.В.")
        self.assertIsNone(l.teacher_full)
        self.assertEqual(l.room, "ауд. 44")
        self.assertEqual(l.addr, "наб. Северной Двины, д. 2")
        self.assertIn("машинного и глубокого обучения", l.subject)

    def test_times_are_clean(self):
        for l in self.days[0].lessons:
            self.assertRegex(l.time_start, TIME)
            self.assertRegex(l.time_end, TIME)


class TestEmptyDay(unittest.TestCase):
    def test_empty_day_column(self):
        html = (FIX / "ruz_empty_day.html").read_text(encoding="utf-8")
        days = parse_page(html)
        self.assertEqual(len(days), 1)
        self.assertEqual(days[0].date, "2026-09-08")
        self.assertEqual(days[0].lessons, [])


class TestWeekSnapshot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        html = (FIX / "ruz_20756_week.html").read_text(encoding="utf-8")
        cls.days = parse_page(html)

    def test_snapshot_size_and_order(self):
        self.assertEqual(len(self.days), 36)
        dates = [date.fromisoformat(d.date) for d in self.days]
        self.assertEqual(dates, sorted(dates))

    def test_no_empty_times(self):
        for d in self.days:
            for l in d.lessons:
                self.assertTrue(l.time_start)
                self.assertTrue(l.time_end)
                self.assertTrue(l.kind)
                self.assertTrue(l.subject)


if __name__ == "__main__":
    unittest.main()
