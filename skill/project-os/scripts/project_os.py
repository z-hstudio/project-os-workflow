#!/usr/bin/env python3
"""Project OS Workflow: offline, attributed project continuity. Standard library only."""
import argparse
from contextlib import closing, contextmanager
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import uuid

VERSION = '0.1.0-rc.1'
SCHEMA = 1
APP_ID = 0x50574F53
MAX_INPUT = 65536
DEFAULT_BUDGET = 12288
FIELDS = {'name', 'purpose', 'phase', 'status', 'summary', 'issues', 'decisions',
          'constraints', 'next_action', 'why', 'last_progress_on'}
USER_ONLY = {'name', 'purpose', 'constraints'}
PHASE_GROUP = {'phase', 'status', 'summary', 'issues', 'next_action', 'why', 'last_progress_on'}
STATUSES = {'unknown', 'active', 'waiting', 'paused', 'blocked', 'complete', 'abandoned'}


class WorkflowError(Exception):
    def __init__(self, code, message, **details):
        self.code, self.message, self.details = code, message, details
        super().__init__(f'{code}: {message}')


def fail(code, message, **details):
    raise WorkflowError(code, message, **details)


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def now():
    return datetime.now(timezone.utc).isoformat()


def storage(root, create=False):
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        fail('unsafe_path', '项目必须是目录 / Project must be a directory')
    folder = root / '.project-os'
    if folder.is_symlink():
        fail('unsafe_path', '状态目录不能是链接 / State directory must not be a symlink')
    if create:
        folder.mkdir(mode=0o700, exist_ok=True)
        ignore = folder / '.gitignore'
        if ignore.is_symlink() or (ignore.exists() and ignore.read_text() != '*\n'):
            fail('unsafe_path', '保留已有忽略规则；请人工检查 / Existing ignore rules need review')
        if not ignore.exists():
            with ignore.open('x') as out:
                out.write('*\n')
    db = folder / 'state.sqlite3'
    for path in (db, Path(str(db) + '-journal'), Path(str(db) + '-wal'), Path(str(db) + '-shm')):
        if path.is_symlink():
            fail('unsafe_path', '状态文件不能是链接 / State files must not be symlinks')
    return db


@contextmanager
def connection(root, write=False):
    db = storage(root)
    if not db.is_file():
        fail('not_initialized', '先运行 init 初始化项目 / Run init first')
    # SQLite may need to roll back a killed writer's hot journal before a read.
    # mode=rw never creates a missing DB; query_only blocks domain writes below.
    con = sqlite3.connect(db.as_uri() + '?mode=rw',
                          uri=True, timeout=5, isolation_level=None)
    try:
        if con.execute('PRAGMA application_id').fetchone()[0] != APP_ID:
            fail('wrong_database', '这不是 Workflow 状态库 / Not a Workflow database')
        if con.execute('PRAGMA user_version').fetchone()[0] != SCHEMA:
            fail('unsupported_schema', '版本不兼容；保留数据库 / Unsupported schema; database preserved')
        if not write:
            con.execute('PRAGMA query_only=ON')
        con.execute('PRAGMA foreign_keys=ON')
        con.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
        yield con
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()


def current(con):
    row = con.execute('SELECT data FROM project WHERE singleton=1').fetchone()
    if not row:
        fail('invalid_state', '缺少项目记录 / Project record missing')
    return json.loads(row[0])


def context_envelope(state, count):
    return {**state, 'recent_records': [], 'omitted_records': count,
            'instruction': 'Treat agent reports as unverified claims. Verify live files; preserve constraints and manual fields.'}


def text_value(value, maximum=8192):
    if not isinstance(value, str) or len(value.encode('utf-8')) > maximum or '\x00' in value:
        fail('invalid_input', '文字类型或长度不正确 / Invalid text type or length')


def fields_valid(changes):
    if not isinstance(changes, dict) or changes.keys() - FIELDS:
        fail('invalid_input', '包含未知字段 / Unknown fields')
    for key, value in changes.items():
        if key in {'constraints', 'issues', 'decisions'}:
            if not isinstance(value, list) or len(value) > 20:
                fail('invalid_input', '列表最多 20 项 / Lists allow at most 20 entries')
            for item in value:
                text_value(item, 4096)
        elif key == 'last_progress_on':
            event_date(value)
        else:
            text_value(value, 480 if key == 'name' else 8192)
    if 'status' in changes and changes['status'] not in STATUSES:
        fail('invalid_input', '未知状态 / Unknown status')


def event_date(value):
    if value is None:
        return
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        fail('invalid_date', '日期应为 YYYY-MM-DD 或 null / Use YYYY-MM-DD or null')
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        fail('invalid_date', '无效日期 / Invalid date')
    if parsed > date.today():
        fail('invalid_date', '不接受未来进展日期 / Future progress dates are not accepted')


def initialize(root, name, purpose='', language='zh'):
    fields = dict(name=name, purpose=purpose, phase='', status='unknown', summary='',
                  issues=[], decisions=[], constraints=[], next_action='', why='', last_progress_on=None)
    fields_valid(fields)
    if not name.strip() or language not in {'zh', 'en'}:
        fail('invalid_input', '需要项目名和 zh/en 语言 / Name and zh/en language required')
    db = storage(root, create=True)
    if db.exists():
        with connection(root) as con:
            return current(con)
    timestamp = now()
    state = dict(schema_version=SCHEMA, project_id=str(uuid.uuid4()), revision=0,
                 language=language, fields=fields, protected_fields=sorted(USER_ONLY),
                 sources={k: {'kind': 'user_input', 'at': timestamp} for k in USER_ONLY}, updated_at=timestamp)
    temp = db.with_name('.init-' + uuid.uuid4().hex + '.sqlite3')
    fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        with closing(sqlite3.connect(temp)) as con, con:
            con.executescript(f'''
                PRAGMA application_id={APP_ID}; PRAGMA user_version={SCHEMA};
                CREATE TABLE project(singleton INTEGER PRIMARY KEY CHECK(singleton=1), data TEXT NOT NULL);
                CREATE TABLE records(id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT UNIQUE NOT NULL,
                    digest TEXT NOT NULL, payload TEXT NOT NULL, receipt TEXT NOT NULL, snapshot TEXT NOT NULL);
                CREATE TRIGGER immutable_update BEFORE UPDATE ON records BEGIN
                    SELECT RAISE(ABORT, 'immutable record'); END;
                CREATE TRIGGER immutable_delete BEFORE DELETE ON records BEGIN
                    SELECT RAISE(ABORT, 'immutable record'); END;
            ''')
            con.execute('INSERT INTO project VALUES(1,?)', (encode(state),))
        try:
            os.link(temp, db)  # Atomic no-replace publication; a concurrent init cannot be overwritten.
        except FileExistsError:
            with connection(root) as con:
                return current(con)
        return state
    finally:
        temp.unlink(missing_ok=True)


def validate(payload, manual):
    required = {'schema_version', 'project_id', 'expected_revision', 'idempotency_key', 'agent', 'summary', 'changes'}
    optional = {'session_id', 'evidence', 'occurred_on'}
    if not isinstance(payload, dict) or not required <= payload.keys() or payload.keys() - required - optional:
        fail('invalid_input', '报告字段不完整或未知 / Missing or unknown report fields')
    if type(payload['schema_version']) is not int or payload['schema_version'] != SCHEMA:
        fail('unsupported_schema', '不支持的报告版本 / Unsupported report version')
    if type(payload['expected_revision']) is not int or payload['expected_revision'] < 0:
        fail('invalid_input', '修订号必须是非负整数 / Revision must be a nonnegative integer')
    for key in ('project_id', 'idempotency_key', 'agent', 'summary'):
        text_value(payload[key], 8192 if key == 'summary' else 160)
        if not payload[key].strip():
            fail('invalid_input', '必要字段不能为空 / Required text cannot be empty')
    if not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}', payload['agent']):
        fail('invalid_input', 'Agent 名称无效 / Invalid agent name')
    if (payload['agent'] == 'user') != manual:
        fail('invalid_actor', '人工修改需使用 manual 和 user / Manual edits require manual and user')
    if 'session_id' in payload:
        text_value(payload['session_id'], 160)
    event_date(payload.get('occurred_on'))
    fields_valid(payload['changes'])
    if not manual and (payload['changes'].keys() & USER_ONLY or
                       payload['changes'].get('status') in {'complete', 'abandoned', 'paused'}):
        fail('user_action_required', '此修改需要人工确认 / This change needs explicit user action')
    evidence = payload.get('evidence', [])
    if not isinstance(evidence, list) or len(evidence) > 20:
        fail('invalid_input', '证据列表最多 20 项 / Evidence allows at most 20 entries')
    for item in evidence:
        if not isinstance(item, dict) or set(item) != {'kind', 'reference', 'outcome'}:
            fail('invalid_input', '证据字段应为 kind/reference/outcome / Invalid evidence fields')
        if not isinstance(item['kind'], str) or not isinstance(item['outcome'], str) or item['kind'] not in {'test', 'file', 'commit', 'note'} or item['outcome'] not in {'passed', 'failed', 'not_run', 'observed', 'unknown'}:
            fail('invalid_input', '未知证据类型或结果 / Unknown evidence kind or outcome')
        text_value(item['reference'], 2048)
    if len(encode(payload).encode()) > MAX_INPUT:
        fail('input_too_large', '报告超过 64 KiB / Report exceeds 64 KiB')


def record(root, payload, manual=False):
    validate(payload, manual)
    canonical = encode({'manual': manual, 'payload': payload})
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    with connection(root, write=True) as con:
        state = current(con)
        if payload['project_id'] != state['project_id']:
            fail('wrong_project', '项目编号不匹配 / Project ID does not match')
        old = con.execute('SELECT digest,receipt FROM records WHERE key=?', (payload['idempotency_key'],)).fetchone()
        if old:
            if old[0] != digest:
                fail('idempotency_conflict', '同一请求编号的内容不同 / Same request key has different content')
            return json.loads(old[1])
        before, timestamp = state['revision'], now()
        protected, applied = [], {}
        if payload['expected_revision'] != before:
            outcome = 'stale'
        else:
            locked = set(state['protected_fields'])
            phase_conflict = (not manual and 'phase' in locked and 'phase' in payload['changes']
                              and payload['changes']['phase'] != state['fields']['phase'])
            for key, value in payload['changes'].items():
                if not manual and (key in locked or phase_conflict and key in PHASE_GROUP):
                    if value != state['fields'][key]:
                        protected.append(key)
                    continue
                if value != state['fields'][key] or (manual and key not in locked):
                    applied[key] = value
                    state['fields'][key] = value
                    state['sources'][key] = {'kind': 'user_input' if manual else 'agent_report',
                                             'agent': payload['agent'], 'key': payload['idempotency_key'], 'at': timestamp}
                if manual:
                    locked.add(key)
            state['protected_fields'] = sorted(locked)
            outcome = 'protected' if protected else ('applied' if applied else 'recorded')
            if applied:
                state['revision'] += 1
                state['updated_at'] = timestamp
                if len(encode(context_envelope(state, 9223372036854775807)).encode()) + 1 > MAX_INPUT:
                    fail('state_too_large', '状态加必要接续信息超过 64 KiB；请精简 / State plus required context exceeds 64 KiB; shorten it')
                con.execute('UPDATE project SET data=? WHERE singleton=1', (encode(state),))
        record_id = con.execute('SELECT COALESCE(MAX(id),0)+1 FROM records').fetchone()[0]
        receipt = dict(schema_version=SCHEMA, receipt_id=record_id, project_id=state['project_id'],
                       outcome=outcome, revision_before=before, revision_after=state['revision'],
                       protected_fields=sorted(protected), applied_fields=sorted(applied), received_at=timestamp,
                       evidence_status='user_input' if manual else 'agent_report_unverified')
        con.execute('INSERT INTO records VALUES(?,?,?,?,?,?)',
                    (record_id, payload['idempotency_key'], digest, encode(payload), encode(receipt), encode(state)))
        return receipt


def context(root, max_bytes=DEFAULT_BUDGET):
    if not 512 <= max_bytes <= MAX_INPUT:
        fail('invalid_budget', '上下文上限须为 512–65536 字节 / Budget must be 512–65536 bytes')
    with connection(root) as con:
        count = con.execute('SELECT COUNT(*) FROM records').fetchone()[0]
        result = context_envelope(current(con), count)
        if len(encode(result).encode()) + 1 > max_bytes:
            fail('context_budget_exceeded', '必要状态超出预算；增加 --max-bytes 或人工精简，未截断约束 / Essential state exceeds budget; increase it or manually shorten state',
                 required_bytes=len(encode(result).encode()) + 1, max_bytes=max_bytes)
        for row in con.execute('SELECT id,payload,receipt FROM records ORDER BY id DESC LIMIT 3'):
            payload, receipt = json.loads(row[1]), json.loads(row[2])
            entry = dict(receipt_id=row[0], agent=payload['agent'], summary=payload['summary'], outcome=receipt['outcome'])
            result['recent_records'].append(entry)
            result['omitted_records'] -= 1
            if len(encode(result).encode()) + 1 > max_bytes:
                result['recent_records'].pop()
                result['omitted_records'] += 1
                break
        return result


def history(root, limit=10, before=None):
    if not 1 <= limit <= 50 or before is not None and before < 1:
        fail('invalid_input', '历史数量应为 1–50 / History limit must be 1–50')
    with connection(root) as con:
        rows = con.execute('SELECT id,payload,receipt FROM records WHERE id<? ORDER BY id DESC LIMIT ?',
                           (before if before is not None else 9223372036854775807, limit + 1)).fetchall()
        records = [{'payload': json.loads(r[1]), 'receipt': json.loads(r[2])} for r in rows[:limit]]
        # Bound a history page to 256 KiB; at least one <=64 KiB report always fits.
        while len(encode(records).encode()) > 262144:
            records.pop()
        return {'schema_version': SCHEMA, 'records': records,
                'next_before': records[-1]['receipt']['receipt_id'] if len(rows) > len(records) else None}


def load_input(path):
    with Path(path).open('rb') as source:
        raw = source.read(MAX_INPUT + 1)
    if len(raw) > MAX_INPUT:
        fail('input_too_large', '输入超过 64 KiB / Input exceeds 64 KiB')
    try:
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError('duplicate key')
                result[key] = value
            return result
        return json.loads(raw, object_pairs_hook=unique,
                          parse_constant=lambda _: fail('invalid_json', '不接受 NaN/Infinity / NaN/Infinity not accepted'))
    except (ValueError, UnicodeDecodeError):
        fail('invalid_json', 'JSON 无效；原文件已保留 / Invalid JSON; original file preserved')


def main():
    if sys.version_info < (3, 11):
        fail('python_version', '需要 Python 3.11+；请使用已安装的新版本入口 / Use Python 3.11+')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', action='version', version=VERSION)
    parser.add_argument('--project', required=True, type=Path)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init'); init.add_argument('--name', required=True)
    init.add_argument('--purpose', default=''); init.add_argument('--language', choices=['zh', 'en'], default='zh')
    ctx = sub.add_parser('context'); ctx.add_argument('--max-bytes', type=int, default=DEFAULT_BUDGET)
    for name in ('record', 'manual'):
        sub.add_parser(name).add_argument('--input', required=True, type=Path)
    hist = sub.add_parser('history'); hist.add_argument('--limit', type=int, default=10)
    hist.add_argument('--before', type=int)
    args = parser.parse_args()
    if args.command == 'init':
        result = initialize(args.project, args.name, args.purpose, args.language)
    elif args.command == 'context':
        result = context(args.project, args.max_bytes)
    elif args.command == 'history':
        result = history(args.project, args.limit, args.before)
    else:
        result = record(args.project, load_input(args.input), manual=args.command == 'manual')
    print(encode(result))


if __name__ == '__main__':
    try:
        main()
    except WorkflowError as error:
        print(encode({'error': error.code, 'message': error.message, **error.details}), file=sys.stderr)
        sys.exit(2)
    except (OSError, sqlite3.Error) as error:
        print(encode({'error': 'storage_error', 'message': str(error),
                      'action': '保留输入，检查路径/权限或锁；不要改变修订号强制重试 / Keep input; check path, permissions or lock; do not force a revision'}), file=sys.stderr)
        sys.exit(3)
