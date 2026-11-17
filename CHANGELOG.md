# Changelog

## 0.1.0-rc.1 — 2026-11-17

Initial standalone release candidate, prepared locally. Publication is a separate action.

- Project-local Python 3.11+ standard-library helper with SQLite state.
- One canonical skill tree and installation adapters for Codex and Claude Code.
- Compact continuation context, attributed progress records, manual updates, and history.
- Revision checks, idempotent report handling, and preservation of manual state.
- Conservative install/uninstall behavior and an explicit public-export file list.
- Chinese and English getting-started guides, GitHub clone/ZIP instructions, and an offline synthetic demo.
- Dependency-free package checker and 31 local tests passing on Python 3.12.13 and 3.13.14.
- Pinned public-only GitHub Actions workflow for Python 3.11–3.13 on Ubuntu 24.04; remote results pending initial push.

### Acceptance still pending

- Real fresh-agent continuation canaries for Codex and Claude Code: **NOT RUN**.
- Linux validation: **NOT TESTED**. Windows: **UNSUPPORTED** because the installer uses `fcntl`.
- Token savings or agent performance improvement: **NOT MEASURED**.

The demo illustrates the local workflow only. It does not establish live skill discovery, agent compliance, or cross-session effectiveness. See [verification](docs/VERIFICATION.md) for local test evidence and the [canary procedure](docs/CANARY.md) for pending live acceptance.
