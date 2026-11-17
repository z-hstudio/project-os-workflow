# Workflow report v1 / 工作记录格式

Run the helper with `--project <root>` before the subcommand. It accepts one
explicit root, never guesses a project or reads another agent's chat database.

## Commands

```sh
python3 <skill-dir>/scripts/project_os.py --project . init --name 'Tiny Notes' --purpose 'Save small notes' --language zh
python3 <skill-dir>/scripts/project_os.py --project . context
python3 <skill-dir>/scripts/project_os.py --project . record --input .project-os/report.json
python3 <skill-dir>/scripts/project_os.py --project . manual --input .project-os/manual.json
python3 <skill-dir>/scripts/project_os.py --project . history --limit 10
```

`init` returns existing state unchanged when already initialized. `context` is a
read-only JSON view; default total output budget including newline is 12 KiB UTF-8,
configurable by `--max-bytes` from 512 to 65536. All current fields and constraints
must fit, or it fails explicitly. Up to three recent summaries fit in the remaining
space; `omitted_records` counts records not shown. `history` returns newest first,
at most 50 entries / 256 KiB per page. Continue using `--before <next_before>`.

## Record input

Use the actual ID/revision from `context`; the example's placeholder is not a valid
project binding. Create a unique key per logical save and keep it on exact retries.

```json
{
  "schema_version": 1,
  "project_id": "COPY_FROM_CONTEXT",
  "expected_revision": 0,
  "idempotency_key": "tiny-notes-step-1",
  "agent": "codex",
  "summary": "Added note normalization; local unit tests passed.",
  "changes": {
    "phase": "Core behavior",
    "status": "active",
    "summary": "Whitespace normalization is implemented.",
    "next_action": "Test empty input.",
    "why": "Empty notes should not be accepted."
  },
  "evidence": [
    {"kind": "test", "reference": "python3 -m unittest", "outcome": "passed"}
  ]
}
```

Required fields are those above except `evidence`; optional fields are `session_id`
(opaque runtime ID), `occurred_on` (real YYYY-MM-DD date or null), and `evidence`.
Unknown fields and duplicate JSON keys are rejected. Maximum input is 64 KiB.
`agent` is a lowercase identifier such as `codex` or `claude-code`; `user` is
reserved for manual input. No native Codex UUID or account is needed.

`changes` is a partial update, and may be empty for a history-only checkpoint:

| Field | Value | Who may change it |
|---|---|---|
| `name`, `purpose` | Text | Explicit user edit |
| `constraints` | Up to 20 strings | Explicit user edit |
| `phase`, `summary`, `next_action`, `why` | Text | Agent unless manually protected |
| `issues`, `decisions` | Up to 20 strings; whole list replaces current list | Agent unless protected |
| `status` | `unknown`, `active`, `waiting`, `blocked` | Agent unless protected |
| `status` | Also `paused`, `complete`, `abandoned` | Explicit user edit only |
| `last_progress_on` | YYYY-MM-DD or null | Agent unless protected; never inferred from save time |

Individual text fields allow 8 KiB UTF-8, names 480 bytes, list entries 4 KiB.
Current state including attribution and its required context envelope is limited
to 64 KiB. Keep narratives much
shorter for useful context. Optional evidence has exactly `kind`, `reference`,
`outcome`; kind is `test/file/commit/note`, outcome is
`passed/failed/not_run/observed/unknown`. At most 20 references, each at most 2 KiB.
The helper does not run a command, open a referenced file, or verify test success.
All agent evidence remains `agent_report_unverified`; a commit changing auth files
cannot establish that authentication is complete.

## Manual edits and conflicts

An explicit user edit uses the same envelope, `agent: "user"`, and the `manual`
command. It locks every supplied field against later automatic changes, including
intentional empty values. `manual` is a workflow convention, not authentication:
any process with filesystem access can edit the database. Do not represent it as
a sandbox or tamper-proof security boundary. There is no automatic unlock in v1.

When an agent proposes a different manually protected phase, all phase-related
updates (status, summary, issues, next action, reason, progress date) stay separate
from current state. Other protected fields retain their values individually.
Use history to review proposals and make a new explicit manual edit if desired.

`expected_revision` is checked inside the same SQLite transaction as the write.
A stale report is retained in immutable history without changing current state.
An identical key/payload replays its original receipt; changing the payload under
that key fails. Do not change the baseline merely to force an old proposal through.

The receipt's `outcome`, `revision_before/after`, `applied_fields`,
`protected_fields` and `evidence_status` distinguish history saved from state
changed and work verified. Receipt dates are save dates, not activity dates.

## Storage and failure

`.project-os/state.sqlite3` is a separate project-local store, schema version 1.
It is not the desktop application's database and has no migration/import coupling.
State and immutable record snapshots commit atomically. Read commands may let
SQLite recover an interrupted transaction's hot journal before enabling query-only
access; they do not update project fields or history. A 5-second lock timeout
returns an error. A newer schema is rejected without reset. An initialization
interrupted before atomic publication may leave an ignored `.init-*.sqlite3`
temporary file; retry does not overwrite it or an existing published database.

Runtime files are ignored by `.project-os/.gitignore`; no raw transcript ingestion,
network, telemetry, shell execution or model calls occur in this helper. The
calling Agent may send the context to its configured model as part of its normal
operation. Do not save secrets here; this is not encryption or secret scanning.

Successful saves (including protected/stale/history-only) exit 0; invalid input
and domain errors exit 2; storage failures exit 3. Errors go to stderr as JSON.
Input files are never deleted; check the same key's receipt before retrying an
uncertain write. Do not claim fresh-agent compatibility from these CLI results alone.
