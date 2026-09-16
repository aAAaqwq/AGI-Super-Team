# npm release status: 1.5.0

Observed on 2026-09-16 UTC. This is a dated release diagnosis, not a live status page. Recheck the registry before relying on it.

## Finding

`FACT`: GitHub has a published `v1.5.0` release, but the official npm registry has no `agi-super-team@1.5.0`. Both npm distribution tags, `latest` and `next`, resolve to `1.4.2`. A GitHub release and an npm publication are separate distribution steps.

`INFERENCE`: The npm distribution step has not produced an available 1.5.0 package. The inspected GitHub workflows contain no npm publication job. This evidence does **not** establish whether a maintainer skipped publication, attempted it elsewhere and failed, or previously removed a package. No npm publication failure log was found in the inspected Actions inventory and recent runs.

## Evidence

| Surface | Observed state | Primary source |
|---|---|---|
| Official npm registry | Versions `1.4.0`, `1.4.1`, `1.4.2`; `latest` and `next` both `1.4.2`; 1.4.2 publication time `2026-08-10T14:40:06.150Z` | [Registry metadata](https://registry.npmjs.org/agi-super-team) |
| GitHub release | Public, neither draft nor prerelease; published `2026-09-14T13:29:29Z`; no attached assets | [v1.5.0 release](https://github.com/aAAaqwq/AGI-Super-Team/releases/tag/v1.5.0) |
| Git tag | `v1.5.0` resolves to `a9652239072e49c06e5c0503ed5df76f02d436aa` | [Tag API](https://api.github.com/repos/aAAaqwq/AGI-Super-Team/git/ref/tags/v1.5.0) |
| Release commit validation | `Validate Repository` succeeded for `a9652239` | [Run 34843007434](https://github.com/aAAaqwq/AGI-Super-Team/actions/runs/34843007434) |
| Current main validation | `Validate Repository` succeeded for `27de4aa1cf97f64fe4004ed40e05bc59220fb32b` | [Run 35058132534](https://github.com/aAAaqwq/AGI-Super-Team/actions/runs/35058132534) |
| GitHub workflows | Repository validation and Pages deployment are active; the inventory has no npm publish workflow | [Workflow inventory](https://api.github.com/repos/aAAaqwq/AGI-Super-Team/actions/workflows) |

## Local package checks and boundaries

At main commit `27de4aa1cf97f64fe4004ed40e05bc59220fb32b`:

- `package.json`, the curated Codex plugin manifest, and the four root Claude/Codex/Cursor/Kimi plugin manifests declare `1.5.0`.
- `npm pack --dry-run --ignore-scripts --json` succeeded: 1,609 files, 4,659,425 packed bytes and 12,904,611 unpacked bytes.
- The dry-run inventory contains every tracked `bin/**/*.mjs` runtime module, with executable mode `0755` on `bin/agi-super-team.mjs`. The inspected transient patterns (`__pycache__`, `.pyc`, `.pyo`, `.DS_Store`, `.env`, and `node_modules`) were absent.
- The command skipped lifecycle scripts. It did not publish, validate npm account permissions, or establish a successful package installation or live harness outcome. Full local tests belong to the accompanying release validation, not this inventory check.

Main has 16 changed files relative to `v1.5.0`, including installer and Adapter behavior, while retaining version `1.5.0`. Its dry-run inventory is therefore not an inventory of the existing release tag. Publishing this main checkout as 1.5.0 would give npm and the existing Git tag different source contents.

## Smallest recovery

1. Select the release source. To complete the existing 1.5.0 release, use a clean checkout of `a9652239072e49c06e5c0503ed5df76f02d436aa`. To ship subsequent main changes, prepare a new version and matching tag instead of silently reusing the existing tag.
2. From the selected clean source, install the documented validation dependencies, run the repository gates in [AGENTS.md](../../AGENTS.md), inspect `npm pack --dry-run --ignore-scripts --json`, and smoke-test an actual packed archive in an isolated destination. Record the source commit and archive integrity.
3. Obtain explicit publication authorization and use an authorized npm maintainer session. Publish the reviewed source to `https://registry.npmjs.org` without bypassing the `prepublishOnly` gate. Account authorization and registry acceptance remain unverified by this diagnosis.
4. Verify the exact version, `dist.integrity`, and intended distribution tag from the official registry, then test installation by exact published version. Update public installation examples only to versions that resolve there.

Changing `latest` alone cannot recover 1.5.0 while that version is absent from the registry. Future automation should treat GitHub release creation and npm registry verification as separate checks and retain publication logs.

## Reproduce the read-only diagnosis

```bash
npm view agi-super-team dist-tags versions time --json --registry=https://registry.npmjs.org
gh release view v1.5.0 --repo aAAaqwq/AGI-Super-Team --json tagName,publishedAt,isDraft,isPrerelease,url,assets
gh api repos/aAAaqwq/AGI-Super-Team/git/ref/tags/v1.5.0
gh api repos/aAAaqwq/AGI-Super-Team/actions/workflows
gh run list --repo aAAaqwq/AGI-Super-Team --limit 15 --json workflowName,headSha,event,status,conclusion,createdAt,url
git diff --stat v1.5.0..27de4aa1cf97f64fe4004ed40e05bc59220fb32b
npm pack --dry-run --ignore-scripts --json
```
