#!/usr/bin/env python3
"""Build the curated OpenClaw package at ``plugins/agi-super-team-openclaw``.

OpenClaw models an agent as a *workspace bootstrap file set*, not a single
definition file, so this package carries one directory per role
(``<root>/ast-*/{IDENTITY,SOUL,AGENTS,USER,TOOLS,MEMORY}.md``), the orchestrator
Skill, and the connection spec whose `configPatch.agents.list` is what actually
registers the agents.

Bytes come from ``bin/adapters/openclaw.mjs`` via
``scripts/util/render_harness_artifacts.mjs``. Nothing is re-rendered here.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_harness_packages import HarnessPackage, main  # noqa: E402


PACKAGE = HarnessPackage(
    harness="openclaw",
    package="agi-super-team-openclaw",
    manifest_relative="openclaw.plugin.json",
    connection_relative="agi-super-team/connection.json",
    # OpenClaw requires a JSON Schema inline, even when the plugin takes no
    # configuration. An empty schema is legal, so this declares the managed
    # `ast-` block instead of accepting arbitrary keys.
    manifest="""{
  "id": "agi-super-team-openclaw",
  "name": "AGI Super Team",
  "version": "@@VERSION@@",
  "description": "Evidence-backed AI team packs with preview-first installation and explicit human review",
  "configSchema": {
    "type": "object",
    "additionalProperties": false,
    "properties": {
      "managedPrefix": {
        "type": "string",
        "default": "ast-",
        "description": "Only agents whose id starts with this prefix are managed; unmanaged agents are preserved."
      },
      "requiredMaxDepth": {
        "type": "integer",
        "default": 2,
        "description": "Maximum subagent spawn depth for the ast-* team."
      },
      "maxChildrenPerAgent": {
        "type": "integer",
        "default": 2,
        "description": "Maximum concurrent child sessions per ast-* manager."
      }
    }
  }
}
""",
    readme="""# AGI Super Team for OpenClaw

This package carries the **OpenClaw-specific layer** only: one workspace
bootstrap directory per role, the orchestrator Skill, and the connection spec.
It intentionally does not ship a copy of the canonical `skills/` tree.

## Install

Through OpenClaw's plugin CLI:

```bash
openclaw plugins install <this-package>   # path, archive, or npm spec
openclaw plugins list --enabled
openclaw plugins inspect agi-super-team-openclaw
```

Or reach the same roles through the generic installer, which is the primary
route and also vendors the canonical Skill bodies:

```bash
npx -y agi-super-team@latest --tool openclaw            # preview
npx -y agi-super-team@latest --tool openclaw --install  # apply
```

## What is inside

| Path | What it is |
|---|---|
| `openclaw.plugin.json` | the native plugin manifest. OpenClaw requires `id` **and** an inline `configSchema`, even for a plugin that takes no configuration |
| `agency-agents/agi-super-team/ast-*/` | 14 role directories, each holding the bootstrap files that exist for that role (`IDENTITY.md`, `SOUL.md`, `AGENTS.md`, `USER.md`, `TOOLS.md`, `MEMORY.md`) |
| `skills/agi-super-team/agi-super-team-orchestrator/SKILL.md` | the entry Skill that decides whether to assemble a team |
| `agi-super-team/connection.json` | the connection spec, including the `configPatch` that registers the agents |

## The manifest is not the wiring

Installing this package writes the role files. It does **not** register the
agents. Registration is the `agents.list` upsert described in
`agi-super-team/connection.json`'s `configPatch`, and it is deliberately
merge-safe:

| Field | Value | What it means |
|---|---|---|
| `mergeContract.strategy` | `upsert-managed-preserve-unmanaged` | entries are upserted by `id`; anything not prefixed `ast-` is left alone |
| `mergeContract.managedPrefix` | `ast-` | the managed boundary |
| `mergeContract.removeUnmentionedManaged` | `false` | an agent you installed previously is never deleted by a later run |
| `mergeContract.conflictPolicy` | `fail-unless-previewed` | conflicts stop rather than guess |
| `mergeContract.generateBindings` | `false` | no channel bindings are created, so nothing auto-sends to third parties |

Each manager entry carries `subagents.allowAgents` -- the delegation allowlist --
with `requireAgentId: true`, and every leaf carries
`tools.deny: ["sessions_spawn"]` so it cannot delegate. Those are properties of
`configPatch`; a package install that stops at the files leaves them unapplied.

## Compatibility note

OpenClaw auto-detects four bundle formats and reads client-specific markers
(`.codex-plugin/`, `.cursor-plugin/`, `.claude-plugin/`) as those formats. This
package therefore ships only the native `openclaw.plugin.json` and does **not**
also carry a `.claude-plugin/` copy -- a package carrying both would be read
through the client-specific path and the native wiring would be skipped.

## Why there are no canonical Skills here

A curated package cannot reference canonical content by relative path, so
shipping Skills means copying them: 495 Skill directories into this package,
and again into the three sibling packages. That is canonical source duplicated
four times to satisfy a layout, which
[ADR-0002](../../docs/adr/0002-generic-workspace-and-curated-distributions.md)
rules out. This package ships the harness-specific layer; the installer vendors
the Skill bodies from the single `skills/` root.

## Evidence boundary

Package structure is covered by `tests/test_openclaw_package.py`, including a
`--check` assertion that the generated bytes still match
`bin/adapters/openclaw.mjs`.

That proves the package is **structurally** sound and in sync with its renderer.
It does **not** prove a current OpenClaw client loads it. `connection.json`
carries `runtimeEvidence: "pending"` and a `canary` block with the checklist a
receipt would have to pass, including `bindings-unchanged`.
""",
)

if __name__ == "__main__":
    raise SystemExit(main(PACKAGE, __doc__ or ""))
