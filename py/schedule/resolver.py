"""Resolve timetable short names («Абрамова Л.В.») to full names from the
official САФУ staff list (narfu.ru/sveden/employees).

The staff page marks every teacher with microdata itemprop="fio". We fold each
full name to the short form the timetable uses and keep only unambiguous
matches — two teachers sharing the same initials (e.g. two Абрамовых) stay
unresolved rather than guessed.

The parsed index is cached in the platform user cache dir under
narfu_schedule/employees_index.json for 30 days — the same file the Go and Rust
implementations use. Failures never propagate: on any network/parse error we
return what we have ({}/stale cache) so the caller keeps the short names.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

from .models import Day
from .ruz import _un, http_get

EMPLOYEES_URL = "https://narfu.ru/sveden/employees/"
_TTL = 30 * 86400  # the staff page changes rarely; refetch after 30 days
_DIR_NAME = "narfu_schedule"
_FILE_NAME = "employees_index.json"


def cache_path() -> str:
    """narfu_schedule/employees_index.json under the platform user cache dir."""
    base = os.environ.get("XDG_CACHE_HOME")
    if not base:
        home = os.path.expanduser("~")
        if os.name == "nt":
            base = os.environ.get("LOCALAPPDATA",
                                  os.path.join(home, "AppData", "Local"))
        elif sys.platform == "darwin":
            base = os.path.join(home, "Library", "Caches")
        else:
            base = os.path.join(home, ".cache")
    return os.path.join(base, _DIR_NAME, _FILE_NAME)


def short_of(full: str) -> str:
    """«Абрамова Любовь Валерьевна» -> «Абрамова Л.В.»"""
    parts = full.split()
    return parts[0] + " " + "".join(p[0] + "." for p in parts[1:])


def build_index(h: str) -> dict:
    """Parse the staff page HTML into {short: full} (unambiguous only)."""
    seen: dict[str, list[str]] = {}
    for m in re.finditer(r'itemprop="fio">(.*?)</td>', h, re.S):
        full = _un(m.group(1))
        parts = full.split()
        if len(parts) < 2:
            continue
        seen.setdefault(short_of(full), []).append(full)
    return {s: f[0] for s, f in seen.items() if len(f) == 1}


def load_index() -> dict:
    """Return the short→full map, fetching/refreshing the cache when needed."""
    path = cache_path()
    idx: dict | None = None
    if os.path.exists(path):
        try:
            if time.time() - os.path.getmtime(path) < _TTL:
                return json.load(open(path, encoding="utf-8"))
            idx = json.load(open(path, encoding="utf-8"))  # stale fallback
        except Exception:
            idx = None
    try:
        h = http_get(EMPLOYEES_URL, timeout=45)
    except Exception:
        return idx if idx is not None else {}
    out = build_index(h)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=1)
    except Exception:
        pass
    return out


def apply_full_names(days: list[Day], index: dict) -> None:
    """Annotate each lesson's teacher_full in place when it resolves."""
    if not index:
        return
    for day in days:
        for lesson in day.lessons:
            full = index.get(lesson.teacher, "")
            if full:
                lesson.teacher_full = full
