#!/usr/bin/env python3
"""Install/uninstall the canonical Skill into one explicit local project."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid

SOURCE = Path(__file__).resolve().parent / 'skill/project-os'
FILES = ('SKILL.md', 'scripts/project_os.py', 'references/protocol.md')
DESTINATIONS = {'codex': '.agents/skills/project-os', 'claude': '.claude/skills/project-os'}


class InstallError(Exception):
    pass


def digest(body):
    return hashlib.sha256(body).hexdigest()


def safe(root, relative):
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts:
        raise InstallError('Unsafe path / 不安全的路径')
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise InstallError('Symlink refused / 不写入符号链接')
    return current


def selected(agent):
    if agent not in {'both', *DESTINATIONS}:
        raise InstallError('Unknown agent / 未知 Agent')
    return list(DESTINATIONS.values()) if agent == 'both' else [DESTINATIONS[agent]]


@contextmanager
def locked(root):
    import fcntl  # macOS/Linux only; Windows is not a supported release platform.
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise InstallError('Project must be a directory / 项目必须是目录')
    data = safe(root, '.project-os')
    data.mkdir(mode=0o700, exist_ok=True)
    ignore = safe(root, '.project-os/.gitignore')
    if not ignore.exists():
        with ignore.open('x') as stream:
            stream.write('*\n')
    elif ignore.read_text() != '*\n':
        raise InstallError('Existing ignore rules need manual review / 保留已有忽略规则，请人工检查')
    lock = safe(root, '.project-os/install.lock')
    with lock.open('a') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise InstallError('Another installation is running / 另一个安装操作尚未结束') from None
        yield root


def manifest(root):
    path = safe(root, '.project-os/installation.json')
    data = json.loads(path.read_text()) if path.exists() else {'schema_version': 1, 'files': {}, 'directories': []}
    if data.get('schema_version') != 1 or not isinstance(data.get('files'), dict) or not isinstance(data.get('directories'), list):
        raise InstallError('Unsupported installation manifest / 安装记录格式不兼容')
    allowed_files = {base + '/' + name for base in DESTINATIONS.values() for name in FILES}
    allowed_dirs = {str(p) for base in DESTINATIONS.values()
                    for name in FILES for p in Path(base, name).parents if str(p) != '.'}
    if data['files'].keys() - allowed_files or set(data['directories']) - allowed_dirs:
        raise InstallError('Invalid ownership paths / 安装记录包含非本包路径')
    for name in [*data['files'], *data['directories']]:
        safe(root, name)
    return data


def save_manifest(root, data):
    path = safe(root, '.project-os/installation.json')
    temp = path.with_name('.installation-' + uuid.uuid4().hex)
    try:
        temp.write_text(json.dumps(data, indent=2) + '\n')
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def create_file(path, body):
    stream = path.open('xb')  # Acquire ownership before enabling cleanup.
    try:
        with stream:
            stream.write(body)
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def install(project, agent='both'):
    bodies = {name: (SOURCE / name).read_bytes() for name in FILES}
    targets = selected(agent)
    with locked(project) as root:
        data, planned = manifest(root), []
        for base in targets:
            directory = safe(root, base)
            if directory.exists() and not any(p.startswith(base + '/') for p in data['files']):
                raise InstallError('Existing skill preserved; choose another project / 保留已有同名 Skill')
            for name, body in bodies.items():
                relative = base + '/' + name
                path = safe(root, relative)
                if path.exists():
                    if not path.is_file() or data['files'].get(relative) != digest(path.read_bytes()) or digest(body) != data['files'][relative]:
                        raise InstallError('Existing file differs; no overwrite / 已有文件不同，不覆盖安装')
                else:
                    planned.append((relative, body))
        created, directories = [], []
        try:
            for relative, body in planned:
                path = root / relative
                for folder in reversed(path.parents):
                    if folder == root or root not in folder.parents or folder.exists():
                        continue
                    folder.mkdir()
                    directories.append(folder)
                create_file(path, body)
                created.append(path)
                data['files'][relative] = digest(body)
            data['directories'] = sorted(set(data['directories']) | {str(p.relative_to(root)) for p in directories})
            save_manifest(root, data)
        except BaseException:
            for path in reversed(created):
                path.unlink(missing_ok=True)
            for folder in reversed(directories):
                try:
                    folder.rmdir()
                except OSError:
                    pass
            raise
        return {'status': 'installed' if planned else 'already_installed', 'files_written': len(planned), 'agents': agent}


def uninstall(project, agent='both'):
    targets = selected(agent)
    with locked(project) as root:
        data, removed, preserved = manifest(root), [], []
        for relative, expected in list(data['files'].items()):
            if not any(relative.startswith(base + '/') for base in targets):
                continue
            path = safe(root, relative)
            if path.exists() and (not path.is_file() or digest(path.read_bytes()) != expected):
                preserved.append(relative)
                continue
            if path.exists():
                path.unlink()
                removed.append(relative)
            del data['files'][relative]
        for relative in sorted(data['directories'], key=lambda s: len(Path(s).parts), reverse=True):
            path = safe(root, relative)
            try:
                path.rmdir()
            except OSError:
                continue
            data['directories'].remove(relative)
        save_manifest(root, data)
        return {'status': 'uninstalled', 'removed': removed, 'preserved': preserved, 'project_state': 'retained'}


def main():
    if sys.version_info < (3, 11):
        raise InstallError('Python 3.11+ required; use a newer installed executable / 需要 Python 3.11+，请更换已安装的入口')
    import sqlite3
    sqlite3.connect(':memory:').close()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['install', 'uninstall'])
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--agent', choices=['both', 'codex', 'claude'], default='both')
    args = parser.parse_args()
    print(json.dumps((install if args.command == 'install' else uninstall)(args.project, args.agent)))


if __name__ == '__main__':
    try:
        main()
    except (InstallError, OSError, ValueError, ImportError) as error:
        print(json.dumps({'error': 'installation_failed', 'message': str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(2)
