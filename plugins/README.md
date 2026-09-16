# 🔌 Distributions

This directory holds curated package implementations. Root-level harness manifests are entry points and
may describe a different scope.

| Distribution | Manifest | Scope | Ships | Evidence boundary |
|---|---|---|---|---|
| [`agi-super-team-codex`](./agi-super-team-codex/) | `.codex-plugin/plugin.json` | Curated Codex skills and specialist roles | 6 Skills + 136 agent TOMLs | Repository structure tested; current-client load receipt pending |
| [`agi-super-team-claudecode`](./agi-super-team-claudecode/) | `.claude-plugin/plugin.json` | Claude Code subagents and the orchestrator Skill | 14 agent definitions + connection spec | Repository structure tested; current-client load receipt pending |
| [`agi-super-team-hermes`](./agi-super-team-hermes/) | `plugin.json` | Hermes role Skills and Profile blueprints | 14 role Skills + 14 blueprints + connection spec | Repository structure tested; no Kanban canary |
| [`agi-super-team-dsh`](./agi-super-team-dsh/) | `dsh-plugin.json` | DSH instruction chain, profile patch, and agent preset | 19 files across three composition layers | Repository structure tested; no preset canary |
| [`agi-super-team-openclaw`](./agi-super-team-openclaw/) | `openclaw.plugin.json` | OpenClaw role workspaces and the `agents.list` patch | 84 workspace files + connection spec | Repository structure tested; no dispatch canary |

Each package is **generated**, and ships only its harness's layer. The four per-harness packages are
produced by `scripts/build_<harness>_package.py`, which reads its bytes from that harness's own adapter
(`bin/adapters/<harness>.mjs`) through `scripts/util/render_harness_artifacts.mjs`. There is one renderer
per harness, and each `tests/test_<harness>_package.py` asserts with `--check` that the checked-in bytes
still match it.

## Why the packages ship no Skills

A curated package cannot reference canonical content by relative path: Claude Code rejects `..` in a
component path, a symlinked `skills/` is not followed, and `npm pack` drops symlinked directories
entirely. Measured against `claude` 2.1.207 and `npm` 11.6.2:

| Route | Result |
|---|---|
| `"skills": "../../skills"` inside a package | `✘ Path contains ".." which could be a path traversal attempt` |
| `skills` as a symlink to canonical `skills/` | `✘ Path not found: ./skills` |
| Symlink surviving an npm tarball | `npm pack` drops symlinked directories entirely |

So the only way to ship Skills would be to copy them — 495 to 509 Skill directories, roughly 68 MB, into
each package and four times over. That is canonical source duplicated to satisfy a harness layout, which
[ADR-0002](../docs/adr/0002-generic-workspace-and-curated-distributions.md) rules out.

Each package therefore ships its harness-specific layer and leaves the Skill bodies to the **generic
installer**, which vendors them from the single `skills/` root. Every package README says so, and each
package's test asserts that no canonical Skill body was vendored.

The one Skill a package does carry is its generated orchestrator entry point
(`agi-super-team-orchestrator`). The adapter produces it rather than copying it, and without it the
package has nothing to trigger on.

## The generic installer is still the primary route

```bash
npx -y agi-super-team@latest --tool <id>            # preview
npx -y agi-super-team@latest --tool <id> --install  # apply
```

That one published npm package covers Claude Code, Codex, OpenClaw, Hermes, and DSH, plus the 14 further
CLI targets declared in [`config/cli-adapters.json`](../config/cli-adapters.json), and it is the only
route that also vendors the Skill bodies. A `plugins/<name>/` package is a **secondary discovery path**
for users who install through a harness's own plugin UI.

A wrapper that carries no content installs nothing, so packages without components are removed rather
than kept as placeholders. See
[ADR-0006](../docs/adr/0006-one-command-onboarding.md) for that decision.

Use [.codex/INDEX.md](../.codex/INDEX.md) as the human-facing Codex installation guide. Do not infer
feature parity from manifest presence, and do not treat a passing validator as a runtime receipt.
