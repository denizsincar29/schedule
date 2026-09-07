# NArFU schedule — Python / Go / Rust

Read САФУ class schedules from the public RUZ timetable
(`ruz.narfu.ru`) — **no login, no API, no keys**. One spec, three
implementations:

- `py/` — Python (the reference implementation) with an **MCP server** so AI
  agents can query schedules directly;
- `go/` — Go CLI;
- `rust/` — Rust CLI.

The timetable lists teachers as short initials («Абрамова Л.В.»); a resolver
expands them to full names («Абрамова Любовь Валерьевна») using the official
staff list at `narfu.ru/sveden/employees/`, cached locally for 30 days. Only
unambiguous short→full matches are applied.

**Status: under construction** (the multi-language rewrite started 2026-09-07).
The shared contract lives in [`spec/`](spec/); phases progress through the three
implementations. The previous generation — *schedule 2.0*, a Python console +
MCP app that read `modeus.org` with a login — is preserved (as a working
historical reference) in [`old/`](old/).

## Layout

```
spec/      shared JSON schema, CLI contract, HTML fixtures  (single source of truth)
py/        Python: stdlib CLI + FastMCP server
go/        Go CLI
rust/      Rust CLI
old/       the legacy modeus.org app (kept for reference)
```

## Data source

`ruz.narfu.ru` is RUZ (Gavrikov), САФУ's public timetable. There is no API —
each implementation reads the same HTML a browser would:

`https://ruz.narfu.ru/?timetable&group=<oid>`

A human group name («151318») is **not** the timetable `oid`; the CLI finds the
oid by scanning the institute group pages, or takes `--oid` directly. The site
publishes ~6 weeks ahead, Mon–Sat, and only lessons that actually exist —
empty days/weeks are simply absent (never invent classes). All three programs
share one CLI contract and emit byte-identical `--json` for the same request.

## License

Use it as you like; keep a mention of the author (Deniz Sincar). The authors of
the site are not responsible if you flood their servers — use the programs
wisely.
