#!/usr/bin/env python3
"""Check this package's flat Skill metadata, links, Python syntax and public export."""
import argparse
import ast
import importlib.util
import json
from pathlib import Path
import re
import tempfile
from urllib.parse import unquote, urlsplit

spec = importlib.util.spec_from_file_location('workflow_export', Path(__file__).with_name('export_release.py'))
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


def check(root):
    root = Path(root).resolve()
    skill = (root / 'skill/project-os/SKILL.md').read_text(encoding='utf-8')
    match = re.match(r'\A---\n(.*?)\n---\n', skill, re.S)
    if not match:
        raise ValueError('Missing Skill metadata')
    meta = {}
    for line in match.group(1).splitlines():
        if ': ' not in line:
            raise ValueError('Skill metadata must use this package\'s flat scalar format')
        key, value = line.split(': ', 1)
        if key in meta or not value or ': ' in value or ' #' in value or value[0] in '\"\'[{*&!>|':
            raise ValueError('Invalid flat Skill metadata')
        meta[key] = value
    if set(meta) != {'name', 'description'} or meta['name'] != 'project-os' or not 1 <= len(meta['description']) <= 1024:
        raise ValueError('Invalid Skill metadata')
    # The exporter supplies path, size, private-data and allowlist validation.
    with tempfile.TemporaryDirectory(prefix='workflow-check-') as temp:
        exported = (Path(temp) / 'candidate').resolve()
        receipt = exporter.export(root, exported)
        if (root / 'SHA256SUMS').exists() and (root / 'SHA256SUMS').read_bytes() != (exported / 'SHA256SUMS').read_bytes():
            raise ValueError('Stale or incomplete public checksums')
        python_files = 0
        for path in exported.rglob('*'):
            if path.suffix == '.py':
                ast.parse(path.read_text(encoding='utf-8'), filename=str(path.relative_to(exported)), feature_version=(3, 11))
                python_files += 1
            if path.suffix != '.md':
                continue
            for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
                link = urlsplit(target)
                if link.scheme or link.netloc or not link.path:
                    continue
                resolved = (path.parent / unquote(link.path)).resolve()
                if not resolved.is_relative_to(exported) or not resolved.exists():
                    raise ValueError('Missing local link: ' + str(path.relative_to(exported)) + ' -> ' + target)
    return {'status': 'passed', 'files': receipt['files'], 'python_3_11_syntax_files': python_files,
            'skill_metadata': 'checked_flat_format_not_live_discovery', 'model_calls': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(check(args.root), indent=2))
