# ADR-0006: One-command onboarding across primary harnesses

- Status: Accepted
- Date: 2026-09-16

## Context

[ADR-0002](./0002-generic-workspace-and-curated-distributions.md) reserved Adapter consolidation for a
separate decision. This record resolves what consolidation actually serves.

The product goal is a single one-liner that installs the AGI Super Team core experience into any of the
**five primary coding agents**:

> 打包整套 AGI Super Team，让主要 5 类 coding agent 用户快速安装体验到核心功能。

There is **one package**, not five. `package.json` publishes it as `agi-super-team`, and
`bin/agi-super-team.mjs` is the entry point:

```bash
npx -y agi-super-team@latest --tool <id>            # preview
npx -y agi-super-team@latest --tool <id> --install  # apply
```

Marketplace entries and `plugins/` packages are a **secondary discovery path** for users who install
through a harness's own plugin UI. They are not the primary onboarding route.

### What was measured

The earlier hypothesis — five `plugins/agi-super-team-<harness>/` packages, each a thin wrapper around
canonical `skills/` — does not work. All three reference routes were tested against `claude` 2.1.207 and
`npm` 11.6.2:

| Route | Result |
|---|---|
| `"skills": "../../skills"` inside a package | `✘ Path contains ".." which could be a path traversal attempt` |
| `skills` as a symlink to canonical `skills/` | `✘ Path not found: ./skills. The runtime loader will report this as a load failure.` |
| Symlink surviving an npm tarball | `npm pack` drops symlinked directories entirely |

A package that carries no content installs nothing. Four of the five packages built on this hypothesis
ship manifests but no components, so they overstate compatibility — the exact failure ADR-0002 warns
against.

### Coverage measured across the five primary harnesses

| Harness | In CLI targets | Adapter module | Install guide | Marketplace entry |
|---|---|---|---|---|
| Claude Code | yes | yes | yes | yes |
| Codex | yes | yes | yes | yes |
| OpenClaw | yes | yes | **no** | **no** |
| Hermes | yes | yes | **no** | **no** |
| DeepSeek Harness | **no** | **no** | **no** | **no** |

## Decision

**The primary onboarding contract is the `npx` installer targeting the five primary harnesses.** Every
primary harness must be installable through it, and the CLI target list is a project surface that must be
kept in sync.

**`plugins/<name>/` holds a distribution only when it ships real content.** A package that carries no
components is removed rather than kept as a placeholder.

- `agi-super-team-codex` is a real distribution (bundled `payload/` of 136 agent TOMLs plus six curated
  skills) and stays.
- `agi-super-team-claudecode`, `-openclaw`, `-hermes`, and `-deepseek-harness` ship no components and are
  removed. Their harnesses are reached through the installer, which is the primary route anyway.

**Marketplace surface is limited to real distributions.** A marketplace entry pointing at a package that
installs nothing is removed with the package.

**Nested package manifests stay where the harness requires them.** Codex reads
`plugins/<name>/.codex-plugin/plugin.json`; Claude Code reads
`plugins/<name>/.claude-plugin/plugin.json`. These are load-bearing and are not collapsed into a
single package-level file.

### Explicitly rejected

- **Duplicating canonical `skills/` into each package.** It satisfies a harness layout while violating
  ADR-0002, and it is unnecessary: the installer already reaches every primary harness, and it is what
  users actually run.
- **Keeping placeholder packages so the directory "looks consolidated".** Appearance is not a
  distribution. A manifest that installs nothing misleads users into thinking support exists.
- **Treating the marketplace as the primary route.** It serves Claude Code and Codex users who browse a
  plugin UI; it does not serve the other three harnesses at all.

## Consequences

- Onboarding is one command per harness, documented in one place, with the five primary harnesses listed
  together rather than split across per-harness files.
- `plugins/` holds exactly one distribution. Removing the four placeholders restores honesty about what
  is installable without touching canonical `agents/`, `skills/`, or `config/`.
- Closing the remaining coverage gaps is now a tracked deliverable rather than a side effect of
  directory layout: DSH must become a CLI target, and OpenClaw/Hermes/DSH must gain install guides.
- Adding a future real package requires materializing content and adding one marketplace entry; no
  reference mechanism is needed.
- The decision is reversible: `plugins/` can regrow when a package carries real content.
