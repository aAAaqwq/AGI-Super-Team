#!/usr/bin/env python3
"""心跳：给任务写"我还在工作"的信号，并读回来判断新鲜度。

进程活着 != 在工作，run 结束 != 有产出。`KeepAlive` / `Restart=always` 只能把
死掉的进程拉起来，它们不会发现"进程活着但卡住了"；而一次 agent run 跑完没产出、
或者跳过没说出口，人类看到的只有"没消息"——和"这次不需要跑"长得一模一样。

心跳补的正是这一段：任务每完成一轮就写一次时间戳，watchdog.py 用
kind=heartbeat 读它。心跳落在 agent 会话之外（状态目录），所以会话结束不影响它。

写入是原子的（先写临时文件再 os.replace），所以任何时刻读到的都是完整 JSON，
不会读到写了一半的内容。

状态目录优先级：--dir 参数 > RELIABLE_HEARTBEAT_DIR 环境变量 >
$XDG_STATE_HOME/heartbeats > ~/.local/state/heartbeats

只用标准库，兼容 Python 3.10+。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
EXIT_OK = 0
EXIT_STALE = 1
EXIT_USAGE = 2

DIRECTORY_ENV = "RELIABLE_HEARTBEAT_DIR"
DEFAULT_TS_FIELD = "ts"
NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

STATUS_OK = "ok"
STATUS_STALE = "stale"
STATUS_MISSING = "missing"


def state_dir(override: object = None) -> Path:
    """解析心跳目录，展开 ~ 与环境变量。"""

    if override is not None:
        return Path(os.path.expanduser(str(override)))
    from_environment = os.environ.get(DIRECTORY_ENV)
    if from_environment:
        return Path(os.path.expanduser(from_environment))
    xdg_state = os.environ.get("XDG_STATE_HOME")
    base = Path(os.path.expanduser(xdg_state)) if xdg_state else Path.home() / ".local" / "state"
    return base / "heartbeats"


def validate_name(name: object) -> str:
    if not isinstance(name, str) or not NAME_PATTERN.match(name.strip()):
        raise ValueError(
            f"心跳名不合法：{name!r}（只允许字母、数字、点、下划线、连字符，长度 1-64）"
        )
    return name.strip()


def heartbeat_path(name: str, directory: object = None) -> Path:
    return state_dir(directory) / f"{validate_name(name)}.json"


def write_heartbeat(
    name: str,
    directory: object = None,
    note: object = None,
    extra: object = None,
    now: object = None,
) -> Path:
    """原子写入一次心跳，返回心跳文件路径。"""

    target = heartbeat_path(name, directory)
    timestamp = float(time.time() if now is None else now)
    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "name": validate_name(name),
        "ts": round(timestamp, 3),
        "iso": datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pid": os.getpid(),
    }
    if isinstance(note, str) and note.strip():
        payload["note"] = note.strip()
    if isinstance(extra, dict):
        for key, value in extra.items():
            if key not in payload:
                payload[key] = value
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=str(target.parent), prefix=".heartbeat-", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    return target


def _resolve(source: object, directory: object = None) -> Path:
    """source 可以是心跳名，也可以是显式路径。"""

    text = str(source)
    path = Path(os.path.expanduser(text))
    if path.is_absolute() or os.sep in text:
        return path
    if path.suffix == ".json":
        return state_dir(directory) / path.name
    return heartbeat_path(text, directory)


def read_heartbeat(source: str, directory: object = None) -> dict | None:
    """读心跳；文件不存在、不可读、JSON 坏都返回 None，不抛异常。"""

    try:
        path = _resolve(source, directory)
    except ValueError:
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def heartbeat_age(source: str, directory: object = None, now: object = None) -> float | None:
    """返回心跳距今秒数；读不到或时间戳不可解析时返回 None。"""

    payload = read_heartbeat(source, directory)
    if payload is None:
        return None
    value = payload.get(DEFAULT_TS_FIELD)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    current = float(time.time() if now is None else now)
    return max(0.0, current - float(value))


def inspect(
    name: str,
    directory: object = None,
    max_age_seconds: object = None,
    now: object = None,
) -> dict:
    """给 CLI 与测试用的状态摘要。"""

    current = float(time.time() if now is None else now)
    age = heartbeat_age(name, directory, now=current)
    limit = float(max_age_seconds) if max_age_seconds is not None else None
    if age is None:
        status = STATUS_MISSING
    elif limit is not None and age > limit:
        status = STATUS_STALE
    else:
        status = STATUS_OK
    return {
        "name": name,
        "path": str(heartbeat_path(name, directory)),
        "status": status,
        "age_seconds": None if age is None else round(age, 3),
        "max_age_seconds": limit,
        "checked_at": datetime.fromtimestamp(current, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", default=None, help=f"心跳目录（默认 {DIRECTORY_ENV} 或 XDG 状态目录）")
    subparsers = parser.add_subparsers(dest="action", required=True)

    beat = subparsers.add_parser("beat", help="写入一次心跳")
    beat.add_argument("name")
    beat.add_argument("--note", default=None)
    beat.add_argument("--json", action="store_true")

    check = subparsers.add_parser("check", help="检查心跳是否新鲜")
    check.add_argument("name")
    check.add_argument("--max-age", type=float, required=True, dest="max_age")
    check.add_argument("--json", action="store_true")

    path_command = subparsers.add_parser("path", help="打印心跳文件路径")
    path_command.add_argument("name")

    listing = subparsers.add_parser("list", help="列出目录下所有心跳")
    listing.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    arguments = parse_arguments(argv)
    try:
        if arguments.action == "beat":
            target = write_heartbeat(arguments.name, arguments.dir, note=arguments.note)
            if arguments.json:
                sys.stdout.write(json.dumps({"name": arguments.name, "path": str(target)}, ensure_ascii=False) + "\n")
            else:
                sys.stdout.write(f"心跳已写入 {target}\n")
            return EXIT_OK
        if arguments.action == "check":
            report = inspect(arguments.name, arguments.dir, arguments.max_age)
            if arguments.json:
                sys.stdout.write(json.dumps(report, ensure_ascii=False) + "\n")
            else:
                age = "-" if report["age_seconds"] is None else f"{report['age_seconds']:.0f}s"
                sys.stdout.write(
                    f"{report['status']}  {arguments.name}  age={age}  limit={arguments.max_age:.0f}s  {report['path']}\n"
                )
            return EXIT_OK if report["status"] == STATUS_OK else EXIT_STALE
        if arguments.action == "path":
            sys.stdout.write(str(heartbeat_path(arguments.name, arguments.dir)) + "\n")
            return EXIT_OK
        directory = state_dir(arguments.dir)
        names = sorted(item.stem for item in directory.glob("*.json")) if directory.is_dir() else []
        reports = [inspect(name, arguments.dir) for name in names]
        if arguments.json:
            sys.stdout.write(json.dumps({"directory": str(directory), "heartbeats": reports}, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(f"# {directory}（{len(reports)} 个心跳）\n")
            for report in reports:
                age = "-" if report["age_seconds"] is None else f"{report['age_seconds']:.0f}s"
                sys.stdout.write(f"  {report['name']}  age={age}\n")
        return EXIT_OK
    except ValueError as error:
        sys.stderr.write(f"heartbeat: {error}\n")
        return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
