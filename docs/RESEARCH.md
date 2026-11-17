# Research and implementation decisions

Research snapshot: **2026-11-17**. This document records design references, not a dependency list or a claim that upstream behavior was reproduced.

## Official format and discovery references

| Source | Relevant observation | Package decision |
| --- | --- | --- |
| [Codex skills documentation](https://developers.openai.com/codex/skills) | Repository skills are discovered from `.agents/skills` locations. The URL currently redirects to [Build skills](https://learn.chatgpt.com/docs/build-skills). | Install only into the selected project's `.agents/skills/project-os`. |
| [Claude Code skills documentation](https://code.claude.com/docs/en/skills) | Local project skills use `.claude/skills/<skill-name>/SKILL.md`. | Provide a project-local Claude Code adapter from the same canonical tree. |
| [Agent Skills specification](https://agentskills.io/specification) | A skill contains a `SKILL.md` with frontmatter; scripts and reference files may accompany it. | Keep the entry concise and put execution logic and the report protocol in separate files. |

These documents justify packaging choices. They do not verify that either current agent will discover or follow this particular skill. That requires the live canaries described in [COMPATIBILITY.md](COMPATIBILITY.md).

## Related projects reviewed

Versions and revisions below identify the reviewed snapshots; they are not floating installation instructions.

| Project | Snapshot / license | Idea considered | Decision here |
| --- | --- | --- | --- |
| [obra/superpowers](https://github.com/obra/superpowers) | v7.0.2; [22f0b463e7a5e579904dd6211a520321035526f7](https://github.com/obra/superpowers/tree/22f0b463e7a5e579904dd6211a520321035526f7); MIT | Explicit workflow stages and verification before a completion claim. | Keep a narrow continuity workflow; do not bundle a development methodology. |
| [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) | v3.28.1; [51bf62def62d1cb317d37936929b4ef97cf862c3](https://github.com/OthmanAdi/planning-with-files/tree/51bf62def62d1cb317d37936929b4ef97cf862c3); MIT | Persist useful working state outside the conversation. | Use compact, structured SQLite records and an explicit context request. No per-turn hooks are installed. |
| [gsd-build/get-shit-done](https://github.com/gsd-build/get-shit-done) | v1.42.3; [bdcaab2c752d9a33a1a1ca9acf3a3c81fb991815](https://github.com/gsd-build/get-shit-done/tree/bdcaab2c752d9a33a1a1ca9acf3a3c81fb991815); MIT | Separate project context, work progression, and execution evidence. | Retain the small state/receipt boundary; do not add orchestration or model calls. |

The reviewed GSD repository was archived on **2026-06-26**; its current README points to a successor. Its snapshot is historical and is not an active dependency or a recommendation to install the archive.

The implementation uses these ideas as references. It copies no upstream code and adds no upstream runtime dependency. The package has its own [MIT license](../LICENSE). Upstream performance claims do not apply to this package.

## Scope decisions

- Python 3.11+ and the standard library keep the standalone helper inspectable and offline. SQLite holds project-local state and receipts.
- One canonical skill avoids adapter-specific protocol drift. The installer copies it into the selected locations without editing global settings.
- Agent reports remain attributed claims. Revision checks and receipt history help explain changes; they cannot establish that an external action succeeded.
- Manual values must survive automatic reports. Installation refuses existing targets; uninstall preserves changed or unowned files and the project database.
- Context has a byte budget. This is a size control, not a token benchmark or a guarantee about agent attention.
- Public exports use an explicit file list. Private project state and development workspace material do not belong in a distributable package.

Accounts, cloud sync, background services, transcript ingestion, automatic model calls, and desktop-app integration are outside this candidate's scope.

## Public continuous integration (2026-11-17)

The CI workflow references two official GitHub-maintained MIT actions, pinned to
observed immutable commits rather than moving version tags:

- [actions/checkout v7.0.1](https://github.com/actions/checkout/tree/3d3c42e5aac5ba805825da76410c181273ba90b1),
  commit `3d3c42e5aac5ba805825da76410c181273ba90b1`.
- [actions/setup-python v7.1.0](https://github.com/actions/setup-python/tree/6d4fd22b20465ccc0f7354476588e8df7c9ca0e0),
  commit `6d4fd22b20465ccc0f7354476588e8df7c9ca0e0`.

Release metadata and repository LICENSE files were read from the official GitHub
API. These are CI-only actions, not installed runtime dependencies. Checkout
disables persistent credentials; workflow permissions are contents-read only.

GitHub documents [standard public runners as free and unlimited](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
The workflow uses only `ubuntu-24.04`, skips private repositories, sets a five-
minute job timeout and uploads no artifact or cache. It invokes no model, uses
no paid runner, and does not spend a private repository's included compute quota.
