#!/usr/bin/env python3
"""Export an allowlisted, history-free public candidate. Never uploads or commits."""
import argparse
import hashlib
from pathlib import Path
import re
import shutil
import tempfile


def export(source, output):
    source, output = Path(source).resolve(), Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError('Output must not exist; existing files are preserved')
    if source == output.resolve() or source in output.resolve().parents:
        raise ValueError('Export outside the source package')
    names = [line.strip() for line in (source / 'release-files.txt').read_text().splitlines()
             if line.strip() and not line.startswith('#')]
    if len(names) != len(set(names)) or not names:
        raise ValueError('Allowlist must be nonempty and unique')
    files = {}
    for name in names:
        p = Path(name)
        if p.is_absolute() or '..' in p.parts or set(p.parts) & {'.git', '.project-os', '__pycache__'} or p.suffix in {'.sqlite3', '.db', '.pyc'} or p.name == '.env':
            raise ValueError('Private or unsafe path in allowlist')
        path = source / p
        if any((source / Path(*p.parts[:i])).is_symlink() for i in range(1, len(p.parts) + 1)):
            raise ValueError('Symlinks are not exported')
        body = path.read_bytes()
        if len(body) > 5 * 1024 * 1024:
            raise ValueError('Individual export file exceeds 5 MiB')
        if p.suffix != '.gif':
            text = body.decode('utf-8')
            if re.search(r'/(?:Users|home)/[^\s/]+/|-----BEGIN [A-Z ]*PRIVATE KEY-----|sk-[A-Za-z0-9]{32,}', text):
                raise ValueError('Potential private path or credential in ' + name)
        elif not body.startswith((b'GIF87a', b'GIF89a')):
            raise ValueError('Invalid GIF signature')
        files[name] = body
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.workflow-export-', dir=output.parent))
    try:
        checksums = []
        for name, body in sorted(files.items()):
            path = stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
            checksums.append(hashlib.sha256(body).hexdigest() + '  ' + name)
        (stage / 'SHA256SUMS').write_text('\n'.join(checksums) + '\n')
        if output.exists():
            raise FileExistsError('Output appeared during export; preserved')
        stage.rename(output)
    finally:
        if stage.exists():
            shutil.rmtree(stage)  # This invocation's exact temporary directory only.
    return {'files': len(files), 'bytes': sum(map(len, files.values())),
            'manifest_sha256': hashlib.sha256(('\n'.join(checksums) + '\n').encode()).hexdigest(),
            'git_history': 'none', 'published': False}


if __name__ == '__main__':
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export(Path(__file__).resolve().parents[1], args.output), indent=2))
