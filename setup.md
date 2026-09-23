# Setup, verification, and recovery

**Most users should not start here.** The recommended installation path is the npm CLI, `npx -y agi-super-team@latest`. Its commands are documented in the [manual CLI installation](./README.md#install-into-your-agent-framework) section of [README.md](./README.md) and summarized in [STARTUP.md](./STARTUP.md).

This page covers two paths, in this order:

1. The recommended npm CLI path at a glance.
2. The **legacy generic workspace materializer** (`./install.sh`) with its own prerequisites, preview/apply commands, updates, and recovery. Reach for it only when you want harness-neutral, inspectable role workspaces instead of a client adapter.

The curated Codex-native package is separate again; follow [`.codex/INDEX.md`](./.codex/INDEX.md) for that distribution.

## Recommended path: the npm CLI

Node.js 18 or newer is required. Preview is the default and writes nothing; `--install` is the explicit write boundary.

```bash
npx -y agi-super-team@latest --list-tools
npx -y agi-super-team@latest --tool claude-code
npx -y agi-super-team@latest --tool claude-code --install --connect
npx -y agi-super-team@latest --tool claude-code --doctor
```

`--list-tools` prints every adapter ID; substitute the one you actually use. Add `--with-subagents <executive>` or `--all-subagents` only when you want the optional specialists. Reapplying the same selection is designed to be idempotent and differing managed destinations are backed up first, but backups are local recovery aids, not an uninstall system — keep your own version-control backup of important configuration. The [primary harness Adapter guide](./docs/guides/harness-adapters.md) carries paths, permissions, and receipt requirements; [release status and recovery](./docs/guides/npm-release-status.md) explains what to do when the published version trails the repository. `--doctor` verifies installed adapter artifacts, not model behavior or task quality.

## Legacy path: the generic workspace materializer (`install.sh`)

The generic installer remains available when you want harness-neutral, inspectable role workspaces instead of a client adapter. It does not configure models, credentials, or provider accounts, and OpenClaw CLI commands are legacy and optional. Codex, Claude Code, Cursor, Gemini, and Kimi have different extension models; repository metadata does not imply feature parity.

### Prerequisites

- Bash and standard Unix tools.
- Node.js for reading the canonical team manifest.
- npm and Python 3 for repository tests and validation.
- Git when the installer must fetch a repository. A local `--source` avoids that fetch.
- Write permission for the selected `--destination`.
- A supported AI harness configured separately. The installer does not configure models, credentials, or provider accounts.

### 1. Inspect a trusted checkout

```bash
git clone --depth 1 --branch main https://github.com/aAAaqwq/AGI-Super-Team.git
cd AGI-Super-Team
git rev-parse HEAD
```

Record the revision, inspect `install.sh`, and review the selected agent and skill directories before applying changes.

### 2. Preview

Preview is the default. Use an explicit destination so the proposed write locations are easy to audit.

```bash
./install.sh --source "$PWD" --destination /path/to/review-workspace solo-founder
```

Other selectors are `content-creator`, `quant-trader`, `full-team`, or one agent ID such as `ceo`. A second positional agent ID filters a starter kit.

Preview may print an optional legacy OpenClaw warning. It should list planned agents and finish by asking you to re-run with `--apply`.

### 3. Apply after review

```bash
./install.sh --source "$PWD" --destination /path/to/review-workspace --apply solo-founder
```

The installer creates `workspace-<agent>/` directories beneath the destination. It copies supported persona files and selected skill directories without replacing existing paths.

Because the installer preserves existing paths, repeated runs are not an upgrade mechanism for modified files. Review differences and merge intentionally.

### 4. Verify

```bash
find /path/to/review-workspace -maxdepth 2 -type f -name 'AGENTS.md' -print
find /path/to/review-workspace -maxdepth 3 -type f -name 'SKILL.md' -print
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --requirement requirements-dev.txt
npm test
npm run validate
```

Expected kit workspaces:

| Kit | Expected directories |
|---|---|
| `solo-founder` | `workspace-ceo`, `workspace-pe`, `workspace-cco` |
| `content-creator` | `workspace-cco`, `workspace-cdo`, `workspace-cmo` |
| `quant-trader` | `workspace-cqo`, `workspace-cdo`, `workspace-cfo` |

Inspect the installed `SOUL.md`, `AGENTS.md`, `TOOLS.md`, and skills before trusting them. External recommendations are informational and are not bundled by the installer.

### Updates

Fetch the `main` branch, inspect the diff, run repository checks, then preview the installer again:

```bash
git fetch origin main
git diff --stat HEAD..origin/main
git diff HEAD..origin/main -- install.sh agents skills starter-kits
```

Do not blindly pull and apply when local workspace files contain customizations. The installer intentionally preserves those files.

### Recovery

If preview is wrong, stop and correct `--source`, `--destination`, or the kit selector; preview writes nothing.

If an apply is interrupted, stop and inspect the destination before rerunning it. Confirm the exact destination and any staging or backup state, then move uncertain new workspaces aside for review.

If apply reports a missing required skill, do not substitute an unrelated skill. Confirm the checkout is complete and run `npm run validate` before retrying.

Never paste credentials into repository files or command output. Configure providers through the chosen harness and keep secrets outside the project checkout.

## Codex-native package

The Codex distribution is under `plugins/agi-super-team-codex/` and registered by `.agents/plugins/marketplace.json`. It does not use `install.sh` or the starter-kit mapping.

Follow the commands and safe sync procedure in [the Codex package index](./.codex/INDEX.md). Agent sync previews first, backs up differing files, and requires explicit application.
