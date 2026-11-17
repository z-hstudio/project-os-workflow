# Fresh-agent acceptance and usage comparison

Status: **NOT RUN**. The offline demo and unit tests do not establish that Codex
or Claude Code discovers or obeys this Skill. This document is an executable
acceptance procedure, not permission to consume model quota.

## Prepare without a model

```sh
python3 scripts/prepare_canary.py --output /new/temporary/tiny-notes-canary
```

This creates a fictional project, both Skill installations, a deliberately failing
whitespace test, user-protected constraints/reason, and four prompt files. It calls
only Python scripts. It never launches `codex`, `claude`, or another model.

Before a live run, record and approve: exact Codex/Claude product versions and
models, package SHA256SUMS, fixture version, reasoning/settings, session count
(maximum four, one attempt each), input/output limits supported by the runtime,
estimated and maximum charge/quota usage, and whether any paid entitlement is used.
**Unknown pricing/quota stays pending; do not silently substitute a model.**
If a hard cap is unsupported, disclose that and leave the run manual. No auto-retry.

## Four bounded sessions

| Session | Fresh agent | Task and required evidence |
|---|---|---|
| A | Codex | Use `A-codex.txt`; observe Skill load, context read, whitespace fix, real test exit and save receipt. |
| B | Claude Code | Use `B-claude.txt`; independently discover next action, add empty-input behavior/test, save receipt. |
| C | Codex | Use `C-codex-workflow.txt`; read B's result, add README example, test and save. This is the workflow measurement. |
| D | Same Codex model/version/settings as C | Use `D-codex-baseline.txt`; provide only the complete synthetic A/B conversation plus source files at B's completion. Same documentation task and acceptance. |

After B, freeze a byte-identical source snapshot for C and D, before either starts.
Give C the installed Skill/state. Give D the same source plus synthetic A/B history,
with the Workflow Skill/state absent from its copy. Use separate project directories
and fresh sessions. Other relevant system settings must match. Record unavoidable
differences, including cache state and tool inventories; an unmatched run is not
a valid savings claim. Do not read or attach real user conversation archives.

Read back the database through `context` and `history` after A, B and C. Acceptance:
the expected new source behavior and tests pass; agent/session attribution is
correct; next actions survive across sessions; `why` and constraints retain the
fixture owner's values; no agent report promotes itself to verified completion.
The agent must invoke its installed Skill and helper; copying commands into a
script on its behalf is not discovery evidence. Missing save or skipped Skill load
is a failed canary, even if the agent says it finished.

Record discovered product/model versions, package hash, observed Skill read path,
command/exit evidence, receipt IDs and revision transitions in a sanitized local
result. Keep raw sessions private. Do not include credentials or personal paths
in public evidence. A version detection check alone is not compatibility testing.

## Normalize actual usage

Create one measurement JSON per C/D run, from the runtime's actual usage report:

```json
{
  "mode": "workflow",
  "task_id": "tiny-notes-readme-v1",
  "model": "EXACT_MODEL",
  "model_version": "EXACT_VERSION",
  "fixture_sha256": "SOURCE_SNAPSHOT_SHA256",
  "settings": {"reasoning": "EXACT_SETTING"},
  "source": "runtime_usage",
  "passed": true,
  "input_tokens": 0,
  "cached_input_tokens": null,
  "output_tokens": 0,
  "reasoning_tokens": null,
  "tool_calls": 0,
  "elapsed_seconds": 0,
  "attempts": 1
}
```

Zeroes above are placeholders, **not measurements**. Use `mode: "baseline"` for D.
Input includes its cached subset; output includes its reasoning subset. If the
runtime's counters have different definitions, normalize explicitly and retain the
source definition; do not add subset counts twice. Unknown subsets stay null.
Do not replace missing total usage with character/byte estimates.

```sh
python3 scripts/compare_usage.py --baseline baseline.json --workflow workflow.json
```

The comparator rejects mismatched models/tasks/snapshots/settings, failed tasks,
estimated usage, retries and impossible counters. Its result covers one matched
pair only and makes no monetary claim. Report output tokens, cached/reasoning
subsets, tool calls, time, correctness and input reduction together. A smaller
prompt that causes an incomplete task is not a successful efficiency result.

Release remains **partial** until A/B/C pass. Token improvement remains
**not measured** until a matched C/D pair is available. If a session fails, preserve
its evidence and stop that run; fixes are offline until another specific live-run
authorization is given.
