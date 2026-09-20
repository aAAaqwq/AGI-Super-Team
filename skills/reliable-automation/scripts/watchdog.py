#!/usr/bin/env python3
"""按声明式注册表检查"该发生但没发生"的任务。

服务对象是自动运转的 agent 团队：定时/事件触发的任务跑了没有、跑成功没有。

核心洞察：进程活着 != 在工作，run 结束 != 有产出。所以这里不查 PID，也不读任务
自己的"我成功了"声明，只查"最后一次成功产出"的时间——产物文件的 mtime
（kind=artifact）、心跳文件里的时间戳（kind=heartbeat），或者一条命令的退出码
（kind=command）。

"持久稳定" != "不失败"，= 失败了你知道。这个脚本负责"知道"那一步。

退出码：
    0  全部健康
    1  存在任何异常（含 config-error；launchd/cron 可直接判读）
    2  命令行用法错误（注册表文件本身读不到也归 1，见下）

只用标准库，兼容 Python 3.10+。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
EXIT_HEALTHY = 0
EXIT_ANOMALY = 1
EXIT_USAGE = 2

STATUS_OK = "ok"
STATUS_STALE = "stale"
STATUS_EMPTY = "empty"
STATUS_CONFIG_ERROR = "config-error"
STATUS_FAILED = "failed"

ANOMALY_STATUSES = (STATUS_STALE, STATUS_EMPTY, STATUS_CONFIG_ERROR, STATUS_FAILED)
SUPPORTED_KINDS = ("artifact", "heartbeat", "command")
DEFAULT_ON_MISSING = "config-error"
DEFAULT_TS_FIELD = "ts"
DEFAULT_TIMEOUT_SECONDS = 30.0
MILLISECONDS_THRESHOLD = 1e11
DETAIL_COLUMN_WIDTH = 60

CATEGORY_LABELS = {
    STATUS_OK: "healthy",
    STATUS_STALE: "stale",
    STATUS_EMPTY: "empty",
    STATUS_CONFIG_ERROR: "config-error",
    STATUS_FAILED: "failed",
}


# --------------------------------------------------------------------------- #
# 基础工具
# --------------------------------------------------------------------------- #
def expand_path(raw: object) -> Path | None:
    """展开 ~ 并把注册表里的字符串变成 Path；不是字符串就返回 None。"""

    if not isinstance(raw, str) or not raw.strip():
        return None
    return Path(os.path.expanduser(raw.strip()))


def parse_timestamp(value: object) -> float | None:
    """把 epoch 秒 / epoch 毫秒 / 数字字符串 / ISO8601 文本统一成 epoch 秒。"""

    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            number = float(text)
        except ValueError:
            return _parse_iso8601(text)
    else:
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number / 1000.0 if abs(number) >= MILLISECONDS_THRESHOLD else number


def _parse_iso8601(text: str) -> float | None:
    candidate = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _display_width(text: str) -> int:
    return sum(2 if unicodedata.east_asian_width(char) in "WF" else 1 for char in text)


def _pad(text: str, width: int) -> str:
    return text + " " * max(0, width - _display_width(text))


def _truncate(text: str, limit: int) -> str:
    """按显示宽度截断（CJK 算 2 列），只影响表格；--json 与 --verbose 给全文。"""

    if _display_width(text) <= limit:
        return text
    kept = []
    width = 0
    for char in text:
        char_width = 2 if unicodedata.east_asian_width(char) in "WF" else 1
        if width + char_width > limit - 1:
            break
        kept.append(char)
        width += char_width
    return "".join(kept) + "…"


def _duration(seconds: float | None) -> str:
    if seconds is None:
        return "-"
    if seconds < 0:
        seconds = 0.0
    if seconds < 90:
        return f"{seconds:.0f}s"
    if seconds < 5400:
        return f"{seconds / 60:.1f}m"
    return f"{seconds / 3600:.1f}h"


# --------------------------------------------------------------------------- #
# 注册表加载
# --------------------------------------------------------------------------- #
def load_registry(path: Path) -> tuple[list[object], str | None]:
    """读注册表。读不到/坏 JSON 都不抛异常，返回 (entries, error)。"""

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as error:
        return [], f"注册表不可读：{path}（{error.strerror or error}）"
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as error:
        return [], f"注册表不是合法 JSON：{path}（第 {error.lineno} 行 {error.msg}）"
    if not isinstance(document, dict):
        return [], f"注册表顶层必须是 JSON 对象：{path}"
    tasks = document.get("tasks")
    if not isinstance(tasks, list):
        return [], f"注册表缺少 tasks 数组：{path}"
    return list(tasks), None


def _base_result(name: str, entry: dict, target: str, now: float) -> dict:
    severity = entry.get("severity")
    return {
        "name": name,
        "kind": entry.get("kind"),
        "target": target,
        "severity": severity if isinstance(severity, str) and severity.strip() else "medium",
        "status": STATUS_OK,
        "age_seconds": None,
        "max_age_seconds": None,
        "checked_at": _iso(now),
        "detail": "",
        "note": entry.get("note") if isinstance(entry.get("note"), str) else "",
    }


def _config_error(result: dict, detail: str) -> dict:
    result["status"] = STATUS_CONFIG_ERROR
    result["detail"] = detail
    return result


def _positive_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if number != number or number <= 0:
        return None
    return number


def _non_negative_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if number != number or number < 0:
        return None
    return number


# --------------------------------------------------------------------------- #
# 单任务评估
# --------------------------------------------------------------------------- #
def evaluate_task(
    entry: object,
    index: int,
    now: float,
    runner=None,
) -> dict:
    """评估一个注册表条目，永远返回结果字典，不抛异常。"""

    if not isinstance(entry, dict):
        return {
            "name": f"<entry #{index}>",
            "kind": None,
            "target": "",
            "severity": "medium",
            "status": STATUS_CONFIG_ERROR,
            "age_seconds": None,
            "max_age_seconds": None,
            "checked_at": _iso(now),
            "detail": "注册表条目必须是 JSON 对象",
            "note": "",
        }

    raw_name = entry.get("name")
    name = raw_name.strip() if isinstance(raw_name, str) and raw_name.strip() else f"<entry #{index}>"
    kind = entry.get("kind")
    target = ""
    result = _base_result(name, entry, target, now)

    if kind not in SUPPORTED_KINDS:
        return _config_error(result, f"kind 必须是 {'/'.join(SUPPORTED_KINDS)} 之一，实际为 {kind!r}")

    if kind == "command":
        command = entry.get("command")
        if isinstance(command, list) and command and all(isinstance(item, str) for item in command):
            target = " ".join(command)
        elif isinstance(command, str) and command.strip():
            target = command.strip()
        else:
            return _config_error(result, "command 必须是非空字符串或字符串数组")
        result["target"] = target
        return _evaluate_command(result, entry, command, now, runner)

    path = expand_path(entry.get("path"))
    if path is None:
        return _config_error(result, "path 必须是非空字符串")
    result["target"] = str(path)
    max_age = _positive_number(entry.get("max_age_seconds"))
    if max_age is None:
        return _config_error(result, "max_age_seconds 必须是正数")
    result["max_age_seconds"] = max_age

    on_missing = entry.get("on_missing", DEFAULT_ON_MISSING)
    if on_missing not in (DEFAULT_ON_MISSING, STATUS_STALE):
        return _config_error(result, "on_missing 只能是 'config-error' 或 'stale'")

    try:
        stat = path.stat()
    except OSError as error:
        if on_missing == STATUS_STALE:
            result["status"] = STATUS_STALE
            result["detail"] = f"产物不存在（{error.strerror or error}），且该任务声明缺失即故障"
            return result
        return _config_error(
            result,
            f"注册表指向的路径不存在：{path}（{error.strerror or error}）——"
            "这是配置错误，不是任务故障；请确认路径或先创建产物",
        )
    if path.is_dir():
        return _config_error(result, f"注册表指向的是目录而不是产物文件：{path}")

    if kind == "artifact":
        return _evaluate_artifact(result, entry, path, stat, now, max_age)
    return _evaluate_heartbeat(result, entry, path, now, max_age)


def _evaluate_artifact(result: dict, entry: dict, path: Path, stat, now: float, max_age: float) -> dict:
    result["age_seconds"] = round(max(0.0, now - stat.st_mtime), 3)
    min_bytes = entry.get("min_bytes")
    if min_bytes is not None:
        expected_bytes = _non_negative_number(min_bytes)
        if expected_bytes is None:
            return _config_error(result, "min_bytes 必须是非负数")
        if stat.st_size < expected_bytes:
            result["status"] = STATUS_EMPTY
            result["detail"] = f"产物只有 {stat.st_size} 字节，小于要求的 {expected_bytes:.0f} 字节"
            return result
    if result["age_seconds"] > max_age:
        result["status"] = STATUS_STALE
        result["detail"] = (
            f"最后一次写入在 {_duration(result['age_seconds'])} 前，超过上限 {_duration(max_age)}"
        )
        return result
    result["detail"] = f"最后写入距今 {_duration(result['age_seconds'])}"
    return result


def _evaluate_heartbeat(result: dict, entry: dict, path: Path, now: float, max_age: float) -> dict:
    ts_field = entry.get("ts_field", DEFAULT_TS_FIELD)
    if not isinstance(ts_field, str) or not ts_field.strip():
        return _config_error(result, "ts_field 必须是非空字符串")
    ts_field = ts_field.strip()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        return _config_error(result, f"心跳文件不可读：{path}（{error.strerror or error}）")
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        return _config_error(result, f"心跳文件不是合法 JSON：{path}（{error}）")
    if not isinstance(payload, dict):
        return _config_error(result, f"心跳文件顶层必须是 JSON 对象：{path}")
    stamp = parse_timestamp(payload.get(ts_field))
    if stamp is None:
        return _config_error(
            result, f"心跳文件缺少可解析的 {ts_field!r} 时间戳：{path}（当前值 {payload.get(ts_field)!r}）"
        )
    result["heartbeat_at"] = _iso(stamp)
    result["age_seconds"] = round(max(0.0, now - stamp), 3)
    if result["age_seconds"] > max_age:
        result["status"] = STATUS_STALE
        result["detail"] = (
            f"距上次心跳 {_duration(result['age_seconds'])}，超过上限 {_duration(max_age)}"
        )
        return result
    result["detail"] = f"心跳距今 {_duration(result['age_seconds'])}"
    return result


def _evaluate_command(result: dict, entry: dict, command: object, now: float, runner) -> dict:
    timeout = _positive_number(entry.get("timeout_seconds")) or DEFAULT_TIMEOUT_SECONDS
    result["max_age_seconds"] = timeout
    shell = isinstance(command, str)
    argv = command if shell else list(command)
    run = subprocess.run if runner is None else runner
    started = time.monotonic()
    try:
        completed = run(
            argv,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        result["status"] = STATUS_FAILED
        result["detail"] = f"命令在 {_duration(timeout)} 内没有结束"
        return result
    except OSError as error:
        result["status"] = STATUS_FAILED
        result["detail"] = f"命令无法执行：{error}"
        return result
    elapsed = time.monotonic() - started
    if completed.returncode == 0:
        result["detail"] = f"退出码 0，耗时 {elapsed:.2f}s"
        return result
    stderr = (completed.stderr or "").strip().splitlines()
    tail = stderr[-1][:200] if stderr else "无 stderr 输出"
    result["status"] = STATUS_FAILED
    result["detail"] = f"退出码 {completed.returncode}，耗时 {elapsed:.2f}s；stderr 末行：{tail}"
    return result


# --------------------------------------------------------------------------- #
# 汇总与输出
# --------------------------------------------------------------------------- #
def summarize(results: list[dict]) -> dict:
    counts = {status: 0 for status in CATEGORY_LABELS}
    for result in results:
        status = result.get("status", STATUS_CONFIG_ERROR)
        counts[status] = counts.get(status, 0) + 1
    anomalies = [result for result in results if result.get("status") in ANOMALY_STATUSES]
    return {
        "total": len(results),
        "anomalies": len(anomalies),
        "byStatus": counts,
        "counts": {CATEGORY_LABELS[status]: counts[status] for status in CATEGORY_LABELS},
    }


def render_table(results: list[dict], summary: dict, registry: Path) -> str:
    headers = ("TASK", "KIND", "STATUS", "AGE", "LIMIT", "SEVERITY", "DETAIL")
    rows = []
    for result in results:
        rows.append(
            (
                str(result.get("name", "")),
                str(result.get("kind") or "-"),
                str(result.get("status", "")),
                _duration(result.get("age_seconds")),
                _duration(result.get("max_age_seconds")),
                str(result.get("severity", "")),
                _truncate(str(result.get("detail", "")), DETAIL_COLUMN_WIDTH),
            )
        )
    widths = [len(header) for header in headers]
    for row in rows:
        for position, cell in enumerate(row):
            widths[position] = max(widths[position], _display_width(cell))
    lines = [
        f"# reliable-automation watchdog — {registry}",
        f"# {_iso(time.time())}  共 {summary['total']} 项，异常 {summary['anomalies']} 项",
        "",
        "  ".join(_pad(header, widths[index]) for index, header in enumerate(headers)).rstrip(),
        "  ".join("-" * width for width in widths),
    ]
    for row in rows:
        lines.append("  ".join(_pad(cell, widths[index]) for index, cell in enumerate(row)).rstrip())
    lines.append("")
    lines.append(
        "  合计："
        + "，".join(
            f"{label}={summary['counts'][label]}"
            for label in ("healthy", "stale", "empty", "config-error", "failed")
        )
    )
    lines.append("  提示：config-error 表示注册表与磁盘现实不符（配置问题），不是任务故障；")
    lines.append("        其余异常才说明任务该产出而没产出。")
    return "\n".join(lines) + "\n"


def build_alert_message(results: list[dict], summary: dict, registry: Path) -> str:
    lines = [
        f"[watchdog] {summary['anomalies']} 项异常 / 共 {summary['total']} 项",
        f"注册表：{registry}",
    ]
    for result in results:
        if result.get("status") not in ANOMALY_STATUSES:
            continue
        lines.append(
            f"- {result.get('name')} [{result.get('kind')}/{result.get('severity')}] "
            f"{result.get('status')}：{result.get('detail')}"
        )
    return "\n".join(lines) + "\n"


def dispatch_alert(command: str, message: str, timeout: float) -> tuple[bool, str]:
    """执行告警命令：{msg} 会被替换，同时告警全文从 stdin 传入。"""

    expanded = command.replace("{msg}", message.strip())
    try:
        completed = subprocess.run(
            expanded,
            shell=True,
            input=message,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, f"告警命令在 {_duration(timeout)} 内没有结束"
    except OSError as error:
        return False, f"告警命令无法执行：{error}"
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip().splitlines()
        tail = stderr[-1][:200] if stderr else "无 stderr 输出"
        return False, f"告警命令退出码 {completed.returncode}；stderr 末行：{tail}"
    output = (completed.stdout or "").strip()
    return True, f"告警命令已执行{('：' + output.splitlines()[-1][:200]) if output else ''}"


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("watchdog.registry.json"),
        help="声明式注册表 JSON（默认：当前目录的 watchdog.registry.json）",
    )
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    parser.add_argument(
        "--alert-cmd",
        default=None,
        help="有异常时执行的 shell 命令；{msg} 会被替换，告警全文同时从 stdin 传入。默认不推送。",
    )
    parser.add_argument(
        "--alert-timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"告警命令超时秒数（默认 {DEFAULT_TIMEOUT_SECONDS:.0f}）",
    )
    parser.add_argument("--verbose", action="store_true", help="表格后附上每项的 note")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    arguments = parse_arguments(argv)
    registry = arguments.registry
    entries, error = load_registry(registry)
    now = time.time()

    if error is not None:
        if arguments.json:
            sys.stdout.write(
                json.dumps(
                    {
                        "schemaVersion": SCHEMA_VERSION,
                        "registry": str(registry),
                        "summary": {"total": 0, "anomalies": 1, "byStatus": {}, "counts": {}},
                        "results": [],
                        "error": error,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n"
            )
        else:
            sys.stderr.write(f"watchdog: {error}\n")
        return EXIT_ANOMALY

    results = [evaluate_task(entry, index, now) for index, entry in enumerate(entries)]
    summary = summarize(results)

    if arguments.json:
        sys.stdout.write(
            json.dumps(
                {
                    "schemaVersion": SCHEMA_VERSION,
                    "registry": str(registry),
                    "checkedAt": _iso(now),
                    "summary": summary,
                    "results": results,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )
    else:
        sys.stdout.write(render_table(results, summary, registry))
        if arguments.verbose:
            for result in results:
                sys.stdout.write(f"    {result['name']}: {result['detail']}\n")
                if result.get("note"):
                    sys.stdout.write(f"        note: {result['note']}\n")

    if arguments.alert_cmd and summary["anomalies"]:
        message = build_alert_message(results, summary, registry)
        if "{msg}" not in arguments.alert_cmd:
            sys.stderr.write("watchdog: --alert-cmd 里没有 {msg} 占位符，告警全文将只通过 stdin 传入\n")
        delivered, detail = dispatch_alert(arguments.alert_cmd, message, arguments.alert_timeout)
        if not arguments.json:
            sys.stdout.write(f"  {'告警' if delivered else '告警失败'}：{detail}\n")
        if not delivered:
            return EXIT_ANOMALY

    return EXIT_ANOMALY if summary["anomalies"] else EXIT_HEALTHY


if __name__ == "__main__":
    raise SystemExit(main())
