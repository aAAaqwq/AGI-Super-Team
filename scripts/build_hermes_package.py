#!/usr/bin/env python3
"""Build the curated Hermes package at ``plugins/agi-super-team-hermes``.

Hermes models a role as a Profile plus a role Skill, so this package carries
both halves of that layer: ``skills/agi-super-team-agents/ast-*/SKILL.md`` and
``agi-super-team/profiles/ast-*/profile.json`` blueprints, plus the
orchestrator Skill and the connection spec.

Bytes come from ``bin/adapters/hermes.mjs`` via
``scripts/util/render_harness_artifacts.mjs``. Nothing is re-rendered here.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_harness_packages import HarnessPackage, main  # noqa: E402


PACKAGE = HarnessPackage(
    harness="hermes",
    package="agi-super-team-hermes",
    manifest_relative="plugin.json",
    connection_relative="agi-super-team/connection.json",
    # Hermes installs a portable Agent Plugins package, so this manifest follows
    # Agent Plugins v1.0.0 rather than a Hermes-specific format. Two things are
    # easy to get wrong and are stated explicitly here:
    #
    #   * `$schema` is REQUIRED. It is how a client selects which validation
    #     contract to apply, and an unrecognised value is a fatal rejection
    #     rather than a warning.
    #   * there is no `skills` field. The core schema is closed and declares no
    #     such key; Skills are discovered by fixed location from `skills/`. A
    #     `skills` entry would be an unknown top-level field -- reported and
    #     ignored -- which also suggests a declaration is doing work it is not.
    manifest="""{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
  "name": "agi-super-team-hermes",
  "version": "@@VERSION@@",
  "description": "Evidence-backed AI team packs with preview-first installation and explicit human review",
  "author": {
    "name": "Daniel Li",
    "url": "https://github.com/aAAaqwq/AGI-Super-Team"
  },
  "homepage": "https://github.com/aAAaqwq/AGI-Super-Team",
  "repository": "https://github.com/aAAaqwq/AGI-Super-Team",
  "license": "MIT"
}
""",
    readme="""# AGI Super Team for Hermes

This package carries the **Hermes-specific layer** only: one role Skill per
canonical agent, the matching Profile blueprints, the orchestrator Skill, and
the connection spec. It intentionally does not ship a copy of the canonical
`skills/` tree.

## Install

Hermes installs a portable plugin from a repository:

```bash
hermes plugins install aAAaqwq/AGI-Super-Team --no-enable
hermes plugins list
hermes plugins enable agi-super-team-hermes
```

Installed plugins start **disabled** and must be enabled explicitly; that is
Hermes's design, not a failure signal.

Or reach the same roles through the generic installer, which is the primary
route and also vendors the canonical Skill bodies:

```bash
npx -y agi-super-team@latest --tool hermes            # preview
npx -y agi-super-team@latest --tool hermes --install  # apply
```

## What is inside

| Path | What it is |
|---|---|
| `plugin.json` | the **Agent Plugins v1.0.0** manifest Hermes installs from |
| `skills/agi-super-team-agents/ast-*/SKILL.md` | 14 role Skills, one per canonical agent |
| `agi-super-team/profiles/ast-*/profile.json` | Profile **blueprints** -- see the warning below |
| `skills/agi-super-team-orchestrator/SKILL.md` | the entry Skill that decides whether to assemble a team |
| `agi-super-team/connection.json` | the connection spec: `profileMap`, delegation permissions, Kanban policy |

## The manifest is a portable Agent Plugins manifest

`plugin.json` targets [Agent Plugins](https://agent-plugins.org/specification)
v1.0.0 -- the vendor-neutral portable format Hermes installs, not a
Hermes-proprietary one. Two consequences worth knowing:

- The required `$schema` selects the validation contract. Pointing it at an
  unsupported version makes a client reject the plugin outright, so the value is
  a real compatibility declaration and not decoration. (The plain-text install
  paths above do not enforce it, which is exactly why an unsupported value is
  worth flagging before it reaches a validating client.)
- The core schema is **closed**. It has no `skills` field: skills live at the
  fixed location `skills/`, and a client discovers them there. There is nothing
  to declare.

The format carries no field for `mcp.json`, `hooks`, or `agents` in the core
either; anything client-specific belongs under `extensions.<reverse-domain>`.

## The Profile blueprints are inert

`agi-super-team/profiles/ast-*/profile.json` files are **blueprints, not
Profiles**. Creating a real Hermes Profile, starting a Gateway, or registering a
Cron job is a human decision: every blueprint carries
`blueprintOnly: true`, `runtimeStateCreated: false`, and
`activation.humanReviewRequired: true`, and the adapter performs none of it.

Two further constraints the blueprints encode, both of which surprise people:

- Hermes Profiles use separate `HERMES_HOME` directories and do **not** inherit
  the default profile's Skills. Point `skills.external_dirs` at the shared root
  (`profileSkillVisibility` in the connection spec says where) or the role
  Skills will not be visible.
- Named-profile dispatch goes through Profiles + Kanban. Hermes's `delegate_task`
  does not carry a profile argument; a task card must pin the role Skill in its
  `skills` array, because writing an `assignee` alone does not load the persona.

## Why there are no canonical Skills here

A curated package cannot reference canonical content by relative path, so
shipping Skills means copying them: 509 Skill directories into this package,
and again into the three sibling packages. That is canonical source duplicated
four times to satisfy a layout, which
[ADR-0002](../../docs/adr/0002-generic-workspace-and-curated-distributions.md)
rules out. This package ships the harness-specific layer; the installer vendors
the Skill bodies from the single `skills/` root.

## Evidence boundary

Package structure is covered by `tests/test_hermes_package.py`, including a
`--check` assertion that the generated bytes still match `bin/adapters/hermes.mjs`.

That proves the package is **structurally** sound and in sync with its renderer.
It does **not** prove a current Hermes client loads it, and it is not a Kanban
canary. `connection.json` carries `runtimeEvidence: "pending"` and a `canary`
block naming the flow a receipt would have to demonstrate.
""",
)

if __name__ == "__main__":
    raise SystemExit(main(PACKAGE, __doc__ or ""))
