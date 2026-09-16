# 🔌 Distributions

This directory holds curated package implementations. Root-level harness manifests are entry points and
may describe a different scope.

| Distribution | Manifest | Scope | Evidence boundary |
|---|---|---|---|
| [`agi-super-team-codex`](./agi-super-team-codex/) | `.codex-plugin/plugin.json` | Curated Codex skills and specialist roles | Repository structure tested; current-client load receipt pending |

## Where do the other harnesses come from?

They are reached through the **generic installer**, which is the primary onboarding route for every
harness. There is one published package — `agi-super-team` on npm with the
`bin/agi-super-team.mjs` entry point:

```bash
npx -y agi-super-team@latest --tool <id>            # preview
npx -y agi-super-team@latest --tool <id> --install  # apply
```

That route covers Claude Code, Codex, OpenClaw, and Hermes, plus the 14 further CLI targets declared in
[`config/cli-adapters.json`](../config/cli-adapters.json). It does not need a `plugins/` directory.

## Why there is only one package

A `plugins/<name>/` package is a **secondary discovery path** for users who install through a harness's
own plugin UI. It is only useful when the package ships real components.

A package cannot reference canonical content by reference. Measured against `claude` 2.1.207 and `npm`
11.6.2:

| Route | Result |
|---|---|
| `"skills": "../../skills"` inside a package | `✘ Path contains ".." which could be a path traversal attempt` |
| `skills` as a symlink to canonical `skills/` | `✘ Path not found: ./skills` |
| Symlink surviving an npm tarball | `npm pack` drops symlinked directories entirely |

A wrapper that carries no content installs nothing, so packages without components were removed rather
than kept as placeholders. See
[ADR-0006](../docs/adr/0006-one-command-onboarding.md) for the decision and the coverage
matrix across the five primary harnesses.

Use [.codex/INDEX.md](../.codex/INDEX.md) as the human-facing Codex installation guide. Do not infer
feature parity from manifest presence, and do not treat a passing validator as a runtime receipt.
