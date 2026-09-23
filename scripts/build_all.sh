#!/usr/bin/env bash
# `npm run build:all` - regenerate every derived artifact in dependency order.
#
# Why this exists: the repository derives nine datasets from skills/ and
# config/ (catalog, original-skills index, agent indexes, team index, subagent
# provenance, codex team, harness packages, skill-quality report, taxonomy
# evaluation) and
# nothing forced them to be regenerated. On 2026-09-21 a skill was merged
# without refreshing the catalog; the repository then failed its own contract
# checks on `main` for two days because a checklist cannot fail a build.
#
# Every generator runs even when an earlier one fails. `&&` would hide all
# failures after the first and `;` would hide all of them, so neither can be
# used: one invocation must report every staleness at once. The exit status is
# non-zero when any generator failed.
#
# Called by .githooks/pre-commit when a commit touches skills/ or config/.

set -u

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$REPO_ROOT" || exit 1

PYTHON="$REPO_ROOT/scripts/python.sh"

# Order matters for one reason only: build_skill_catalog.py is the sole writer
# of catalog/skill-index.json, and two later generators consume it as input.
#
#   build_original_skills_index.py     reads catalog/skill-index.json
#   build_skill_taxonomy_evaluation.py reads catalog/skill-index.json
#
# Everything else reads authored inputs (config/, skills/, agents/) only, so
# its position below is for readability rather than correctness.
#
# `build:skills` is deliberately absent: it is a composite that runs the first
# two generators below, and listing it as well would run both of them twice.
STEPS=(
  "build:skill-catalog|scripts/build_skill_catalog.py"
  "build:original-skills|scripts/build_original_skills_index.py"
  "build:agent-indexes|scripts/build_agent_skill_indexes.py"
  "build:team-index|scripts/build_team_index.py"
  "build:subagent-sources|scripts/build_executive_subagent_sources.py"
  "build:codex-team|scripts/build_codex_csuite_adapter.py"
  "build:harness-packages|scripts/check_harness_packages.py"
  "build:skill-quality|scripts/audit_skill_quality.py"
  "build:taxonomy-evaluation|scripts/build_skill_taxonomy_evaluation.py"
)

# Stop this list from going stale. Adding a tenth generator to package.json
# without adding it here would silently reintroduce the very drift this script
# exists to prevent, so the omission is made to fail loudly instead. The scan
# reads every `build:*` entry, follows composites, and compares the union of
# the generators they name against the generators covered above.
if ! command -v node >/dev/null 2>&1; then
  printf 'error: node is required to verify generator coverage (package.json).\n' >&2
  exit 127
fi

covered=$(printf '%s\n' "${STEPS[@]}" | cut -d'|' -f2 | sort)
declared=$(node --input-type=module -e '
  import { readFileSync } from "node:fs";
  const { scripts } = JSON.parse(readFileSync("package.json", "utf8"));
  const found = new Set();
  for (const [name, command] of Object.entries(scripts)) {
    if (!name.startsWith("build:")) continue;
    for (const match of command.matchAll(/scripts\/[\w.-]+\.py/g)) found.add(match[0]);
  }
  process.stdout.write([...found].sort().join("\n") + "\n");
')

if [ "$covered" != "$declared" ]; then
  printf 'error: build:all does not cover every generator declared in package.json.\n' >&2
  printf '\nStale or missing here (add to STEPS in scripts/build_all.sh):\n' >&2
  comm -13 <(printf '%s\n' "$covered") <(printf '%s\n' "$declared") | sed 's/^/  /' >&2
  printf 'Listed here but gone from package.json (remove from STEPS):\n' >&2
  comm -23 <(printf '%s\n' "$covered") <(printf '%s\n' "$declared") | sed 's/^/  /' >&2
  exit 1
fi

total=0
failures=0
report=""

for step in "${STEPS[@]}"; do
  label=${step%%|*}
  script=${step#*|}
  total=$((total + 1))
  printf '\n=== %s (%s)\n' "$label" "$script"
  bash "$PYTHON" "$script"
  status=$?
  if [ "$status" -ne 0 ]; then
    failures=$((failures + 1))
    report="${report}${label} (${script}) exited ${status}"$'\n'
  fi
done

printf '\n'
if [ "$failures" -ne 0 ]; then
  printf 'build:all FAILED - %s of %s generator(s) did not complete:\n' "$failures" "$total" >&2
  printf '%s' "$report" | sed 's/^/  - /' >&2
  printf '\nArtifacts written before the failure are on disk and untouched.\n' >&2
  printf 'Fix the generators above, then re-run `npm run build:all`.\n' >&2
  exit 1
fi

printf 'build:all OK - %s generator(s) refreshed.\n' "$total"
