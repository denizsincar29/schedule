"""MCP server exposing the schedule to AI agents (FastMCP, stdio).

Every tool returns the shared schema.json shape as a JSON string so results are
stable for the model. Networking rules mirror the CLI: only ruz.narfu.ru and
(under full names) narfu.ru/sveden/employees are ever contacted.

Run:  python3 -m schedule.mcp_server   (or via the py/mcp.json config)
"""
from __future__ import annotations

import json
from datetime import date

from mcp.server.fastmcp import FastMCP

from . import core, ruz
from .models import Week, to_json
from .resolver import load_index

mcp = FastMCP("narfu-schedule")


def _today() -> date:
    return date.today()


def _resolve(group: str | None, oid: str | None) -> tuple[str, str]:
    return core.resolve_target(group, oid)


def _fetch(oid: str):
    return ruz.parse_page(ruz.fetch_group(oid))


def _dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


@mcp.tool()
def schedule_day(group: str | None = None, oid: str | None = None,
                 date: str | None = None,
                 full_names: bool = False) -> str:
    """Расписание на один день. Укажи group («151318») или oid («20756»);
    date — «ГГГГ-ММ-ДД» (по умолчанию сегодня). Вернёт schema.json (Week),
    где days содержит запрошенный день (пустой lessons = пар нет)."""
    g, oid2 = _resolve(group, oid)
    d = date or str(_today())
    w: Week = core.make_week(g, oid2, _fetch(oid2), _today(), day=d,
                             full_names=full_names)
    return to_json(w)


@mcp.tool()
def schedule_week(group: str | None = None, oid: str | None = None,
                  date: str | None = None,
                  offset: int = 0,
                  full_names: bool = False) -> str:
    """Расписание на неделю (Пн–Сб). group/oid — как в schedule_day; date —
    любая дата недели «ГГГГ-ММ-ДД» (по умолчанию ближайший понедельник);
    offset — сдвиг в неделях. Вернёт schema.json (Week)."""
    g, oid2 = _resolve(group, oid)
    w = core.make_week(g, oid2, _fetch(oid2), _today(), start=date,
                       offset=offset, full_names=full_names)
    return to_json(w)


@mcp.tool()
def find_group(name: str) -> str:
    """Найти группу по имени («151318») и вернуть её oid расписания."""
    oid, found = core.resolve_target(name, None)
    return _dump({"name": found, "oid": oid})


@mcp.tool()
def resolve_teacher(short: str) -> str:
    """Раскрыть короткое имя «Фамилия И.О.» в полное ФИО из официального
    списка преподавателей; null если неоднозначно/неизвестно."""
    full = load_index().get(short)
    return _dump({"teacher": short, "teacher_full": full})


if __name__ == "__main__":
    mcp.run()
