# Contributing

Keep changes focused on reliable project handoff. Runtime code uses Python 3.11+
and its standard library; no desktop app, model API or network service is needed.

Before submitting a change:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_package.py
```

Tests create isolated fictional projects. Do not use private databases, original
chat histories, credentials or real project screenshots in fixtures or issues.
Do not replace real-agent acceptance with the offline demo.

Keep these boundaries:

- Preserve manually edited fields, immutable receipts and revision checks.
- Agent reports are attributed claims, not proof of completion.
- Edit `skill/project-os` once; both installation locations use that source.
- Add a failing behavior test for persistence or installation changes.
- Add public files deliberately to `release-files.txt`; no recursive uploads.
- Keep Chinese/English instructions consistent with actual commands and results.
- Do not launch real model sessions as part of tests or CI. See [CANARY.md](docs/CANARY.md).

CI runs isolated tests and package validation on standard public GitHub-hosted
Linux runners with Python 3.11, 3.12 and 3.13. No model credentials or secret
environment variables are required. Private repository copies skip this CI job
to avoid consuming private-runner billing allowances.

For defects, use the [issue template](.github/ISSUE_TEMPLATE/bug_report.md) with a
minimal synthetic reproduction. Changes to project state format need an explicit
compatibility/migration plan; never fix a schema problem by deleting user data.
