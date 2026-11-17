# Compatibility and acceptance

Applies to **0.1.0-rc.1**, dated **2026-11-17**.

## Runtime and installation

| Component | Requirement / status |
| --- | --- |
| Python | Code requires 3.11 or later, including the standard-library `sqlite3` module. Executed tests currently use 3.13.14; the minimum version is not a tested-version claim. |
| Additional Python packages | None for the installed helper. |
| State | Local `.project-os/state.sqlite3`. Initialization writes `.project-os/.gitignore` containing `*`; the root `.gitignore` is unchanged. |
| Network | The helper and installer run offline and make no model API calls. The chosen agent may use its own network service. |
| Codex | Project-local `.agents/skills/project-os`; current official discovery format, live package acceptance pending. |
| Claude Code | Project-local `.claude/skills/project-os`; current official discovery format, live package acceptance pending. |
| Global configuration | No changes required or performed by the installer. |

The two adapters use identical skill content. On a project with both installed, either helper addresses the same project-local state when passed the same `--project` directory. An installation directory is not a second database.

## Platform coverage

| Platform | Coverage |
| --- | --- |
| macOS | Local tests have run with Python 3.12.13 / 3.13.14. See [VERIFICATION.md](VERIFICATION.md) for the exact candidate's results; these do not validate live agent behavior. |
| Linux | **NOT TESTED**. The standard-library design is not a verified support claim. |
| Windows | **UNSUPPORTED** in this candidate: the installer uses the Unix-only `fcntl` module. |

No minimum Codex or Claude Code application version is asserted without a successful recorded canary. Product discovery rules can change; consult [Codex](https://developers.openai.com/codex/skills) and [Claude Code](https://code.claude.com/docs/en/skills) documentation when diagnosing discovery failures.

## Separate validation layers

1. **Local tests:** exercise persistence, context assembly, installation, and package boundaries in temporary projects. Run `python3 -m unittest discover -s tests -v` from the package root. Results are recorded in [VERIFICATION.md](VERIFICATION.md); a passing result establishes only the tested local behaviors.
2. **Synthetic demonstration:** `python3 examples/demo.py` uses fictional data. Its GIF is a local rendering, not an agent recording.
3. **Real fresh-agent canaries: NOT RUN.** These must establish skill discovery, useful context retrieval, evidence-aware recording, and continuation in a separate fresh session for each adapter. Pending instructions are in [CANARY.md](CANARY.md).
4. **Token or effectiveness benchmark: NOT MEASURED.** No saving percentage or general improvement claim is supported by the demo.

## Live canary gate

Before launching real agent sessions, obtain approval for the exact product/model and version, task fixture, session count, settings, and expected cost or quota use. Unknown costs stay pending. A failed or inconclusive run does not authorize an automatic retry.

Use a temporary fictional project. In session A, discover the installed skill, read context, make a small verifiable change, and record its result. In a fresh session B, discover the skill again, identify the saved state and next action, inspect the relevant files, and continue. Check manual-field preservation and the resulting receipts independently of the agent's summary.

For each adapter, retain a sanitized record of package hash, OS/Python and agent/model versions, approved settings, commands, expected/observed behavior, receipt readback, and pass/fail findings. Keep raw sessions and private data out of the public package. Update this document only after that evidence exists.
