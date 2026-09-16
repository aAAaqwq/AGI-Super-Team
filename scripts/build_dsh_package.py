#!/usr/bin/env python3
"""Build the curated DSH package at ``plugins/agi-super-team-dsh``.

DSH does not model a role as one file. Three mechanisms carry what an "Agent"
means: the global instruction chain (``AGENTS.md``), the profile patch layer
(``profiles/<profile>/cordis.patch.yml``), and the agent-plane preset
(``.agent-presets/ast-team/``). This package carries all three, plus the
orchestrator Skill and the connection spec.

Bytes come from ``bin/adapters/dsh.mjs`` via
``scripts/util/render_harness_artifacts.mjs``. Nothing is re-rendered here.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_harness_packages import HarnessPackage, main  # noqa: E402


PACKAGE = HarnessPackage(
    harness="dsh",
    package="agi-super-team-dsh",
    manifest_relative="dsh-plugin.json",
    connection_relative="agi-super-team/connection.json",
    # DSH distributes a plugin as an npm package whose manifest declares
    # `dsh.bundle.patch` pointing at a `cordis.patch.yml` layer. This package is
    # that layer, checked in, so a consumer can read it before running anything.
    #
    # The shape follows the published DSH plugin format exactly:
    #   {"dsh": {"bundle": {"patch": "./cordis.patch.yml"}}}
    # There is deliberately no `$schema`, no `main`, and no `type`: the format
    # documents none of those for a pure bundle package, and inventing a schema
    # URL would point readers at a file that does not exist. The preset and the
    # global instruction path are not manifest contract keys either, so they are
    # documented in `README.md` and `agi-super-team/connection.json` rather than
    # smuggled in as unofficial fields.
    #
    # This file is not an install input for the repository's own installer --
    # `bin/adapters/dsh.mjs` already writes the patch layer directly. It exists
    # so this directory is a valid DSH plugin on its own, for a user who
    # publishes it as one.
    manifest="""{
  "name": "agi-super-team-dsh",
  "version": "@@VERSION@@",
  "description": "Evidence-backed AI team packs with preview-first installation and explicit human review",
  "files": [
    "AGENTS.md",
    "README.md",
    "profiles",
    ".agent-presets",
    "skills",
    "agi-super-team"
  ],
  "dsh": {
    "bundle": {
      "patch": "./profiles/web/cordis.patch.yml"
    }
  },
  "author": {
    "name": "Daniel Li",
    "url": "https://github.com/aAAaqwq/AGI-Super-Team"
  }
}
""",
    readme="""# AGI Super Team for DSH

This package carries the **DSH-specific layer** only. It intentionally does not
ship a copy of the canonical `skills/` tree.

## Install

DSH installs a plugin per profile:

```bash
dsh plugin --profile web add <this-package>
```

Or reach the same roles through the generic installer, which is the primary
route and also vendors the canonical Skill bodies:

```bash
npx -y agi-super-team@latest --tool dsh            # preview
npx -y agi-super-team@latest --tool dsh --install  # apply
```

## What is inside, and why it takes three mechanisms

DSH composes a session from an agent preset, and `dsh-web-app` disables the
host `skill-filesystem` row. No single mechanism carries a role, so all three
are needed:

| Path | What it is | Why it is needed |
|---|---|---|
| `dsh-plugin.json` | the plugin manifest | declares `dsh.bundle.patch` so DSH knows which file is the patch layer |
| `AGENTS.md` | the user-global instruction chain | the only place a session is guaranteed to look before the project tree. **Advisory only** -- it carries the CEO contract, never a capability |
| `profiles/web/cordis.patch.yml` | the declarative user patch layer | re-enables the host `skill-filesystem` row and points `customSkillDirs` at this repository's `skills/`. This is the **only** way Skills on disk become reachable |
| `.agent-presets/ast-team/agent.cordis.yml` | the agent-plane composition | where tools and prompt sections are composed, so role routing and delegation live here |
| `.agent-presets/ast-team/agents/<role>/AGENTS.md` | the canonical role bodies | DSH has no per-role file directory, so the role instructions land as workspace instructions inside the preset |
| `skills/agi-super-team/agi-super-team-orchestrator/SKILL.md` | the entry Skill | decides whether to assemble a team |
| `agi-super-team/connection.json` | the connection spec | `presetMap`, skill-discovery wiring, and the documented limitations |

## Registering the preset

The preset (`.agent-presets/ast-team`) is what actually composes a role, but it
is **not** a manifest field. DSH composes a session from exactly one preset and
a running session can only switch while it has produced nothing, so selecting
`ast-team` is a user action. `agi-super-team/connection.json` records that as
`activation.presetMustBeSelectedByUser`, alongside `activation.requiresProfilePatch`
and the patch target profile.

## Two things that will bite you

**The patch file is never merged into.** A `cordis.patch.yml` is a single YAML
document holding a top-level array, so there is no safe append: the shipped
profile template already ends in `[]`, and appending after it produces a file
DSH refuses to parse. The installer therefore overwrites the file **only** when
it holds no real entries, and leaves it completely alone otherwise. If you have
your own entries in that patch, this package's patch will not be applied.

**The patch targets the `web` profile.** `$DSH_PROFILE` is the documented way to
pin a profile; without it the adapter uses `web`, the profile `dsh web` boots.
The generated files here assume that default. Set `DSH_PROFILE` before running
the installer if you use a different profile, or the patch will land in the
wrong profile's directory.

## Limitations the adapter itself documents

- DSH exposes no per-role tool or capability boundary. Every `ast-*` role
  composes from the same `ast-team` preset, so the C-suite/leaf separation rests
  on the persona routing and the host approval stack, not on the harness.
- The runtime effect of the patch was observed on DSH 0.1.5-rc.1 -- a developer
  preview with breaking changes expected -- and under the headless profile only.

## Why there are no canonical Skills here

A curated package cannot reference canonical content by relative path, so
shipping Skills means copying them: 495 Skill directories into this package,
and again into the three sibling packages. That is canonical source duplicated
four times to satisfy a layout, which
[ADR-0002](../../docs/adr/0002-generic-workspace-and-curated-distributions.md)
rules out. This package ships the harness-specific layer, including the patch
that *points at* the shared Skills root; the installer vendors the bodies.

## Evidence boundary

Package structure is covered by `tests/test_dsh_package.py`, including a
`--check` assertion that the generated bytes still match `bin/adapters/dsh.mjs`.

That proves the package is **structurally** sound and in sync with its renderer.
It does **not** prove a current DSH client loads it. `connection.json` carries
`runtimeEvidence: "pending"` and a `canary` block naming the flow a receipt
would have to demonstrate.
""",
)

if __name__ == "__main__":
    raise SystemExit(main(PACKAGE, __doc__ or ""))
