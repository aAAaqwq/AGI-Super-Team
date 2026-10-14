#!/usr/bin/env python3
"""验证内容工作包的 manifest、交付文件和证据引用一致性。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


EVIDENCE_PATTERN = re.compile(r"\bE-\d{3,}\b")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"文件不存在: {path.name}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 无效: {path.name}: {exc.msg}") from None
    if not isinstance(data, dict):
        raise ValueError(f"JSON 顶层必须是对象: {path.name}")
    return data


def is_within(base: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(base)
    except ValueError:
        return False
    return True


def validate_package(package: Path) -> list[str]:
    errors: list[str] = []
    package = package.resolve()

    try:
        manifest = load_json(package / "manifest.json")
    except (OSError, ValueError) as exc:
        return [str(exc)]

    evidence_path = package / "01-evidence-ledger.md"
    try:
        evidence_text = evidence_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ["文件不存在: 01-evidence-ledger.md"]
    except OSError as exc:
        return [f"无法读取证据账本: {exc}"]

    known_evidence = set(EVIDENCE_PATTERN.findall(evidence_text))
    if not known_evidence:
        errors.append("证据账本没有可识别的证据 ID")

    deliverables = manifest.get("deliverables")
    if not isinstance(deliverables, list) or not deliverables:
        errors.append("manifest.deliverables 必须是非空数组")
        return errors

    seen_paths: set[str] = set()
    for index, item in enumerate(deliverables, start=1):
        if not isinstance(item, dict):
            errors.append(f"第 {index} 个交付项必须是对象")
            continue

        relative_path = item.get("path")
        if not isinstance(relative_path, str) or not relative_path.strip():
            errors.append(f"第 {index} 个交付项缺少 path")
            continue
        if relative_path in seen_paths:
            errors.append(f"交付路径重复: {relative_path}")
            continue
        seen_paths.add(relative_path)

        deliverable_path = (package / relative_path).resolve()
        if not is_within(package, deliverable_path):
            errors.append(f"交付路径越界: {relative_path}")
            continue
        if not deliverable_path.is_file():
            errors.append(f"交付文件不存在: {relative_path}")
            continue

        try:
            deliverable_text = deliverable_path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"无法读取交付文件 {relative_path}: {exc}")
            continue

        referenced = set(EVIDENCE_PATTERN.findall(deliverable_text))
        for evidence_id in sorted(referenced - known_evidence):
            errors.append(f"{relative_path} 引用了未知证据 ID: {evidence_id}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package_dir", type=Path, help="内容工作包目录")
    args = parser.parse_args()

    errors = validate_package(args.package_dir)
    if errors:
        for error in errors:
            print(f"错误: {error}", file=sys.stderr)
        return 2

    print(f"验证通过: {args.package_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
