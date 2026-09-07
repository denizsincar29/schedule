# schedule — Go

Go version of the shared NArFU RUZ schedule spec. **Stdlib only** — no
external modules, builds and runs offline.

## CLI

Build once, then run from anywhere:

```bash
go build ./cmd/schedule            # produces ./schedule
./schedule --oid 20756 --today     # today's classes, text
./schedule --oid 20756 --today --full-names
./schedule --group 151318 --week   # nearest Mon–Sat week
./schedule --oid 20756 --week --start 2026-09-14
./schedule --group 151318 --json   # schema.json output
```

Or run without building:

```bash
go run ./cmd/schedule --oid 20756 --today
```

Flags and output follow [spec/cli.md](../spec/cli.md); `--json` matches
[spec/schema.json](../spec/schema.json) byte-for-byte against the Python
reference (verified on live data: `--week`, `--today`, `--week --full-names`,
`--group` auto-find all produce identical output).

## Tests

```bash
go test ./...                      # parser / resolver / dates / core, no network
```

Tests parse the frozen `spec/fixtures` snapshots, mirroring the Python tests.

## Layout

- `internal/model` — structs per `spec/schema.json` (field order = JSON order).
- `internal/ruz` — HTTP fetch + HTML parsing (mirror of `py/schedule/ruz.py`).
- `internal/resolver` — teacher short→full resolution + shared 30-day cache.
- `internal/dates` — weekday/month helpers, week-boundary math.
- `internal/core` — window selection shared by the CLI (mirror of core.py).
- `cmd/schedule` — the CLI entry point.

## Cache

Full teacher names are cached (30 days) in the user cache dir under
`narfu_schedule/employees_index.json` — shared with the Python/Rust versions.
