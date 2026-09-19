#!/usr/bin/env python3
"""幂等键：claim(key) —— 同一个键只允许第一次返回 True。

为什么需要它：自动运转的 agent 任务一定会被"重跑"——定时器重叠触发、队列重投、
run 失败后重试、崩溃恢复。如果动作本身不是幂等的，重跑就会产生两份副作用
（同一份报告发两次、台账写两遍）和两份 token 消耗。与其每次都提心吊胆地想
"这个会不会重复执行"，不如让每个"只该发生一次"的动作先领一张凭证：
领到了才干活。

键约定（这是调用方要遵守的契约，脚本只检查合法性，不强制结构）：

    <task_type>:<entity>:<time_bucket>

- task_type   动作类型，动词或名词，例如 daily-review / publish / approve
- entity      作用对象，例如 inbox / weekly-report / publish-2026-09-16
- time_bucket 时间桶，决定"多久算同一个键"，例如 2026-09-16T10:30 / 2026-09-16 / 2026-W38

例子：
    daily-review:inbox:2026-09-16          # 今天的收件箱复盘只跑一次
    publish:weekly-report:2026-W38         # 这周这份报告只发布一次
    approve:publish-2026-09-16:human       # 这条 L3 人工放行只记一次（闸门凭证）
    rebalance:portfolio:2026-W38           # 这周这个组合只调仓一次

time_bucket 是人的责任，不是脚本的：键取得太粗会漏做，取得太细会重复做。
ttl_seconds 是兜底——同一个键在 TTL 内只允许一次，过期后可以再来（给周期性任务）。

落盘格式：JSONL 追加写，O_APPEND + 单次 os.write，配合 POSIX flock，
并发调用不会撕裂行、也不会同时领到同一张凭证（定时器重叠触发时这一点很关键）。

只用标准库，兼容 Python 3.10+。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
EXIT_CLAIMED = 0
EXIT_ALREADY_CLAIMED = 1
EXIT_USAGE = 2

LEDGER_ENV = "RELIABLE_LEDGER"
MAX_KEY_LENGTH = 512
INVALID_LINE = "无法解析的 ledger 行"

try:  # POSIX 才有；没有 flock 时退化为"尽力而为"的追加语义
    import fcntl
except ImportError:  # pragma: no cover - 非 POSIX 平台
    fcntl = None


# --------------------------------------------------------------------------- #
# 基础工具
# --------------------------------------------------------------------------- #
def validate_key(key: object) -> str:
    if not isinstance(key, str) or not key.strip():
        raise ValueError("幂等键不能为空")
    text = key.strip()
    if len(text) > MAX_KEY_LENGTH:
        raise ValueError(f"幂等键过长（{len(text)} > {MAX_KEY_LENGTH}）")
    if any(character.isspace() for character in text) or "\n" in text:
        raise ValueError(f"幂等键不能包含空白字符：{text!r}")
    return text


def key_shape_warning(key: str) -> str | None:
    """键不满足 <task_type>:<entity>:<time_bucket> 约定时给出提醒（不阻断）。"""

    segments = key.split(":")
    if len(segments) < 3 or any(not segment for segment in segments):
        return (
            f"键 {key!r} 不满足约定 <task_type>:<entity>:<time_bucket>；"
            "结构化的键才能在以后回答谁在什么时候做过什么"
        )
    return None


def resolve_ledger(ledger_path: object) -> Path:
    if ledger_path is None:
        ledger_path = os.environ.get(LEDGER_ENV)
    if not ledger_path:
        raise ValueError(f"必须提供 ledger 路径（--ledger 或 {LEDGER_ENV} 环境变量）")
    return Path(os.path.expanduser(str(ledger_path)))


def _positive_seconds(value: object, label: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} 必须是正数或 None")
    number = float(value)
    if number != number or number <= 0:
        raise ValueError(f"{label} 必须是正数或 None")
    return number


def _lock(descriptor: int) -> None:
    if fcntl is not None:
        fcntl.flock(descriptor, fcntl.LOCK_EX)


def _unlock(descriptor: int) -> None:
    if fcntl is not None:
        fcntl.flock(descriptor, fcntl.LOCK_UN)


def _read_all(descriptor: int) -> list[dict]:
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks = []
    while True:
        chunk = os.read(descriptor, 65536)
        if not chunk:
            break
        chunks.append(chunk)
    records = []
    for line in b"".join(chunks).split(b"\n"):
        if not line.strip():
            continue
        try:
            payload = json.loads(line.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            records.append({"key": None, "ts": None, "invalid": True})
            continue
        records.append(payload if isinstance(payload, dict) else {"key": None, "ts": None, "invalid": True})
    return records


def _last_claim(records: list[dict], key: str) -> float | None:
    latest = None
    for record in records:
        if record.get("key") != key:
            continue
        stamp = record.get("ts")
        if isinstance(stamp, bool) or not isinstance(stamp, (int, float)):
            continue
        latest = float(stamp) if latest is None else max(latest, float(stamp))
    return latest


def _expired(stamp: float, ttl_seconds: float | None, now: float) -> bool:
    if ttl_seconds is None:
        return False
    return (now - stamp) >= ttl_seconds


def _encode(key: str, now: float, ttl_seconds: float | None) -> bytes:
    record = {
        "schemaVersion": SCHEMA_VERSION,
        "key": key,
        "ts": round(now, 3),
        "iso": datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pid": os.getpid(),
        "ttl_seconds": ttl_seconds,
    }
    return (json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


# --------------------------------------------------------------------------- #
# 公开接口
# --------------------------------------------------------------------------- #
def claim(
    key: str,
    ledger_path: object,
    ttl_seconds: object = None,
    now: object = None,
) -> bool:
    """领一次凭证。首次返回 True 并落盘；已领过返回 False（不写盘）。

    ttl_seconds 给定时，"已领过"只在 TTL 内成立；超过 TTL 视为可以再领一次。
    """

    clean_key = validate_key(key)
    ttl = _positive_seconds(ttl_seconds, "ttl_seconds")
    current = float(time.time() if now is None else now)
    path = resolve_ledger(ledger_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        _lock(descriptor)
        records = _read_all(descriptor)
        last = _last_claim(records, clean_key)
        if last is not None and not _expired(last, ttl, current):
            return False
        payload = _encode(clean_key, current, ttl)
        written = os.write(descriptor, payload)
        if written != len(payload):  # pragma: no cover - 只可能在磁盘异常时发生
            raise OSError(f"ledger 只写入了 {written}/{len(payload)} 字节")
        os.fsync(descriptor)
        return True
    finally:
        _unlock(descriptor)
        os.close(descriptor)


def records_for(key: str, ledger_path: object) -> list[dict]:
    """返回某个键的全部凭证记录（按落盘顺序）。"""

    clean_key = validate_key(key)
    path = resolve_ledger(ledger_path)
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except FileNotFoundError:
        return []
    try:
        return [record for record in _read_all(descriptor) if record.get("key") == clean_key]
    finally:
        os.close(descriptor)


def gc(ledger_path: object, now: object = None) -> dict:
    """清理过期凭证：丢掉 ttl 已过期的记录，以及无法解析的行。

    返回 {"kept": n, "removed": n, "invalid": n}。
    注意：重写是一次 os.replace，属于"换 inode"。所以 gc 只应在没有并发写入的
    时候跑（例如 cron 的安静时段），否则可能与正在追加的进程互相看不见。
    """

    current = float(time.time() if now is None else now)
    path = resolve_ledger(ledger_path)
    if not path.is_file():
        return {"kept": 0, "removed": 0, "invalid": 0}

    descriptor = os.open(path, os.O_RDONLY)
    try:
        _lock(descriptor)
        records = _read_all(descriptor)
    finally:
        _unlock(descriptor)
        os.close(descriptor)

    kept: list[bytes] = []
    removed = 0
    invalid = 0
    for record in records:
        if record.get("invalid"):
            invalid += 1
            continue
        stamp = record.get("ts")
        ttl = record.get("ttl_seconds")
        if isinstance(stamp, bool) or not isinstance(stamp, (int, float)):
            invalid += 1
            continue
        if isinstance(ttl, (int, float)) and not isinstance(ttl, bool) and float(ttl) > 0:
            if _expired(float(stamp), float(ttl), current):
                removed += 1
                continue
        kept.append(_render_record(record))

    replacement = path.with_name(path.name + ".gc")
    with replacement.open("wb") as stream:
        for line in kept:
            stream.write(line)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(replacement, path)
    return {"kept": len(kept), "removed": removed, "invalid": invalid}


def _render_record(record: dict) -> bytes:
    return (json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _add_json_flag(parser: argparse.ArgumentParser) -> None:
    """让 --json 既能放在子命令前，也能放在子命令后（default=SUPPRESS 避免覆盖）。"""

    parser.add_argument(
        "--json",
        action="store_true",
        default=argparse.SUPPRESS,
        help="输出机器可读 JSON",
    )


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ledger", default=None, help=f"JSONL 账本路径（默认读 {LEDGER_ENV} 环境变量）")
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    subparsers = parser.add_subparsers(dest="action", required=True)

    claim_parser = subparsers.add_parser(
        "claim", help="首次领取返回 0，已领过返回 1（便于 shell 里用 && 链）"
    )
    claim_parser.add_argument("key")
    claim_parser.add_argument("--ttl", type=float, default=None, help="TTL 秒数；省略表示该键永久只允许一次")
    _add_json_flag(claim_parser)

    show_parser = subparsers.add_parser("show", help="列出账本中的所有键与最近一次领取时间（只读）")
    _add_json_flag(show_parser)

    gc_parser = subparsers.add_parser("gc", help="清理过期凭证；只应在无并发写入时运行")
    _add_json_flag(gc_parser)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    arguments = parse_arguments(argv)
    try:
        path = resolve_ledger(arguments.ledger)
    except ValueError as error:
        sys.stderr.write(f"idempotency: {error}\n")
        return EXIT_USAGE

    try:
        if arguments.action == "claim":
            warning = key_shape_warning(arguments.key)
            if warning:
                sys.stderr.write(f"idempotency: 提醒：{warning}\n")
            first = claim(arguments.key, path, arguments.ttl)
            if arguments.json:
                sys.stdout.write(
                    json.dumps({"key": arguments.key, "first": first, "ledger": str(path)}, ensure_ascii=False) + "\n"
                )
            else:
                sys.stdout.write("claimed\n" if first else "already-claimed\n")
            return EXIT_CLAIMED if first else EXIT_ALREADY_CLAIMED

        if arguments.action == "show":
            descriptor = None
            try:
                descriptor = os.open(path, os.O_RDONLY)
                records = _read_all(descriptor)
            except FileNotFoundError:
                records = []
            finally:
                if descriptor is not None:
                    os.close(descriptor)
            if arguments.json:
                sys.stdout.write(json.dumps({"ledger": str(path), "records": records}, ensure_ascii=False, indent=2) + "\n")
            else:
                sys.stdout.write(f"# {path}（{len(records)} 条记录）\n")
                for record in records:
                    sys.stdout.write(f"  {record.get('iso', '?')}  ttl={record.get('ttl_seconds')}  {record.get('key')}\n")
            return EXIT_CLAIMED

        if arguments.action == "gc":
            report = gc(path)
            if arguments.json:
                sys.stdout.write(json.dumps({"ledger": str(path), **report}, ensure_ascii=False) + "\n")
            else:
                sys.stdout.write(
                    f"保留 {report['kept']} 条，清理 {report['removed']} 条过期，丢弃 {report['invalid']} 条无效行\n"
                )
            return EXIT_CLAIMED
    except (ValueError, OSError) as error:
        sys.stderr.write(f"idempotency: {error}\n")
        return EXIT_USAGE

    return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
