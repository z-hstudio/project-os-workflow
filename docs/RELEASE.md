# Release candidate and release procedure

Candidate: **0.1.0-rc.1** · Prepared: **2026-11-17**

Public source: [z-hstudio/project-os-workflow](https://github.com/z-hstudio/project-os-workflow). Tagged downloads are listed on [GitHub Releases](https://github.com/z-hstudio/project-os-workflow/releases). Source publication does not establish live-agent acceptance, measured token savings, or a social-media announcement.

## Acceptance status

| Check | Status |
| --- | --- |
| Local helper, installation, and export tests | See [VERIFICATION.md](VERIFICATION.md) for actual results on macOS / Python 3.12.13 / 3.13.14. Python 3.11 is also tested in the Linux CI matrix. |
| Synthetic demo | Fictional offline workflow only; not live agent acceptance. |
| Codex fresh-session canary | **NOT RUN — exact model/quota authorization pending.** |
| Claude Code fresh-session canary | **NOT RUN — exact model/quota authorization pending.** |
| Linux | Ubuntu 24.04, Python 3.11/3.12/3.13: 31 offline tests and package checks passed in [CI](https://github.com/z-hstudio/project-os-workflow/actions/runs/44049174989). |
| Windows | **UNSUPPORTED**: the installer uses `fcntl`. |
| Token savings | **NOT MEASURED.** |
| Public publication | Public source repository verified. Tagged asset publication is tracked on GitHub Releases; no social-media post was sent. |

Do not replace pending live checks with mocked transcripts or the synthetic GIF. Keep the candidate label until the intended release acceptance has evidence.

## Prepare a local export

Run from the package root:

```sh
python3 -m unittest discover -s tests -v
python3 examples/demo.py
python3 scripts/export_release.py --output /new/empty/path
```

Use a destination path that does not yet exist. The exporter reads `release-files.txt`; it must not copy the parent repository recursively. The result is a reviewable local directory, not an upload.

Inspect the exported file list and sizes, verify the package version and license, and rerun the local tests from the export. Check that relative documentation links resolve, both READMEs match the CLI, and the demo is visibly labeled synthetic. Verify no private database, real project identifiers, user paths, full logs, credentials, or private screenshots are present.

Before publishing, review the exact destination, included files, license, candidate wording, and any platform costs. Obtain the matching authorization for that concrete external action. Live canaries require their own model/session authorization as described in [COMPATIBILITY.md](COMPATIBILITY.md); the pending run procedure is in [CANARY.md](CANARY.md).

## Candidate announcement drafts — not published

### 中文

做了一个 Project OS Workflow 候选版：把项目进展、依据和下一步存在项目自己的 SQLite 数据库里，让 Codex 和 Claude Code 在新会话里有一份简短的接续记录。Python 标准库运行，项目级安装。当前提供离线合成演示；真实新会话接续验收还没跑，也没有 token 节省数据。先开放候选版供检查和反馈。

### English

Project OS Workflow is a release candidate for keeping project progress, evidence, and next actions in a project-local SQLite database. It provides Codex and Claude Code skill adapters with a Python standard-library helper. The current demo is synthetic and offline. Real fresh-session continuation tests are still pending, and no token savings have been measured. The candidate is intended for inspection and feedback.

Use these drafts only after the actual candidate destination and publication have been approved. Replace availability language if no public candidate has been published.
