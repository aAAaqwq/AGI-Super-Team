# 🚀 Start here

This file is a compatibility router. The maintained installation instructions live in the following documents:

| Goal | Canonical guide |
|---|---|
| **Install the team now — fastest path** | [Manual CLI installation](./README.md#install-into-your-agent-framework) — `npx -y agi-super-team@latest --tool <id>` |
| Install by pasting one prompt into a coding agent | [One-prompt coding-agent install](./README.md#coding-agent-quick-start) |
| Understand the project | [README.md](./README.md) |
| Inspect the curated Codex package | [.codex/INDEX.md](./.codex/INDEX.md) |
| Compare other harness manifests | [Harness compatibility](./docs/guides/harness-compatibility.html) |
| Choose a focused team | [Starter Kits](./starter-kits/) |
| Generic workspace files via `install.sh` — **legacy; most users do not need this** | [setup.md](./setup.md) |

`npx -y agi-super-team@latest` is the primary entry point. `install.sh` is the legacy generic workspace materializer: reach for it only when you want harness-neutral, inspectable role files instead of a client adapter, and read the legacy section of [setup.md](./setup.md) before running it.

## ⚡ Quick start in three steps

**1. Install.** Preview first — it writes nothing — then apply the same selection:

```bash
npx -y agi-super-team@latest --list-tools
npx -y agi-super-team@latest --tool claude-code
npx -y agi-super-team@latest --tool claude-code --install --connect
npx -y agi-super-team@latest --tool claude-code --doctor
```

Replace `claude-code` with an ID from `--list-tools`. Every target uses the same command shape; `--install` is the explicit write boundary and `--doctor` verifies what landed. See [all adapter targets](./README.md) and the [primary harness Adapter guide](./docs/guides/harness-adapters.md) for paths, permissions, and receipt requirements. `@latest` installs the published npm release, which can trail the repository; read [release status and recovery](./docs/guides/npm-release-status.md) if the version looks behind.

**2. Restart the client**, or open a new task, so it re-reads the installed Agents and Skills.

**3. Trigger the team.** Paste this reusable prompt and replace the placeholder with your own outcome:

```text
Swarm agents: <your outcome>

Act as the CEO coordinator.
- Define the outcome and acceptance checks.
- Choose the smallest sufficient team.
- Parallelize only independent work with explicit file ownership.
- Use Skills as methods and require an independent Governor review.
- Synthesize one verified result.

If native multi-agent delegation is unavailable, execute the same role plan sequentially and say so. Do not publish, deploy, spend money, use credentials, or take irreversible action without my approval.
```

`Swarm agents:` is the routing cue, not a promise of unlimited parallelism. The installed framework controls actual concurrency, nesting, tools, and model access. The maintained copy of this template lives in [README.md](./README.md#coding-agent-quick-start).

Do not copy or symlink the full `skills/` directory into a live harness. Start with a focused kit and install through an adapter instead of hand-copying trees.

Legacy OpenClaw layouts are repository history, not the current recommended installation path. Never infer provider credentials, gateway configuration, or runtime compatibility from the presence of a manifest.
