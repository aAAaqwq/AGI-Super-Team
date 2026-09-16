# Repository architecture map

Agents enter this repository with partial context. This is the map for the whole tree: what each top-level path is, which module owns it, and whether it carries authority.

The authoritative narrative is [`ARCHITECTURE.md`](../ARCHITECTURE.md) at the repository root — read it for the five layers, seams, deletion tests, and change map. The machine-readable ownership contract is [`config/repository-architecture.json`](../config/repository-architecture.json), and this map is derived from it. Consequential decisions live in [`adr/`](./adr/).

For the files inside `docs/` itself, see the [docs inventory](./docs-inventory.md).

## Path ownership at a glance

Every tracked path is classified by `role`. `authority: true` means the path is a source of truth that other artifacts must not override.

| Role | Count | Meaning |
|---|---|---|
| `authored-authority` | 21 | Canonical sources of truth |
| `generated-output` | 21 | Build products; regenerate, never hand-edit |
| `authored-source` | 14 | Authored inputs that are not themselves authority |
| `implementation` | 12 | Executable tooling |
| `public-navigation` | 12 | Entry points for humans and search |
| `governance` | 11 | Shared language, decisions, and policies |
| `distribution-adapter` | 10 | Framework-specific packaging surfaces |
| `evidence` | 5 | Verification and QA records |

## Authority: the 21 sources of truth

Changing one of these changes meaning for everything downstream. `config/` holds most of them.

- `config/team-manifest.json` — Team and kit membership; drives the installer and validation.
- `config/skill-taxonomy.json` — Skill category and candidate risk signals.
- `config/skill-taxonomy-gold.json` — Reviewed classification labels and fixed sample membership.
- `config/skill-provenance.json`, `config/skill-curation.json` — Skill provenance and curation evidence.
- `config/skill-quality-baseline.json` — Quality gate baseline.
- `config/repository-architecture.json` — Path ownership and authority separation.
- `config/external-skill-sources.json` — Removed machine-local link tombstones.
- Canonical physical Skill inventory — tracked `skills/*/SKILL.md` files, interpreted by [`scripts/repository_model.py`](../scripts/repository_model.py).

README counts, badges, plugin manifests, and generated JSON must never override these.

## The five layers

| Layer | Authored source | Consumer | Contract |
|---|---|---|---|
| Reusable instructions | `skills/*/SKILL.md` | Catalog, Agents, distributions | Tracked physical entrypoint; no symlink |
| Team composition | `agents/`, `starter-kits/`, `config/team-manifest.json` | Generic installer and docs | Manifest is roster and kit authority |
| Distribution | `bin/adapters/`, `config/harness-adapters/`, curated plugin manifests | External harnesses | Presence is not compatibility evidence |
| Verification evidence | `scripts/`, `tests/`, CI | Maintainers and release gates | Structural checks do not imply runtime outcomes |
| Discovery and navigation | `catalog/`, `docs/`, README indexes | Humans, search, coding agents | Generated files never become source authority |

## Top-level paths

| Path | Role | Module | Notes |
|---|---|---|---|
| [`skills/`](../skills/) | canonical library | catalog-discovery | Foundational; consumed by every pack and catalog. Contains `skills/original/` first-party work. |
| [`agents/`](../agents/) | authored-source | team-composition | Generic role packs; `agents/*/TOOLS.md` are generated. |
| [`starter-kits/`](../starter-kits/) | authored-source | team-composition | Outcome-shaped entry points. |
| [`config/`](../config/) | authored-authority | multiple | Most sources of truth and their schemas. |
| [`bin/`](../bin/adapters/) | implementation | safe-installation | CLI entry point, installer, and the Adapter registry. |
| [`install.sh`](../install.sh) | implementation | safe-installation | Generic workspace materializer. |
| [`catalog/`](../catalog/) | generated-output | catalog-discovery | Built by `npm run build:skills`; never a source. |
| [`scripts/`](../scripts/) | implementation | verification-evidence | Builders, validators, and audits. |
| [`tests/`](../tests/) | evidence | verification-evidence | Behavior and contract tests. |
| [`docs/`](./) | public-navigation | public-navigation | GitHub Pages artifact plus editorial surface. |
| [`cookbook/`](../cookbook/) | public-navigation | public-navigation | Long-form references. |
| [`plugins/`](../plugins/) | distribution-adapter | distribution-adapters | Curated per-harness packages; each remains manifest-only until a matching client receipt exists. |
| [`assets/`](../assets/) | public-navigation | public-navigation | Brand and demo media. |
| `.claude-plugin/`, `.codex-plugin/`, `.cursor-plugin/`, `.kimi-plugin/`, `.agents/`, `.codex/` | distribution-adapter | distribution-adapters | Root harness manifests. |
| `ARCHITECTURE.md`, `CONTEXT.md`, `CHARTER.md`, `COLLABORATION.md` | governance / authored-source | governance-memory | Shared language and decision memory. |

## Important seams

- `team-manifest portability class → install.sh selection → workspace Skills + generated TOOLS.md` is the generic-install Seam; only `required` and `optional` cross it.
- `team-manifest assignments → catalog builder → skill-index assignments` is the human/machine classification Seam.
- `skill-taxonomy → catalog builder → catalog/` is a generated discovery Seam.
- Fixed Gold labels + generated skill index → taxonomy evaluator → agreement report is a semantic-regression Seam. It measures label agreement, not runtime quality.
- The four primary external Adapters consume canonical Agents and assigned physical Skills without modifying either source tree.
- `CHARTER.md` and `COLLABORATION.md` are required shared generic-workspace inputs. Installed role packs use relative links to them.

## Change map

| When changing | Update | Verify |
|---|---|---|
| Agent or kit membership | `config/team-manifest.json`, referenced Agent files | `npm run validate -- --warnings-as-errors` |
| Skill metadata or taxonomy | Skill `SKILL.md`, taxonomy, and reviewed label only when its source changed | `npm run check:skills`, `npm run check:skill-quality`, `npm run check:taxonomy-evaluation` |
| Generic installer behavior | `install.sh` and installer fixtures | `npm run test:installer` |
| Curated Codex package | `plugins/agi-super-team-codex/` and its index | Repository tests plus client receipt when available |
| Site data or SEO | `docs/`, data builder, site contracts | `npm run test:repository` |
| Repository boundary or path role | architecture registry, context, relevant ADR | `npm run check:architecture` |
| CLI target or external Adapter | `config/cli-adapters.json`, `bin/adapters/`, `config/harness-adapters/` | See [Adapter 注册机制](./guides/adapter-registration.md) |

## Deletion tests

| Remove | Expected impact | Conclusion |
|---|---|---|
| `config/team-manifest.json` | Installer, catalog usage, and validator must fail before writes | High-Depth authority Interface |
| `config/skill-taxonomy.json` | Catalog build/check must fail | Authored classification authority |
| `config/skill-taxonomy-gold.json` | Semantic evaluation must fail closed | Reviewed evaluation authority |
| `catalog/` | Rebuilders recreate discovery outputs | Generated outputs, never authority |
| One distribution Adapter | Only that harness surface is lost | Adapter boundary is local |
| `CHARTER.md` or `COLLABORATION.md` | Installer preflight must fail with zero writes | Required shared installation Seam |
| A runtime receipt | Source content stays valid but `Verified` disappears | Evidence is not source truth |

## Contract score boundary

`npm run check:architecture` measures automated architecture-classification contracts: path ownership, authority separation, generated lineage, Adapter status, navigation, decision memory, and taxonomy debt ceilings. `npm run check:taxonomy-evaluation` separately measures agreement with the fixed reviewed Gold Set.

**Neither score proves Skill quality, safety, clean harness installs, fixture outcomes, or external beta evidence.**

Return to the [repository README](../README.md).
