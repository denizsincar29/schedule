"""Date helpers shared by the CLI and the MCP server.

The timetable works in whole weeks Mon–Sat; all dates are handled as ISO
strings (YYYY-MM-DD) at the model boundary and as datetime.date inside.
"""
from __future__ import annotations

from datetime import date, timedelta

WKDAY_RU = ["понедельник", "вторник", "среда", "четверг", "пятница",
            "суббота", "воскресенье"]
MONTHS_RU = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
             "августа", "сентября", "октября", "ноября", "декабря"]


def weekday_ru(d: date) -> str:
    return WKDAY_RU[d.weekday()]


def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def next_monday(d: date) -> date:
    m = monday_of(d)
    return m if d.weekday() == 0 else m + timedelta(days=7)


def ru_date(d: date) -> str:
    """«7 сентября» (used in human text output)."""
    return f"{d.day} {MONTHS_RU[d.month - 1]}"
