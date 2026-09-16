import { join } from "node:path";
import {
  BEGIN_MARKER,
  END_MARKER,
  globalCeoPayload,
  roleBody,
  specialistBody,
} from "../installer/render.mjs";
import {
  DSH_DEFAULT_PROFILE,
  DSH_PATCH_BEGIN,
  DSH_PATCH_END,
  DSH_PRESET_ID,
  ORCHESTRATOR_SKILL_DIR,
  dshAgentPreset,
  dshOrchestratorSkill,
  dshPatchPayload,
  dshPresetMetadata,
  dshRoleEnvelope,
  dshSkillRoot,
} from "./dsh-templates.mjs";

export const ADAPTER_ID = "dsh";

export {
  DSH_DEFAULT_PROFILE,
  DSH_PATCH_BEGIN,
  DSH_PATCH_END,
  DSH_PRESET_ID,
};

// DSH brings its own agent composition machinery: roles are *not* one file per
// agent the way Claude Code / Codex / Hermes model them. Three mechanisms carry
// what an "Agent" means here, and this adapter uses all three because none of
// them alone is sufficient:
//
//   1. `$DSH_HOME/AGENTS.md` — the user-global instruction chain. Advisory only
//      ("workspace instructions do not override system, developer, or direct
//      user instructions"), so it carries the CEO contract, never a capability.
//   2. `<dshHome>/profiles/<profile>/cordis.patch.yml` — the declarative user
//      patch layer. It re-enables the host `skill-filesystem` row that
//      `dsh-web-app` disables and points `customSkillDirs` at this repository's
//      skills. This is the ONLY way skills on disk become reachable.
//   3. `<dshHome>/.agent-presets/<id>/agent.cordis.yml` — the agent-plane
//      composition. A session composes its tools and prompt sections from here,
//      so role routing and the delegation tools live in the preset.
//
// The preset id is `ast-team`, which is also the `agentPaths` entry in the CLI
// manifest — so `--install` really writes the tree that entry points at.

/**
 * The DSH data root. `configureHarnessRoots` already resolves `$DSH_HOME` (or
 * `~/.dsh`) into `tool.installationRoot`, and `core.mjs` installs every
 * artifact under that same root — so the adapter must read it back rather than
 * re-deriving it, or the patch would point `customSkillDirs` at a path the
 * skills were never written to. Without the resolver (direct module use in
 * tests) fall back to the documented default under the given home.
 */
function dshHome({home, tool}) {
  if (tool?.installationRoot) return tool.installationRoot;
  if (typeof home !== "string" || !home.trim()) {
    throw new Error("DSH adapter requires a home or a resolved installation root");
  }
  return join(home, ".dsh");
}

/**
 * The profile whose patch layer this adapter owns. `$DSH_PROFILE` is the
 * documented way for a deployment to pin a profile; without it the adapter
 * uses `web`, the profile `dsh web` boots.
 */
export function resolveDshProfile(environment = process.env) {
  const configured = environment?.DSH_PROFILE;
  if (configured === null || configured === undefined) return DSH_DEFAULT_PROFILE;
  const name = String(configured).trim();
  return name || DSH_DEFAULT_PROFILE;
}

/**
 * Whether a patch layer already carries entries this adapter must not
 * overwrite. A `cordis.patch.yml` is a single YAML document holding a top-level
 * array, so there is no safe merge: this returns true when the file holds real
 * entries, and the installer then leaves it completely alone.
 *
 * A file holding only the shipped template's placeholder `[]`, blank lines, and
 * comments counts as empty — overwriting that is safe and is the normal case,
 * because DSH writes the placeholder the first time a profile is booted.
 */
export function hasPreexistingPatchEntries(existing) {
  if (existing === null || existing === undefined) return false;
  const text = Buffer.isBuffer(existing) ? existing.toString("utf8") : String(existing);
  return text
    .split(/\r?\n/)
    .some((line) => {
      const trimmed = line.trim();
      // `[]` is the shipped placeholder. A file containing only it (plus
      // comments) carries no entries and is safe to replace.
      return trimmed && !trimmed.startsWith("#") && trimmed !== "[]";
    });
}

function presetRoot(dshRoot) {
  return join(dshRoot, ".agent-presets", DSH_PRESET_ID);
}

function assertContract({ tool, agents }) {
  if (!tool || tool.id !== ADAPTER_ID) throw new Error("DSH adapter requires tool.id=dsh");
  if (!Array.isArray(agents)) throw new Error("DSH adapter requires canonical agents");
}

export function renderAdapterArtifacts({
  packageRoot,
  home,
  environment = process.env,
  tool,
  agents,
  groups = {},
  specialists = [],
  includeAgents = true,
  includeSkills = true,
}) {
  assertContract({ tool, agents });
  const dshRoot = dshHome({home, tool});
  const profile = resolveDshProfile(environment);
  const skillRoot = dshSkillRoot(dshRoot);
  const artifacts = [];

  if (includeAgents) {
    const ceo = agents.find((agent) => agent.id === "ceo");
    if (ceo) {
      // The global instruction chain is the only place a DSH session is
      // guaranteed to look before the project tree, so the CEO contract lives
      // here. Advisory by design — capabilities are the preset's job.
      artifacts.push({
        relativePath: "AGENTS.md",
        content: globalCeoPayload(packageRoot),
        label: "adapter:dsh/global-ceo",
        managed: {begin: BEGIN_MARKER, end: END_MARKER},
      });
      artifacts.push({
        relativePath: join("profiles", profile, "cordis.patch.yml"),
        content: dshPatchPayload(dshRoot),
        label: "adapter:dsh/skill-filesystem-patch",
        // Deliberately NOT a managed block. A `cordis.patch.yml` is a single
        // YAML document holding one top-level array, so merging cannot append:
        // the shipped profile template already ends in `[]`, and appending
        // entries after it yields a file DSH refuses to parse (`end of the
        // stream or a document separator is expected`). Overwriting is safe
        // exactly when the file holds no real entries, which is what this
        // predicate decides — so the payload is written as a complete,
        // standalone patch file and the user's own entries are never touched.
        skipIf: hasPreexistingPatchEntries,
      });
    }
    artifacts.push({
      relativePath: join(".agent-presets", DSH_PRESET_ID, "agent.cordis.yml"),
      content: dshAgentPreset(packageRoot, agents, specialists, skillRoot),
      label: "adapter:dsh/preset:composition",
    });
    artifacts.push({
      relativePath: join(".agent-presets", DSH_PRESET_ID, "preset.yml"),
      content: dshPresetMetadata(),
      label: "adapter:dsh/preset:metadata",
    });
    // DSH has no per-role file directory, so the canonical role bodies land as
    // the workspace instructions of the preset's `ast-team` member tree.
    for (const agent of agents) {
      artifacts.push({
        relativePath: join(
          ".agent-presets",
          DSH_PRESET_ID,
          "agents",
          agent.id,
          "AGENTS.md",
        ),
        content: Buffer.from(
          `${dshRoleEnvelope(agent, groups[agent.id] || null)}\n\n${roleBody(packageRoot, agent, groups[agent.id] || null, (manager, id) => `ast-${manager}-${id}`, (id) => `ast-${id}`)}\n`,
        ),
        label: `adapter:dsh/role:${agent.id}`,
      });
    }
    for (const specialist of specialists) {
      artifacts.push({
        relativePath: join(
          ".agent-presets",
          DSH_PRESET_ID,
          "agents",
          specialist.manager,
          "subagents",
          specialist.id,
          "AGENTS.md",
        ),
        content: specialistBody(packageRoot, specialist),
        label: `adapter:dsh/specialist:${specialist.manager}/${specialist.id}`,
      });
    }
  }

  if (includeSkills) {
    artifacts.push({
      relativePath: join(
        "skills",
        "agi-super-team",
        ORCHESTRATOR_SKILL_DIR,
        "SKILL.md",
      ),
      content: dshOrchestratorSkill(packageRoot, skillRoot),
      label: "adapter:dsh/skill:orchestrator",
    });
  }
  return artifacts;
}

export function buildConnectionSpec({
  packageRoot,
  home,
  environment = process.env,
  tool,
  agents,
  specialists = [],
}) {
  assertContract({ tool, agents });
  const dshRoot = dshHome({home, tool});
  const profile = resolveDshProfile(environment);
  const preset = presetRoot(dshRoot);
  return {
    connectionMode: "agent-preset-plus-user-patch",
    coordinatorRuntime: "global-agents-md-and-ast-team-preset",
    home: dshRoot,
    paths: {
      globalInstructions: join(dshRoot, "AGENTS.md"),
      presetRoot: preset,
      presetComposition: join(preset, "agent.cordis.yml"),
      profilePatch: join(dshRoot, "profiles", profile, "cordis.patch.yml"),
      orchestratorSkill: join(
        dshRoot,
        "skills",
        "agi-super-team",
        ORCHESTRATOR_SKILL_DIR,
        "SKILL.md",
      ),
    },
    profile,
    presetId: DSH_PRESET_ID,
    roleAgents: agents.map((agent) => `ast-${agent.id}`),
    specialistAgents: specialists.map(
      (item) => `ast-${item.manager}-${item.id}`,
    ),
    activation: {
      mode: "dsh-agent-preset",
      entrySkill: ORCHESTRATOR_SKILL_DIR,
      requiresProfilePatch: true,
      // DSH composes a session from exactly one preset, and a running session
      // can switch only while it has produced nothing.
      presetMustBeSelectedByUser: true,
    },
    limitations: [
      "DSH exposes no per-role tool or capability boundary: every ast-* role composes from the same ast-team preset, so the C-suite/leaf separation is carried by the persona routing and the host approval stack rather than by the harness.",
      "The skill-filesystem patch is skipped when the target profile's cordis.patch.yml already declares entries; a patch file is one YAML document and cannot be merged into.",
      "The runtime effect of the patch was observed on DSH 0.1.5-rc.1 (developer preview, breaking changes expected) and under the headless profile only.",
    ],
    canary: {
      status: "pending",
      requiresDshCli: true,
      requiredFlow: ["ast-ceo", "manager-output", "ast-governor", "ast-ceo-synthesis"],
      receiptMustBindRepositoryRevision: true,
    },
  };
}
