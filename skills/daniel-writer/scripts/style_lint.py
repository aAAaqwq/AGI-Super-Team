#!/usr/bin/env python3
"""对 Daniel 写作草稿执行保守的语言检查。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


PATTERNS = {
    "通用化开头": [
        r"在当今.{0,20}时代",
        r"随着.{0,20}(发展|进步)",
    ],
    "报告式语言": [
        r"综上所述",
        r"值得注意的是",
        r"不难发现",
        r"降本增效",
        r"赋能",
    ],
    "能力夸大": [
        r"一键(生成|出片|完成)",
        r"全自动",
        r"完美",
        r"必爆",
        r"百分之百",
        r"手机上(终于|已经).{0,8}(好读|读得顺)",
    ],
    "未经测量的收益": [
        r"(节省|省下|降低).{0,10}(时间|成本|返工)",
        r"效率提升\s*\d+%",
        r"最(费|省).{0,8}(时间|成本)",
    ],
    "绝对归因": [
        r"问题(才|就|已经|彻底)?(消失|解决)",
        r"问题根本不在",
    ],
    "Agent越权": [
        r"Agent.{0,12}(自动完成|替我完成|全权负责|预测成功)",
    ],
}

NEGATION_RE = re.compile(r"不|没有|未|不能|不得|并非|不是|避免|禁止")


def is_negated(text: str, start: int, end: int) -> bool:
    """忽略被明确否定或禁止的能力表述。"""
    prefix = text[max(0, start - 12) : start]
    direct_negation = re.compile(
        r"(?:不|没有|未|不能|不得|并非|不是|避免|禁止)"
        r"(?:再|要|会|能|可|应|该|宣称|声称|写成|描述为)?"
        r"[\s“”\"：:，,]*$"
    )
    matched_text = text[start:end]
    negation_inside_match = re.compile(
        r"(?:不|没有|未|不能|不得|并非|不是|避免|禁止)"
        r"(?:再|要|会|能|可|应|该|宣称|声称|写成|描述为)?"
        r"[\s“”\"：:，,]*"
        r"(?:一键|全自动|完美|必爆|百分之百|手机上|自动完成|替我完成|全权负责|预测成功)"
    )
    return bool(direct_negation.search(prefix) or negation_inside_match.search(matched_text))


def lint(text: str) -> dict[str, list[dict[str, object]]]:
    findings: dict[str, list[dict[str, object]]] = {}
    for category, patterns in PATTERNS.items():
        hits = []
        for pattern in patterns:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                if category in {"能力夸大", "Agent越权"} and is_negated(
                    text, match.start(), match.end()
                ):
                    continue
                line = text.count("\n", 0, match.start()) + 1
                hits.append({"line": line, "text": match.group(0), "pattern": pattern})
        if hits:
            findings[category] = hits
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", help="需要检查的 UTF-8 草稿文件")
    args = parser.parse_args()
    path = Path(args.file)
    findings = lint(path.read_text(encoding="utf-8"))
    print(json.dumps({"文件": str(path), "问题": findings}, ensure_ascii=False, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
