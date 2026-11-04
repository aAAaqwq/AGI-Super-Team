# npm release status: 1.8.0

Observed on 2026-11-04. This is a dated release snapshot, not a live status page. Recheck the registry before relying on it.

## Registry state

- `latest` resolves to `1.7.1` (published 2026-09-20).
- `next` still resolves to `1.4.2`; it is stale and should not be used.
- `1.8.0` is prepared in this checkout but not published.

## What 1.8.0 changes

- **Skill library is installable.** `--list-skills` lists every canonical Skill; `--skill <name>` installs one; `--all-skills` installs the full library. The default remains the `config/team-manifest.json` assignment for the selected Agents.
- **New Skills registered.** The 17 Skills added since `v1.7.1` are assigned to their owning roles instead of being catalog-only. Two malformed frontmatter blocks (`daniel-xhs-writing`, `vibe-knowledge-award`) were repaired so the generated index carries real names and descriptions.
- **Installed Agent links resolve.** Agent/role text is now rebased from the repository layout to each harness's real Skill directory. Smoke installs of `claude-code` and `codex` report 0 broken relative links (previously 235 and 217).
- **`--no-skills` is consistent.** Claude Code frontmatter and adapter connection specs no longer advertise Skills that were not installed.
- **Packaging.** `catalog/skill-index.json` and its schema ship with the package; runtime logs, scan dumps, and `data/**/*.jsonl` are excluded; unused non-Codex plugin copies are no longer packed; a `prepack` step normalizes file modes to `0644`/`0755`. The packed archive is about 16.9 MB packed / 46.7 MB unpacked across roughly 5,200 files.

## Known gaps

- This checkout is 4 commits behind `origin/main`, which adds 5 A-share Skills. Sync and register those before tagging `v1.8.0`.
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
