# Docs directory inventory

Every file under `docs/`. For how the repository is put together, start with the [repository architecture map](./repository-architecture.md).

## Site

- [`index.html`](./index.html) — public homepage: the brief → team → deliverable story, with framework-specific preview commands.
- [`verification.html`](./verification.html) — how structural checks and runtime receipts differ, and what is actually proven.
- [`guides/index.html`](./guides/index.html) — the HTML guide hub.
- [`sitemap.xml`](./sitemap.xml) and [`404.html`](./404.html) — search and failure routes.

## Guides

Maintained installation, compatibility, evidence, and use-case guidance.

- [`guides/harness-adapters.md`](./guides/harness-adapters.md) — the four primary frameworks' install targets, on-disk artifacts, wiring behavior, and receipt requirements.
- [`guides/adapter-registration.md`](./guides/adapter-registration.md) — how Adapters are registered and validated in code, and what adding a framework actually requires.
- [`guides/team-agent-skill-architecture.md`](./guides/team-agent-skill-architecture.md) — canonical explanation of Team selection, C-suite routing, specialist leaves, Skill assignment, and Adapter compilation.
- [`guides/routing-and-enforcement.md`](./guides/routing-and-enforcement.md) — the four architecture layers, L0–L3 routing tiers, and which constraints each harness can hard-enforce versus prompt-only.
- [`guides/npm-release-status.md`](./guides/npm-release-status.md) — dated diagnosis of the npm/GitHub release drift and its structural fix.
- [`guides/claude-code-install.html`](./guides/claude-code-install.html) — Claude Code installation guide.
- [`guides/codex-install.html`](./guides/codex-install.html) — Codex installation guide.
- [`guides/harness-compatibility.html`](./guides/harness-compatibility.html) — what each supported framework can and cannot enforce.
- [`guides/choose-ai-team.html`](./guides/choose-ai-team.html) — picking a team shape for your task.
- [`guides/solo-founder.html`](./guides/solo-founder.html), [`guides/content-creator.html`](./guides/content-creator.html), [`guides/quant-research.html`](./guides/quant-research.html) — worked use-case guides.

## Evidence and skill curation

- [`100-dev-skills-candidates.md`](./100-dev-skills-candidates.md) — candidate developer Skill list awaiting review.
- [`skill-provenance-and-scoring.md`](./skill-provenance-and-scoring.md) — how a Skill's provenance and curation evidence is scored.
- [`skill-taxonomy-gold-set.md`](./skill-taxonomy-gold-set.md) — the reviewed taxonomy gold set.
- [`skills-matrix.md`](./skills-matrix.md) — legacy Agent matrix.
- [`adr/`](./adr/) — architecture decision memory; see its [index](./adr/README.md).
- [`data/`](./data/) — generated same-origin statistics plus a separately classified verification receipt; never source authority.

Generated data must declare its builder and verification command in the [architecture registry](../config/repository-architecture.json).

Return to the [repository README](../README.md).
