# Verification — 0.1.0-rc.1

Date: **2026-11-17**. Overall acceptance: **PARTIAL**, pending authorized fresh
Codex/Claude sessions and an actual matched usage comparison. Repository
publication and offline CI are tracked separately below and in [RELEASE.md](RELEASE.md).

## Executed locally

| Check | Result |
|---|---|
| `python3 -I -m unittest discover -s tests -v` on macOS | **31 tests passed on Python 3.12.13; 31 passed on Python 3.13.14** |
| Core persistence and context | 14 tests: revision conflicts, idempotency, protected fields/phase, wrong project/version, actual killed-writer recovery, transaction rollback, immutable records, context capacity and invalid input |
| Installation ownership | 6 tests: two identical adapters, repeat install, existing files, symlinks, edited/unowned preservation, tampered ownership paths, rollback and a racing user file |
| Public packaging and demo | 5 tests: allowlist, private runtime exclusion, traversal/symlinks/credential marker, existing destination, offline demo and canary preparation |
| Usage comparator | 3 tests: calculation over synthetic numbers, unmatched case rejection, invalid/estimated/failed result rejection |
| Package verification | 3 tests: valid package, broken relative link, incomplete metadata/stale checksums; no third-party parser required |
| `python3 scripts/check_package.py` | Passed: flat Skill metadata, relative links, Python 3.11 syntax, export allowlist and existing checksums |
| Offline Tiny Notes demo | Both installed helper paths used; revisions 0 → 1 → 2, latest next action read by a fresh process; local behavior assertions passed |
| Canary preparation | Four prompt files prepared; **zero Agent sessions launched**; initial failing test intentionally left for live session A |
| Demonstration media | Six locally rendered frames from sanitized helper results; 18-second GIF; no cloud image/video generation |

The test groups contain multiple assertions per test; the row counts above refer
to test methods, not claims of complete platform coverage. Tests run only against
temporary synthetic projects. The desktop application's previous tests are not
evidence for this package.

The demo's final compact context was **1,461 UTF-8 bytes**, including its newline,
under the default 12 KiB budget. This is one small fixture's size, not a token
measurement or expected saving. Runtime/model token usage remains **NOT MEASURED**.

## Review corrections

One independent local review reproduced two problems: rollback could remove a
concurrently created unowned file; a nearly-full accepted state could exceed the
largest context envelope. Each received one targeted fix and regression test.
An additional actual-process interruption test exposed SQLite hot-journal recovery
under a read-only connection; opening the existing store for recovery and then
enabling query-only access resolved it in one targeted fix. No review loop followed.

## Not established

- Fresh Codex and Claude Code Skill discovery, compliance and cross-agent handoff:
  **NOT RUN**. Installed CLI version checks found Codex `0.167.0-alpha.3.2` and
  Claude Code `2.1.185`; version checks are not canaries.
- Token improvement or cost savings: **NOT MEASURED**. The comparator's unit tests
  use synthetic numbers, not product performance data.
- Python 3.11 and Linux: awaiting the new public CI run. Windows is unsupported
  by the installer.
- The host's generic Skill validator previously lacked PyYAML. The package now
  includes its own tested standard-library checker for this Skill's deliberately
  flat metadata format. This is not a general YAML validator or live Agent test.
- External-model review: **NOT PERFORMED**. One local release-readiness review
  also verified the clean export and first-user path using Python 3.12.13.

## Public CI

The workflow runs the same offline suite and package checks on standard public
GitHub-hosted Ubuntu 24.04 runners, with Python 3.11, 3.12 and 3.13. It skips private
repositories, grants only repository-read permissions, and uses no model API,
secrets, cache or uploaded artifacts. The first run is pending publication;
successful remote evidence will be linked here after readback.

Use [CANARY.md](CANARY.md) for the outstanding live acceptance and matched
measurement procedure. Preserve failures and unknown measurements rather than
promoting this candidate to a fully verified release.
