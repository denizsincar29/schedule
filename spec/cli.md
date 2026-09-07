# CLI contract — shared by `py/`, `go/` and `rust/`

Every implementation exposes the **same command-line interface** and prints the
**same `--json` output** (key order and content as in [schema.json](schema.json))
for the same request. Text output is a human-readable Russian summary and may
differ slightly in wording between languages — JSON is the parity target.

## Usage

```
schedule --group <group-name> | --oid <oid>
         [--today | --tomorrow | --week]
         [--start YYYY-MM-DD] [--offset N]
         [--full-names] [--json]
```

- `--group <name>` — human group name as shown on ruz.narfu.ru (e.g. `151318`).
  The program auto-finds the timetable oid by scanning the institute group pages.
  Mutually exclusive with `--oid`; one of the two is required.
- `--oid <oid>` — known timetable oid (e.g. `20756`); skips the group scan.
- Window selector, mutually exclusive, default `--week`:
  - `--today` — the requested group's classes for the current local day.
  - `--tomorrow` — classes for the next day.
  - `--week` — a full Mon–Sat window (see below).
- `--start YYYY-MM-DD` — with `--week`: pin the window to the week containing
  this date (normalized to its Monday). If the date is itself a Monday it is
  used as-is.
- `--offset N` — with `--week`: shift the window by N whole weeks (N default 0;
  negative goes back). Mutually exclusive with `--start`.
- `--full-names` — resolve each lesson's short teacher form («Абрамова Л.В.»)
  to the full name («Абрамова Любовь Валерьевна») via the official staff list.
- `--json` — emit `schema.json` instead of human text.

Exit code `0` on success (including an empty window); non-zero on network /
group-resolution failure, with a short Russian message on stderr.

## Window semantics

- **`--week`**: the default window is the nearest full Mon–Sat week that starts
  on the next Monday (or today, when today is Monday). `--offset N` shifts that
  whole window; `--start` replaces the anchor. Either way `week_start` in the
  JSON is always a Monday.
- **`--today` / `--tomorrow`**: the returned window is that single day;
  `week_start` is the Monday of that day's week.
- **The site only publishes classes that exist.** Empty day columns are present
  with `lessons: []` when the day is inside the published range but has no
  classes; days outside the published range are simply absent from `days`.
  A week with no published days yields `days: []` — the implementations say the
  schedule for that week is not out yet; they never invent classes.

## JSON output

Top-level object per [schema.json](schema.json):

```json
{
  "group": "151318",
  "oid": "20756",
  "week_start": "2026-09-07",
  "days": [
    {
      "date": "2026-09-07",
      "weekday": "понедельник",
      "lessons": [
        {
          "num": "1",
          "time_start": "08:20",
          "time_end": "09:55",
          "kind": "Лекция",
          "subject": "Прикладные задачи машинного и глубокого обучения (модуль)",
          "teacher": "Абрамова Л.В.",
          "teacher_full": "Абрамова Любовь Валерьевна",
          "room": "ауд. 44",
          "addr": "наб. Северной Двины, д. 2"
        }
      ]
    }
  ]
}
```

Field notes (see schema for full descriptions):

- `group` is the name passed with `--group`; it is `""` when only `--oid` was
  given.
- `teacher` is exactly what the timetable prints (initials). `teacher_full` is
  `null` unless `--full-names` resolved it **unambiguously** — two teachers
  sharing the same initials (e.g. two Абрамовых) are left unresolved rather
  than guessed.
- `time_start`/`time_end` split the timetable's single «08:20–09:55» string
  into 24h `HH:MM`.
- Lessons in a day are sorted by `num` numerically.

## Text output

Russian, screen-reader friendly. Structure (may differ slightly per language):

```
Неделя с 7 сентября по 12 сентября:          # --week; or for --today:
понедельник, 7 сентября:                     #   <weekday>, <d> <month>:
  08:20–09:55 — Лекция. Прикладные задачи машинного и глубокого обучения (модуль), Абрамова Любовь Валерьевна. ауд. 44, наб. Северной Двины, д. 2
```

- Each lesson line: `time — kind. subject[, full/short teacher]. room, addr`.
- With `--full-names` the full name is printed; otherwise the short form.
- Days without classes are skipped in `--week` text output; a whole empty week
  prints one line: «на эту неделю занятий не выложено». An empty requested day
  prints «<weekday>, <d> <month>: пар нет».

## Staff list and cache

Full names come from the official staff page `https://narfu.ru/sveden/employees/`
(microdata `itemprop="fio"`, ~850 entries). Each implementation:

- fetches it lazily and caches the parsed `short → full` map locally for 30 days
  in the platform user cache dir under `narfu_schedule/employees_index.json`
  (Linux `$XDG_CACHE_HOME`/`~/.cache`, Windows `%LOCALAPPDATA%`, macOS
  `~/Library/Caches`) — all three languages share one cache file;
- resolves **only unambiguous** short→full matches;
- on any network/cache failure **degrades silently** to the timetable's own
  short names (never crashes, never guesses initials).

## Examples

```
schedule --group 151318                     # nearest full week
schedule --oid 20756 --today                # today only (fast, no group scan)
schedule --oid 20756 --today --full-names   # ... with full teacher names
schedule --group 151318 --week --offset 1   # the week after next
schedule --oid 20756 --week --start 2026-09-14
schedule --group 151318 --json              # machine-readable (schema.json)
```
