"""Command-line entry point — the shared CLI contract (spec/cli.md).

Output: plain screen-reader-friendly Russian by default, or schema.json with
--json. Exit 0 even for an empty window; non-zero on network/group failure.
Window logic lives in core.py (shared with the MCP server).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, timedelta

from . import core, ruz
from .dates import ru_date, weekday_ru
from .models import Lesson, Week, to_dict


def _args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        prog="schedule",
        description="Читает расписание группы САФУ с ruz.narfu.ru "
                    "(без логина). Текст по умолчанию, --json по schema.json.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--group", help="имя группы как на сайте, напр. 151318")
    g.add_argument("--oid", help="oid расписания (без поиска группы)")
    w = ap.add_mutually_exclusive_group()
    w.add_argument("--today", action="store_true", help="только на сегодня")
    w.add_argument("--tomorrow", action="store_true", help="только на завтра")
    w.add_argument("--week", action="store_true",
                   help="вся неделя Пн–Сб (по умолчанию)")
    ap.add_argument("--start", metavar="YYYY-MM-DD",
                    help="неделя, содержащая эту дату (с --week)")
    ap.add_argument("--offset", type=int, default=0,
                    help="сдвиг недели на N недель (с --week)")
    ap.add_argument("--full-names", action="store_true",
                    help="полные ФИО преподавателей из официального списка")
    ap.add_argument("--json", action="store_true",
                    help="вывод в формате schema.json")
    return ap.parse_args(argv)


def _loc(L: Lesson) -> str:
    addr = L.addr.lstrip(" ,")
    loc = L.room.rstrip()
    if addr:
        loc = f"{loc}, {addr}" if loc else addr
    return loc


def _line(L: Lesson) -> str:
    s = f"{L.time_start}–{L.time_end} — {L.kind}. {L.subject}"
    t = L.teacher_full or L.teacher
    if t:
        s += f", {t}"
    s += f". {_loc(L)}"
    return re.sub(r"([.!?])\1+", r"\1", s)


def _print_day(target: date, w: Week) -> None:
    day = w.days[0] if w.days else None
    if not day or not day.lessons:
        print(f"{weekday_ru(target)}, {ru_date(target)}: пар нет")
        return
    print(f"{day.weekday}, {ru_date(target)}:")
    for L in day.lessons:
        print("  " + _line(L))


def _print_week(w: Week) -> None:
    start = date.fromisoformat(w.week_start)
    end = start + timedelta(days=5)
    print(f"Неделя с {ru_date(start)} по {ru_date(end)}:")
    has = [d for d in w.days if d.lessons]
    if not has:
        print("  на эту неделю занятий не выложено")
        return
    for d in has:
        print(f"\n{d.weekday}, {ru_date(date.fromisoformat(d.date))}:")
        for L in d.lessons:
            print("  " + _line(L))


def run(a: argparse.Namespace, today: date | None = None) -> int:
    today = today or date.today()
    oid, group_name = core.resolve_target(a.group, a.oid)
    days = ruz.parse_page(ruz.fetch_group(oid))
    single = bool(a.today or a.tomorrow)
    target = (today if a.today else today + timedelta(days=1)) if single else None
    if single:
        w = core.make_week(group_name, oid, days, today, day=str(target),
                           full_names=a.full_names)
    else:
        w = core.make_week(group_name, oid, days, today, start=a.start,
                           offset=a.offset, full_names=a.full_names)
    if a.json:
        print(json.dumps(to_dict(w), ensure_ascii=False, indent=2))
        return 0
    if single:
        _print_day(target, w)
    else:
        _print_week(w)
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return run(_args(argv))
    except Exception as e:
        print(f"ошибка: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
