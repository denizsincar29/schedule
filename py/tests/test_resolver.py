"""Resolver tests against the employees fixture (no network).

The fixture deliberately holds two Абрамовых with different initials so we can
assert the ambiguity rule: only unambiguous short→full mappings survive.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from schedule.resolver import apply_full_names, build_index, short_of  # noqa: E402
from schedule.ruz import parse_page  # noqa: E402

FIX = Path(__file__).resolve().parents[2] / "spec" / "fixtures"


class TestShortOf(unittest.TestCase):
    def test_full_to_short(self):
        self.assertEqual(short_of("Абрамова Любовь Валерьевна"), "Абрамова Л.В.")

    def test_two_initialed(self):
        self.assertEqual(short_of("Деменков Максим Евгеньевич"), "Деменков М.Е.")


class TestBuildIndex(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        html = (FIX / "employees_frag.html").read_text(encoding="utf-8")
        cls.idx = build_index(html)

    def test_resolves_all_fixture_teachers(self):
        self.assertEqual(self.idx["Абрамова Л.В."], "Абрамова Любовь Валерьевна")
        self.assertEqual(self.idx["Абрамова М.А."], "Абрамова Марина Алексеевна")
        self.assertEqual(self.idx["Деменков М.Е."], "Деменков Максим Евгеньевич")
        self.assertEqual(self.idx["Деменкова Е.А."],
                         "Деменкова Екатерина Алексеевна")
        self.assertEqual(self.idx["Шурыкина Л.С."], "Шурыкина Людмила Сергеевна")

    def test_both_abramovas_survive(self):
        # different initials -> each maps to exactly one full name
        self.assertIn("Абрамова Л.В.", self.idx)
        self.assertIn("Абрамова М.А.", self.idx)


class TestApplyFullNames(unittest.TestCase):
    def test_annotates_in_place(self):
        html = (FIX / "ruz_one_day.html").read_text(encoding="utf-8")
        days = parse_page(html)
        idx = {"Абрамова Л.В.": "Абрамова Любовь Валерьевна"}
        apply_full_names(days, idx)
        self.assertEqual(days[0].lessons[0].teacher_full,
                         "Абрамова Любовь Валерьевна")

    def test_unresolved_stays_none(self):
        days = parse_page((FIX / "ruz_one_day.html").read_text(encoding="utf-8"))
        apply_full_names(days, {"Кто-то И.К.": "Кто-то Имя Кто-тович"})
        self.assertIsNone(days[0].lessons[0].teacher_full)


if __name__ == "__main__":
    unittest.main()
