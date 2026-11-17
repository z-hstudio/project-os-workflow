#!/usr/bin/env python3
"""Prepare a fictional local project; never start an agent or consume model quota."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

PACKAGE = Path(__file__).resolve().parents[1]


def prepare(output):
    root = Path(output).absolute()
    root.mkdir(parents=True, exist_ok=False)
    def run(args):
        result = subprocess.run([sys.executable, *args], cwd=root, text=True, capture_output=True, check=True)
        return json.loads(result.stdout)
    run([str(PACKAGE / 'install.py'), 'install', '--project', '.', '--agent', 'both'])
    helper = '.agents/skills/project-os/scripts/project_os.py'
    state = run([helper, '--project', '.', 'init', '--name', 'Tiny Notes Canary',
                 '--purpose', 'Keep small notes; verify handoff between coding agents', '--language', 'zh'])
    manual = dict(schema_version=1, project_id=state['project_id'], expected_revision=0,
                  idempotency_key='fixture-owner', agent='user', summary='Fixture owner constraints',
                  changes={'constraints': ['Only change this fictional project.', 'No network, dependency install, publish or model spawning.'],
                           'why': 'Human-owned note: preserve this text.'})
    (root / '.project-os/owner.json').write_text(json.dumps(manual))
    run([helper, '--project', '.', 'manual', '--input', '.project-os/owner.json'])
    (root / 'notes.py').write_text('def normalize(text):\n    return text\n')
    (root / 'test_notes.py').write_text('import unittest\nfrom notes import normalize\n\nclass NotesTests(unittest.TestCase):\n    def test_whitespace(self):\n        self.assertEqual(normalize(" hello "), "hello")\n')
    prompts = {
        'A-codex.txt': '使用 project-os Skill。先读状态和相关文件。仅修复 normalize 去除两侧空白，运行 python3 -m unittest。通过 Skill 保存结果，下一步写“拒绝空白笔记”。保留人工字段，不宣布整个项目完成。',
        'B-claude.txt': '使用 project-os Skill 接手这个项目。先读取状态，从记录识别下一步，核对源文件后实现它并添加测试。运行 python3 -m unittest 后保存记录，下一步写“补充 README 使用示例”。保留人工字段。',
        'C-codex-workflow.txt': '使用 project-os Skill 接续。读取状态和必要文件，完成保存的下一步，运行测试，保存结果。不要把本次聊天结束当作项目完成。',
        'D-codex-baseline.txt': '仅根据附加的 A/B 完整虚构会话历史和当前项目文件继续下一步，为 notes.normalize 补充 README 使用示例并运行测试。本次不读取 Project OS 状态、不调用其 helper。'
    }
    (root / 'canary-prompts').mkdir()
    for name, prompt in prompts.items():
        (root / 'canary-prompts' / name).write_text(prompt + '\n')
    return {'status': 'prepared_not_executed', 'sessions_launched': 0, 'model_calls': 0,
            'next': 'Read docs/CANARY.md and obtain exact model/quota authorization before launching any session.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.output), indent=2))
