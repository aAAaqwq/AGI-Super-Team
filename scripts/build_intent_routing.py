#!/usr/bin/env python3
"""Render the intent-routing table into the canonical orchestrator Skill."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "intent-routing.json"
SCHEMA = ROOT / "config" / "intent-routing.schema.json"
TARGET = ROOT / "skills" / "orchestrate-agi-super-team" / "SKILL.md"
BEGIN = "<!-- INTENT-ROUTING:BEGIN -->"
END = "<!-- INTENT-ROUTING:END -->"

LABELS = {
    "ceo": "CEO",
    "cto": "CTO",
    "pe": "PE",
    "cpo": "CPO",
    "cqo": "CQO",
    "cmo": "CMO",
    "cfo": "CFO",
    "cdo": "CDO",
    "cco": "CCO",
    "clo": "CLO",
    "cro": "CRO",
    "cso": "CSO",
    "coo": "COO",
    "governor": "Governor",
}


def role(agent_id: str) -> str:
    return f"{LABELS[agent_id]}（`{agent_id}`）"


def render() -> str:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    rows = []
    for route in config["routes"]:
        supporting = "、".join(LABELS[item] for item in route["supporting"]) or "—"
        rows.append(
            f"| {route['intent']} | {role(route['primary'])} | {supporting} | "
            f"{'、'.join(route['keywords'])} |"
        )
    escalation = config["escalation"]
    when = "\n".join(f"- {item}" for item in escalation["when"])
    return "\n".join(
        [
            BEGIN,
            "先按任务意图选主责 C-suite，再决定是否需要协作角色。",
            "",
            "| 意图信号 | 主责 | 可协作 | 典型关键词 |",
            "|---|---|---|---|",
            *rows,
            "",
            f"**升级到 {role(escalation['primary'])} 的条件**（任一满足才升级）：",
            "",
            when,
            "",
            f"**兜底**：{config['fallback']}",
            END,
        ]
    )


def main() -> int:
    if not SCHEMA.is_file():
        print(f"missing schema: {SCHEMA}", file=sys.stderr)
        return 1
    text = TARGET.read_text(encoding="utf-8")
    start = text.find(BEGIN)
    finish = text.find(END)
    if start < 0 or finish < start:
        print(f"missing intent-routing markers in {TARGET}", file=sys.stderr)
        return 1
    rendered = render()
    updated = text[:start] + rendered + text[finish + len(END):]
    if "--check" in sys.argv:
        if updated != text:
            print(f"intent routing is stale: {TARGET}", file=sys.stderr)
            return 1
        print("Intent routing is current")
        return 0
    TARGET.write_text(updated, encoding="utf-8")
    print(f"Wrote {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
