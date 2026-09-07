"""Data model per spec/schema.json.

Field order on the dataclasses matches the property order in schema.json and
the key order of every implementation's --json output, so the three languages
serialize byte-identically.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass


@dataclass
class Lesson:
    num: str
    time_start: str
    time_end: str
    kind: str
    subject: str
    teacher: str
    teacher_full: str | None
    room: str
    addr: str


@dataclass
class Day:
    date: str
    weekday: str
    lessons: list[Lesson]


@dataclass
class Week:
    group: str
    oid: str
    week_start: str
    days: list[Day]


def to_dict(w: Week) -> dict:
    return asdict(w)


def to_json(w: Week) -> str:
    return json.dumps(asdict(w), ensure_ascii=False, indent=2)
