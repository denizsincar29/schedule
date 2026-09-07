# schedule — Python (reference implementation)

Python version of the shared NArFU RUZ schedule spec. The CLI is **stdlib
only**; the MCP server needs the optional `mcp` extra.

## CLI

Run from this directory (no install needed):

```bash
python3 -m schedule --oid 20756 --today            # today's classes, text
python3 -m schedule --oid 20756 --today --full-names
python3 -m schedule --group 151318 --week          # nearest Mon–Sat week
python3 -m schedule --oid 20756 --week --start 2026-09-14
python3 -m schedule --group 151318 --json          # schema.json output
```

Or install and get a `schedule` command:

```bash
pip install -e .
schedule --oid 20756 --today
```

Flags and output follow [spec/cli.md](../spec/cli.md); JSON matches
[spec/schema.json](../spec/schema.json).

## Tests

```bash
python3 -m unittest discover -s tests   # parser / resolver / dates, no network
```

## MCP server (for AI agents)

```bash
pip install -e ".[mcp]"
python3 -m schedule.mcp_server           # stdio transport
```

Tools: `schedule_day(group|oid, date?, full_names?)`,
`schedule_week(group|oid, date?, offset?, full_names?)`, `find_group(name)`,
`resolve_teacher("Абрамова Л.В.")`. Results are JSON per the shared schema.

Editor config example in [`mcp.json`](mcp.json) (VS Code style); for Claude
Code add it with `claude mcp add narfu-schedule -- python3 -m schedule.mcp_server`
run from this directory.

## Cache

Full teacher names are cached (30 days) in the user cache dir under
`narfu_schedule/employees_index.json` — shared with the Go/Rust versions.
