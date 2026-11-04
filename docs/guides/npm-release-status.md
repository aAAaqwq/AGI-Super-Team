# npm release status: 1.8.0

Observed on 2026-11-04. This is a dated release snapshot, not a live status page. Recheck the registry before relying on it.

## Registry state

- `latest` resolves to `1.7.1` (published 2026-09-20).
- `next` still resolves to `1.4.2`; it is stale and should not be used.
- `1.8.0` is prepared in this checkout but not published.

## What 1.8.0 changes

- **Skill library is installable and categorized.** `--list-skills` groups every canonical Skill by category; `--list-categories` prints category counts; `--skill <name>` installs one; `--skill-pack <category>` installs a category; `--all-skills` installs the full library. The default remains the `config/team-manifest.json` assignment for the selected Agents.
- **22 adapter targets.** Pi (`.pi/agent/skills`), Oh My Pi (`.omp/agent`), and Grok Build (`.grok`) join the existing Claude Code, Codex, OpenClaw, Hermes, DSH, OpenCode, Gemini CLI, and generic adapters. CI installs every adapter from the packed tarball on Linux, macOS, and Windows.
- **Intent routing is explicit.** The orchestrator Skill and every harness wrapper now embed a routing table keyed by work object and delivery, and each C-suite Agent description carries concrete trigger keywords. Single-domain tasks go to the matching C-suite; CTO is no longer a default fallback; CEO is reserved for cross-domain trade-offs.
- **New Skills registered.** The 22 Skills added since `v1.7.1` are assigned to their owning roles instead of being catalog-only. Two malformed frontmatter blocks (`daniel-xhs-writing`, `vibe-knowledge-award`) and 17 unparseable YAML blocks were repaired so the generated index carries real names and descriptions.
- **Installed Agent links resolve.** Agent/role text is now rebased from the repository layout to each harness's real Skill directory. Smoke installs of `claude-code` and `codex` report 0 broken relative links (previously 235 and 217).
- **`--no-skills` is consistent.** Claude Code frontmatter and adapter connection specs no longer advertise Skills that were not installed.
- **Packaging.** `catalog/skill-index.json`, the intent-routing config, and their schemas ship with the package; runtime logs, scan dumps, and `data/**/*.jsonl` are excluded; a `prepack` step normalizes file modes to `0644`/`0755`. The packed archive is about 16.9 MB packed / 47 MB unpacked across roughly 5,200 files.

## Known gaps

- Publishing requires an authenticated npm session or the `NPM_TOKEN` repository secret. The local CLI currently returns 401.
- Default CI verifies the discovery contract only: artifacts install, agent frontmatter parses, connection manifests point at real Skills, orchestrator routes resolve, and Skill links exist. It does not start a model or observe delegation.
- A manual `Harness Canary (manual)` workflow can run `discovery` or `route` checks against a real client. It skips unless `live=true` and the matching `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` secret exists; every run writes a receipt artifact.
- `--doctor` still derives its expected file set from the current flags, so a plain `--doctor` after `--all-subagents --install` reports drift. Use the same flags for the check.
- The Codex `config.toml` depth block is intentionally skipped when the user already owns an `[agents]` table; that install then keeps `max_depth = 1`. Merging into a foreign table is not implemented.

## Release gates

```bash
npm test
npm run validate:strict
npm pack --dry-run --ignore-scripts --json
npm pack
npm install --prefix /tmp/ast-install ./agi-super-team-1.8.0.tgz
node /tmp/ast-install/node_modules/agi-super-team/bin/agi-super-team.mjs --list-tools
git tag v1.8.0 && git push origin main v1.8.0
```

The tag must be exactly `v1.8.0` (it must equal `v` + `package.json.version`), and the `NPM_TOKEN` repository secret must exist for `.github/workflows/npm-publish.yml` to publish.

## Verification boundaries

The checks above prove file layout and installer behavior only. They do not prove that a harness client loaded the Agents, that delegation actually occurred, or that the registry accepted the upload. Those require a client receipt and a registry lookup by exact version.
