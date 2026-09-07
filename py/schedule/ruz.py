"""Fetch and parse the САФУ RUZ timetable HTML (ruz.narfu.ru).

No API exists — the script reads the same pages a browser would. The parsing
rules mirror the proven reference implementation (pipeline narfu_schedule):
day columns are <div class="dayofweek">, each lesson a nested
<div class="timetable_sheet ..."> (the non-_xs variant), the teacher sits in a
<nobr> inside the discipline span, the room/address in the auditorium span.
"""
from __future__ import annotations

import html
import re
import ssl
import urllib.request
from datetime import date

from .dates import weekday_ru
from .models import Day, Lesson

BASE = "https://ruz.narfu.ru/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126 Safari/537.36")


def _un(s: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", s)).strip()


def http_get(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": BASE})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read().decode("utf-8", "replace")


def find_oid(group: str) -> tuple[str, str]:
    """Human group name («151318») -> (timetable oid, name as found)."""
    home = http_get(BASE)
    insts = []
    for m in re.finditer(r'<a href="\?groups&institution=(\d+)"', home):
        if m.group(1) not in insts:
            insts.append(m.group(1))
    if not insts:
        insts = ["1", "3", "4", "6", "12", "13", "15", "23", "26", "28",
                 "33", "35", "36"]
    want = re.compile(r"(?i)(^|\s)" + re.escape(group.strip()) + r"($|\s)")
    for i in insts:
        page = http_get(BASE + "?groups&institution=" + i)
        for m in re.finditer(r'<a[^>]*href="\?timetable&group=(\d+)"[^>]*>(.*?)</a>',
                             page, re.S):
            oid, text = m.group(1), _un(re.sub(r"<[^>]+>", " ", m.group(2)))
            if want.search(text):
                return oid, text.split()[0]
    raise RuntimeError(f"группа «{group}» не найдена ни в одном институте")


def fetch_group(oid: str) -> str:
    return http_get(BASE + "?timetable&group=" + oid)


def _split_time(t: str) -> tuple[str, str]:
    parts = re.split(r"\s*[-–—]\s*", t)
    if len(parts) != 2:
        return t, ""
    return parts[0].strip(), parts[1].strip()


def _num(n: str) -> int:
    try:
        return int(n)
    except Exception:
        return 99


def parse_page(h: str) -> list[Day]:
    """Published day columns, chronological order (as they appear on the page).

    A column that exists but has no classes yields a Day with lessons=[].
    """
    h = re.sub(r"<!--.*?-->", "", h, flags=re.S)
    pat = re.compile(r'<div class="dayofweek[^"]*">(.*?)</div>', re.S)
    ms = list(pat.finditer(h))
    days: list[Day] = []
    for k, m in enumerate(ms):
        head = _un(m.group(1)).split(",")
        if len(head) != 2:
            continue
        wd, dt = head[0].strip(), head[1].strip()
        try:
            d = date(*reversed([int(x) for x in dt.split(".")]))
        except Exception:
            continue
        seg = h[m.end(): (ms[k + 1].start() if k + 1 < len(ms) else len(h))]
        lessons: list[Lesson] = []
        for lm in re.finditer(r'<div class="timetable_sheet(?!_xs)[^"]*">', seg):
            j, depth, closed = lm.end(), 1, None
            while j < len(seg) and depth > 0:
                nxt = re.compile(r"<div\b|</div>").search(seg, j)
                if not nxt:
                    break
                depth += 1 if seg[nxt.start():nxt.start() + 4] == "<div" else -1
                j = nxt.end()
                if depth == 0:
                    closed = j
                    break
            chunk = seg[lm.end():closed] if closed else ""

            def fld(cn: str) -> str:
                mm = re.search(r'<span class="%s">(.*?)</span>' % cn, chunk,
                               re.S)
                return _un(mm.group(1)) if mm else ""

            num = fld("num_para")
            tm = fld("time_para")
            kind = fld("kindOfWork")
            disp = fld("discipline")
            nm = re.search(r"<nobr>(.*?)</nobr>", disp, re.S)
            teacher = _un(nm.group(1)) if nm else ""
            subject = _un(re.sub(r"\s*\(<nobr>.*?</nobr>\)\s*$", "", disp,
                                 flags=re.S))
            aud = fld("auditorium")
            bm = re.search(r"<b>(.*?)</b>(.*)$", aud, re.S)
            room = _un(bm.group(1)) if bm else ""
            # the site keeps a leading comma before the street part («ауд. 44»,
            # «наб. Северной Двины…») — drop it for a clean addr field
            addr = (_un(re.sub(r"<[^>]+>", "", bm.group(2))).lstrip(" ,")
                    if bm else "")
            if tm:
                start, end = _split_time(tm)
                lessons.append(Lesson(num=num, time_start=start,
                                      time_end=end, kind=kind,
                                      subject=subject, teacher=teacher,
                                      teacher_full=None, room=room, addr=addr))
        lessons.sort(key=lambda x: _num(x.num))
        days.append(Day(date=str(d), weekday=weekday_ru(d), lessons=lessons))
    return days
