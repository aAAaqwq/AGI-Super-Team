# ADR-0008: Ship the complete `skills/` directory in the npm package

- Status: Accepted
- Date: 2026-09-18
- 编号说明：本文原编为 0007，与随后在文献综述线上合入的 [ADR-0007: 壳与魂的分层归属](./0007-shell-soul-layering-and-borrowing.md) 撞号，故重编为 0008。两者讨论不同问题，不构成取代关系。

## Context

`package.json` shipped every `skills/*/SKILL.md` so the whole library stayed discoverable from npm, but only the Skills assigned in `config/team-manifest.json` got their complete directory in the tarball. Every other Skill's entrypoint arrived without the `scripts/` and `references/` files its own instructions tell the reader to run — an npm install resolved to a command that cannot execute. Skill authors reference their own `references/patterns.md`, `scripts/…`, and `assets/…` paths throughout the body, so a tarball carrying the entrypoint alone is a broken product for every non-manifest Skill.

A notice mechanism was built and evaluated as an alternative: annotate each partial Skill's `SKILL.md` with a pointer to the repository, keeping the package small. The investigation surfaced three costs that made the mechanism worse than the problem it solved:

- **Evidence-system coupling.** Two systems treat `SKILL.md` bytes as ground truth — the Gold Set label digest (`source_sha256`) and the catalog's `skill_tree_digest`. Injecting a notice into a reviewed file silently invalidated its label and flipped curated Skills to `stale`; both systems had to learn to strip the generated block, and the strip had to be byte-exact (`strip(render(x)) == x`) or digests drifted.
- **Mutation churn.** 181 `SKILL.md` files were rewritten; every future notice edit or removal re-touched them, and the diff surface belonged to tooling, not authors.
- **Broken-by-default UX.** Even a correct notice sends npm consumers to a clone step. A Skill is useful in the package or it is not; a pointer to the repo is a partial install.

## Decision

Ship the complete `skills/` directory in the npm package. Replace the enumerated per-skill `files` entries with a single `"skills/"` entry, so every tracked file under `skills/` travels in the tarball. No `SKILL.md` is modified, so the Gold Set digests and catalog tree digests stay valid with zero code changes.

`.npmignore` already excludes `**/__pycache__/`, `**/*.py[cod]`, `**/.venv/`, and `**/node_modules/`, so the package grows only with content, not transient files.

The notice mechanism and its builder are not adopted. The byte-neutrality and idempotence requirements that the investigation derived are recorded here as the bar any future annotation tooling must meet, should a size-constrained distribution ever be reconsidered.

## Consequences

- The npm tarball grows from ~13 MB unpacked to the full `skills/` tree (~73 MB on disk, compressed smaller in the tarball). Every Skill — manifest and non-manifest alike — works directly from npm.
- Distribution no longer depends on `team-manifest.json` membership; adding a Skill to the repo automatically adds it to the package.
- The evidence systems (taxonomy Gold Set, provenance/curation tree digests) are untouched by distribution.
- Future size pressure should be addressed by excluding large artifacts (e.g. sample data) via `.npmignore`, not by stripping content that instructions reference.
