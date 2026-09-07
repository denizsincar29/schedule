"""Shared orchestration used by both the CLI and the MCP server.

Keeps the window-selection semantics (spec/cli.md) in exactly one place so a
CLI query and an MCP query for the same day/week can never disagree.
"""
from __future__ import annotations

from datetime import date, timedelta

from . import ruz
from .dates import monday_of, next_monday
from .models import Day, Week
from .resolver import apply_full_names, load_index


def resolve_target(group: str | None, oid: str | None) -> tuple[str, str]:
    """(oid, group-name-as-printed) from --oid or --group (auto-find)."""
    if oid:
        return oid, (group or "")
    found_oid, name = ruz.find_oid(group)
    return found_oid, name


def window(days: list[Day], today: date, *,
           day: str | None = None,
           start: str | None = None,
           offset: int = 0) -> tuple[date, list[Day]]:
    """(week_start, days in window). `day` wins over `start`/`offset`."""
    if day is not None:
        d = date.fromisoformat(day)
        picked = [x for x in days if x.date == day]
        return monday_of(d), picked
    begin = date.fromisoformat(start) if start else next_monday(today)
    begin = monday_of(begin) + timedelta(weeks=offset)
    end = begin + timedelta(days=7)
    picked = [x for x in days
              if begin <= date.fromisoformat(x.date) < end]
    picked.sort(key=lambda x: x.date)
    return begin, picked


def make_week(group: str, oid: str, days: list[Day], today: date, *,
              day: str | None = None,
              start: str | None = None,
              offset: int = 0,
              full_names: bool = False) -> Week:
    """Fetch-free builder: given parsed days, return the requested window.

    When full_names is set the short→full pass runs against the cached/fetched
    staff index (may hit the network once per 30 days).
    """
    if full_names:
        apply_full_names(days, load_index())
    begin, picked = window(days, today, day=day, start=start, offset=offset)
    return Week(group=group, oid=oid, week_start=str(begin), days=picked)
