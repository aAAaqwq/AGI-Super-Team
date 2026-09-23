# Contributing to AGI Super Team

Contributions should be reviewable, attributable, safe to test, and honest about support. Do not include secrets, private data, unlicensed content, or claims that cannot be reproduced.

## Derived data and the pre-commit hook

Eight datasets here are generated from authored sources and committed: the skill catalog, the original-skills index, the per-agent skill indexes, the executive subagent provenance ledger, the Codex team, the four harness packages under `plugins/`, the skill-quality report, and the taxonomy evaluation. `npm test` fails whenever one of them disagrees with its sources.

Because that check runs in CI, a stale artifact is not caught until after you push — historically not until after a merge to `main`, where it went unnoticed for two days. The repository therefore also ships a pre-commit hook:

```bash
git config core.hooksPath .githooks   # once per clone; pulls in no npm dependency
```

With it enabled, a commit touching `skills/` or `config/` runs two guards. They catch different things, and the second one cannot be fixed by regenerating anything:

1. **Derived data must not be stale.** The hook runs `npm run build:all`, re-stages the artifacts it rewrote, and blocks the commit when any generator fails, so sources and derived data land together.
2. **Structural quality debt must not grow.** `config/skill-quality-baseline.json` is a ratchet: its numbers are ceilings meant to fall, and no generator can lower one. After the rebuild the hook runs `npm run check:skill-quality` and blocks the commit when a metric exceeds its ceiling, printing the regressed numbers and offering a choice — fix the content (usually a new skill whose `description` lacks a trigger phrase or runs past 180 characters), or raise that ceiling deliberately and explain why in the commit message. Fixing the content is the default answer.

Either guard failing exits non-zero and leaves your index exactly as you left it. Commits touching neither directory return immediately (tens of milliseconds); one that does touch them takes a few seconds. `check:skill-quality` is the only `check:*` script that is a ratchet — the others assert that a generated artifact matches its sources, which the rebuild already covers, so the hook does not repeat them.

**The hook does not turn itself on.** `core.hooksPath` is per-clone state that git will not set for you, and this repository has no npm dependencies, so nothing guarantees an `npm install` that could set it. A `prepare` script does set it when you happen to run `npm install`, but treat the command above as the step that makes it true. Until you run it, your commits are unchecked locally and CI is the first place drift appears.

If the hook blocks a commit you believe is fine, run the generators by hand (`npm run build:all`) or bypass it with `git commit --no-verify`. Prefer fixing the drift to bypassing the check. When guard 2 blocks, bypassing is the wrong reflex — the ratchet is asking you to either fix the content or consciously accept the debt, and `--no-verify` chooses neither.

Every `npm` script here resolves its own Python interpreter, so `npm test`, `npm run validate:strict`, and `npm run build:all` work on a machine whose `python3` is older than 3.11 — no virtualenv activation required. The resolution order is `AGI_SUPER_TEAM_PYTHON` first, then `python3.13`/`python3.12`/`python3.11`, then `python3` if it is new enough, then `uv`. Set `AGI_SUPER_TEAM_PYTHON` when a suitable interpreter exists but is not discoverable by name; the interpreter needs Python 3.11 or newer plus the packages in `requirements-dev.txt`.

## Before opening a pull request

1. Branch from `main` and keep the change focused.
2. Search for an existing skill, agent, or issue before adding a duplicate.
3. Record provenance for adapted material: upstream URL, revision or retrieval date, license, and what changed.
4. Add or update tests for executable behavior. For documentation, run examples in an isolated temporary destination when safe.
5. Run the repository checks:

   ```bash
   python3 -m venv .venv
   . .venv/bin/activate
   python -m pip install --requirement requirements-dev.txt
   npm run build:all
   npm test
   npm run validate -- --warnings-as-errors
   ```

6. Review the diff for credentials, personal data, unsafe shell commands, generated artifacts, and unsupported claims.

## Skills

A skill lives at `skills/<name>/SKILL.md`. Keep one clear purpose, document triggers and boundaries, and place optional scripts or assets in the same skill directory.

Run `npm run build:all` after adding, renaming, or recategorizing a skill; `npm run build:skills` is the narrower two-generator subset that covers the catalog and the original-skills index alone. With the pre-commit hook enabled the full build runs for you whenever you commit under `skills/`. If the deterministic rule chooses the wrong primary category, add the narrowest rule or an explicit override to [`config/skill-taxonomy.json`](./config/skill-taxonomy.json).

Do not submit placeholders, bulk-generated duplicates, unsupported compatibility claims, or instructions with no maintainable purpose. A catalog entry is not automatically curated, tested, or portable across harnesses.

Commands must state prerequisites, expected effects, and recovery. Destructive, external, production, or account-changing operations need explicit human confirmation. Never embed credentials or encourage users to pipe unreviewed remote code into a shell.

## Agents

An agent lives at `agents/<id>/` and normally includes `SOUL.md` and `AGENTS.md`; other persona or workflow files are optional. Keep role boundaries clear and use mentor references only as creative framing, not affiliation or endorsement.

## Provenance and licensing

For copied or adapted content, include the source project, immutable revision where possible, source license, and adaptation summary in the relevant provenance file or pull-request description.

Confirm that the source license permits redistribution. Do not submit scraped private content, proprietary prompts, model outputs with unclear rights, or generated code copied from an unverified source.

## Testing evidence

The pull request must include:

- exact commands executed and their results;
- the harness and relevant version used for manual checks;
- fixtures or sanitized inputs needed to reproduce the result;
- limitations, skipped checks, and untested environments;
- screenshots only when they add evidence and contain no sensitive data.

Do not claim “production-ready,” “live-validated,” profitable, secure, or universally compatible solely from unit tests or a local demo.

## Pull request scope

Use `.github/PULL_REQUEST_TEMPLATE.md`. Describe behavior before and after, risk, rollback, provenance, and evidence. Maintainers may ask for a smaller change or reject additions that cannot be safely maintained.

Report vulnerabilities privately as described in [SECURITY.md](./SECURITY.md). Follow [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md) in all project spaces.
