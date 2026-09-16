# Documentation index

This is the entry point for everything under `docs/`.

`docs/` is both the GitHub Pages artifact and an editorial navigation surface. It is **public navigation, not source authority** — see [repository architecture](./repository-architecture.md) for what that means.

## Start here

- [**Repository architecture map**](./repository-architecture.md) — how the whole repository is put together: the five layers, the 21 sources of truth, every top-level path and its owning module, the seams, and the change map. Derived from [`config/repository-architecture.json`](../config/repository-architecture.json).
- [**Docs inventory**](./docs-inventory.md) — every file in `docs/`, grouped by purpose.
- [Repository context](../CONTEXT.md) — shared architecture and product language.
- [Root architecture narrative](../ARCHITECTURE.md) — the authoritative long-form version of the map above.

## Architecture and decisions

- [`repository-architecture.md`](./repository-architecture.md) — whole-repository map.
- [`adr/`](./adr/) — architecture decision memory; see its [index](./adr/README.md).
- [`guides/adapter-registration.md`](./guides/adapter-registration.md) — how Adapters are registered and validated in code.
- [`guides/team-agent-skill-architecture.md`](./guides/team-agent-skill-architecture.md) — how the Team, C-suite, Subagents, and Skills connect.
- [`guides/routing-and-enforcement.md`](./guides/routing-and-enforcement.md) — architecture layers, L0–L3 routing tiers, and per-harness enforceability.

## Installing and using

- [`guides/harness-adapters.md`](./guides/harness-adapters.md) — the four primary frameworks' install targets and wiring behavior.
- [`guides/harness-compatibility.html`](./guides/harness-compatibility.html) — what each framework can and cannot enforce.
- [`guides/claude-code-install.html`](./guides/claude-code-install.html), [`guides/codex-install.html`](./guides/codex-install.html) — per-framework install guides.
- [`guides/choose-ai-team.html`](./guides/choose-ai-team.html), [`guides/solo-founder.html`](./guides/solo-founder.html), [`guides/content-creator.html`](./guides/content-creator.html), [`guides/quant-research.html`](./guides/quant-research.html) — picking a team shape and worked use cases.

## Evidence and releases

- [`verification.html`](./verification.html) — how structural checks differ from runtime receipts.
- [`guides/npm-release-status.md`](./guides/npm-release-status.md) — the npm/GitHub release drift diagnosis and its structural fix.
- [`skill-provenance-and-scoring.md`](./skill-provenance-and-scoring.md), [`skill-taxonomy-gold-set.md`](./skill-taxonomy-gold-set.md) — how Skill curation is scored and reviewed.
- [`data/`](./data/) — generated statistics and the separately classified verification receipt.

## Site

- [`index.html`](./index.html) — public homepage.
- [`guides/index.html`](./guides/index.html) — the HTML guide hub.
- [`sitemap.xml`](./sitemap.xml) and [`404.html`](./404.html) — search and failure routes.

---

Generated data must declare its builder and verification command in the [architecture registry](../config/repository-architecture.json). Return to the [repository README](../README.md).
