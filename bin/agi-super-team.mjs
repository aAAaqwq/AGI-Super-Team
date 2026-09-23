#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, rmdirSync } from "node:fs";
import { homedir, platform } from "node:os";
import { basename, dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { loadCatalog, selectTools } from "./installer/catalog.mjs";
import { applyPlanTransaction, buildPlan, doctor, safeRoot } from "./installer/core.mjs";
import { configureHarnessRoots } from "./installer/harness-roots.mjs";
import {
  connectHarnessTransaction,
  preflightHarnessConnection,
  writeHarnessReceiptTransaction,
} from "./installer/connect.mjs";
import { spawnCli } from "./installer/process.mjs";

const PACKAGE_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");

function distributionMetadata(packageRoot) {
  const packageJson = JSON.parse(
    readFileSync(join(packageRoot, "package.json"), "utf8"),
  );
  const revisionResult = spawnSync(
    "git",
    ["-C", packageRoot, "rev-parse", "HEAD"],
    {encoding: "utf8"},
  );
  const sourceRevision = revisionResult.status === 0
    ? revisionResult.stdout.trim()
    : process.env.AGI_SUPER_TEAM_REVISION || null;
  const dirtyResult = spawnSync(
    "git",
    ["-C", packageRoot, "status", "--porcelain", "--untracked-files=normal"],
    {encoding: "utf8"},
  );
  const sourceDirty = dirtyResult.status === 0
    ? Boolean(dirtyResult.stdout.trim())
    : null;
  return {
    packageVersion: packageJson.version,
    sourceRevision,
    sourceDirty,
    revisionMatched: Boolean(sourceRevision && sourceDirty === false),
  };
}

function usage() {
  console.log(`AGI Super Team — preview-first multi-CLI installer

Usage:
  npx -y agi-super-team [options]

Targets:
  --tool <id>            Select a target (repeatable; default: codex)
  --all-tools            Select all 19 targets
  --list-tools           List supported targets
  --home <path>          Override the OS-home base for global targets
  --project-dir <path>   Root for project-scoped targets (default: current directory)

Content and actions:
  --no-agents            Do not install canonical Agents
  --with-subagents <id>  Install one executive group from the hierarchy (repeatable)
  --all-subagents        Install all 92 executive specialist leaves
  --with-cco-specialists Compatibility alias for --with-subagents cco
  --no-skills            Do not install the six curated Skills
  --doctor               Verify the selected installation (read-only)
  --install              Apply changes (default: preview)
  --connect              Connect installed Adapter state and write a pending receipt
  --verbose              Print every planned file instead of the condensed summary
  --plugin               Explicitly install/update the Codex plugin (network side effect)
  --skip-plugin          Compatibility alias that keeps plugin installation disabled

Legacy Codex options remain supported:
  --team <id> --all-teams --all-agents --no-global-ceo
  --skip-plugin --codex-home <path> --list`);
}

function requireValue(argv, index, option) {
  const value = argv[index + 1];
  if (!value || value.startsWith("--")) throw new Error(`${option} requires a value`);
  return value;
}

function parseArgs(argv) {
  const usesMultiTargetInterface = argv.some((argument) =>
    ["--tool", "--all-tools", "--list-tools", "--home", "--project-dir", "--no-agents", "--no-skills", "--with-subagents", "--all-subagents", "--with-cco-specialists", "--doctor", "--connect"].includes(argument),
  );
  const options = {
    install: false, connect: false, doctor: false, listTools: false, listTeams: false, verbose: false,
    tools: [], allTools: false, home: homedir(), homeExplicit: false, projectDir: process.cwd(),
    includeAgents: true, includeSkills: true, teams: [], allTeams: true,
    allAgents: false, globalCeo: true, codexHome: process.env.CODEX_HOME || null,
    plugin: false, legacy: false, includeCcoSpecialists: false, subagentManagers: [], allSubagents: false,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--install") options.install = true;
    else if (argument === "--connect") options.connect = true;
    else if (argument === "--doctor") options.doctor = true;
    else if (argument === "--verbose") options.verbose = true;
    else if (argument === "--all-tools") options.allTools = true;
    else if (argument === "--list-tools") options.listTools = true;
    else if (argument === "--no-agents") options.includeAgents = false;
    else if (argument === "--no-skills") options.includeSkills = false;
    else if (argument === "--with-cco-specialists") options.includeCcoSpecialists = true;
    else if (argument === "--all-subagents") options.allSubagents = true;
    else if (argument === "--all-teams") { options.allTeams = true; options.legacy = true; }
    else if (argument === "--all-agents") { options.allAgents = true; options.legacy = true; }
    else if (argument === "--no-global-ceo") { options.globalCeo = false; options.legacy = true; }
    else if (argument === "--plugin") options.plugin = true;
    else if (argument === "--skip-plugin") options.plugin = false;
    else if (argument === "--list") { options.listTeams = true; options.legacy = true; }
    else if (argument === "--help" || argument === "-h") { usage(); process.exit(0); }
    else if (["--tool", "--home", "--project-dir", "--team", "--codex-home", "--with-subagents"].includes(argument)) {
      const value = requireValue(argv, index, argument);
      if (argument === "--tool") options.tools.push(value);
      else if (argument === "--home") { options.home = value; options.homeExplicit = true; }
      else if (argument === "--project-dir") options.projectDir = value;
      else if (argument === "--team") { options.teams.push(value); options.allTeams = false; options.legacy = true; }
      else if (argument === "--with-subagents") options.subagentManagers.push(value);
      else { options.codexHome = value; options.legacy = true; }
      index += 1;
    } else throw new Error(`unknown option: ${argument}`);
  }
  if (!options.includeAgents && !options.includeSkills) throw new Error("--no-agents and --no-skills select no content");
  if (!options.includeAgents && (options.includeCcoSpecialists || options.allSubagents || options.subagentManagers.length)) throw new Error("subagent options require Agents");
  if (options.allSubagents && (options.includeCcoSpecialists || options.subagentManagers.length)) throw new Error("choose --all-subagents or individual subagent groups, not both");
  if (options.install && options.doctor) throw new Error("choose either --install or --doctor");
  if (options.connect && !options.install) throw new Error("--connect requires --install");
  if (options.allTools && options.tools.length) throw new Error("choose --all-tools or --tool, not both");
  if (options.legacy && (options.allTools || options.tools.some((id) => id !== "codex"))) {
    throw new Error("legacy Team options only apply to the codex target");
  }
  if (!usesMultiTargetInterface) options.legacy = true;
  return options;
}

function resolveCodex(environment) {
  const candidates = [
    process.env.CODEX_CLI,
    "codex",
    join(homedir(), ".local", "bin", "codex"),
    platform() === "darwin" ? "/Applications/ChatGPT.app/Contents/Resources/codex" : null,
  ].filter(Boolean);
  for (const candidate of candidates) {
    const result = spawnCli(candidate, ["--version"], { encoding: "utf8", env: environment });
    if (result.status === 0) return candidate;
  }
  throw new Error("Codex CLI not found; install Codex or pass --skip-plugin");
}

function installCodexPlugin(codexHome, packageVersion) {
  const environment = { ...process.env, CODEX_HOME: codexHome };
  const codex = resolveCodex(environment);
  const capabilities = [
    ["plugin", "add", "--help"],
    ["plugin", "marketplace", "add", "--help"],
    ["plugin", "marketplace", "upgrade", "--help"],
  ];
  for (const arguments_ of capabilities) {
    const result = spawnCli(codex, arguments_, { encoding: "utf8", env: environment });
    if (result.status !== 0) {
      throw new Error(`Codex CLI does not support required plugin command: ${arguments_.slice(0, -1).join(" ")}`);
    }
  }
  const commands = [
    ["plugin", "marketplace", "add", "aAAaqwq/AGI-Super-Team", "--ref", `v${packageVersion}`],
    ["plugin", "marketplace", "upgrade", "agi-super-team"],
    ["plugin", "add", "agi-super-team-codex@agi-super-team"],
  ];
  const completed = [];
  for (const arguments_ of commands) {
    const result = spawnCli(codex, arguments_, { stdio: "inherit", env: environment });
    if (result.status !== 0) {
      const prior = completed.length
        ? `; earlier explicit plugin steps completed (${completed.join(", ")}) and may require Codex plugin-manager cleanup`
        : "";
      throw new Error(`Codex plugin command failed: ${arguments_.join(" ")}${prior}`);
    }
    completed.push(arguments_.slice(0, -1).join(" "));
  }
}

function ensureDirectoryForExternalStage(path) {
  const created = [];
  let cursor = path;
  while (!existsSync(cursor)) {
    created.push(cursor);
    const parent = dirname(cursor);
    if (parent === cursor) break;
    cursor = parent;
  }
  mkdirSync(path, {recursive: true, mode: 0o700});
  return () => {
    for (const directory of created) {
      try {
        rmdirSync(directory);
      } catch (error) {
        if (error.code === "ENOENT") continue;
        if (["ENOTEMPTY", "EEXIST"].includes(error.code)) break;
        throw error;
      }
    }
  };
}

function listTools(catalog) {
  console.log("AGI Super Team CLI targets (19)");
  for (const tool of catalog.tools) {
    console.log(`  ${tool.id.padEnd(14)} ${tool.scope.padEnd(7)} ${tool.support.padEnd(18)} ${tool.label}`);
  }
}

function listTeams(catalog) {
  console.log("AGI Super Team outcome Teams");
  for (const team of catalog.kits) console.log(`  ${team.id.padEnd(20)} ${team.name} — ${team.agents.join(", ")}`);
}

function selectedAgentIds(catalog, options) {
  if (!options.legacy || options.allAgents) return null;
  const kits = new Map(catalog.kits.map((kit) => [kit.id, kit]));
  const ids = options.allTeams ? [...kits.keys()] : options.teams;
  const unknown = ids.filter((id) => !kits.has(id));
  if (unknown.length) throw new Error(`unknown Team: ${unknown.join(", ")}`);
  const roles = new Set(options.globalCeo ? ["ceo"] : []);
  for (const id of ids) for (const role of kits.get(id).agents) if (role !== "ceo") roles.add(role);
  return roles;
}

function selectedSubagentManagers(catalog, options) {
  const available = Object.keys(catalog.specialistGroups);
  const selected = options.allSubagents
    ? available
    : [...options.subagentManagers, ...(options.includeCcoSpecialists ? ["cco"] : [])];
  const unknown = [...new Set(selected)].filter((id) => !available.includes(id));
  if (unknown.length) throw new Error(`unknown subagent group: ${unknown.join(", ")}`);
  return new Set(selected);
}

function configureLegacyCodex(tools, options) {
  const legacyTools = tools.map((tool) => tool.id === "codex" ? {
    ...tool,
    agentMode: "codex-toml",
  } : tool);
  if (!options.codexHome) {
    return {tools: legacyTools, home: safeRoot(options.home, "home")};
  }
  const codexHome = safeRoot(options.codexHome, "Codex home");
  if (codexHome === resolve(homedir())) throw new Error(`refusing unsafe Codex home: ${codexHome}`);
  const home = dirname(codexHome);
  const prefix = basename(codexHome);
  return {
    home,
    tools: legacyTools.map((tool) => tool.id === "codex" ? {
      ...tool,
      agentPaths: [join(prefix, "agents")],
      skillPaths: [join(prefix, "skills")],
    } : tool),
  };
}

function configureCodexRoot(tools, options, home) {
  if (options.legacy || !options.codexHome || !tools.some((tool) => tool.id === "codex")) return tools;
  const codexHome = safeRoot(options.codexHome, "Codex home");
  const defaultCodexHome = safeRoot(join(home, ".codex"), "Codex home");
  if (options.homeExplicit && relative(defaultCodexHome, codexHome) !== "") {
    throw new Error(`--home conflicts with CODEX_HOME: ${codexHome}`);
  }
  if (codexHome === home) throw new Error(`refusing unsafe Codex home: ${codexHome}`);
  return tools.map((tool) => tool.id === "codex" ? {
    ...tool,
    agentPaths: ["agents"],
    connectionPath: join("agi-super-team", "connection.json"),
    installationRoot: codexHome,
  } : tool);
}

const BACKUP_DIRECTORY = ".agi-super-team-backups";
const WARNING_FILE_LIMIT = 10;
const ROOT_LIMIT = 5;
const SPECIALIST_LABEL = /(?:^|[/\s-])specialists?[:/\s]/i;
const SKILL_LABEL = /(?:^|[/\s-])skills?[:/\s]|(?:^|[/\s-])orchestrator$/i;
const AGENT_LABEL = /(?:^|[/\s-])(?:agents?|roles?)[:/\s]|(?:^|[/\s-])global-ceo$/i;

/**
 * The plan is the only authority on what a run writes, so the preview counts
 * come from plan labels. Every adapter family names its role artifacts one of
 * four ways (`agent:<id>`, `role:<id>`, `… Agent ast-<id>`, `…-agent:<id>`), the
 * Codex `--all-agents` payload labels leaves as `agent:ast-<manager>-<leaf>`, and
 * Skills are always `skill:<name>` plus one Adapter orchestrator Skill.
 */
function artifactName(label) {
  const token = label.split(/[/\s:]+/).filter(Boolean).pop() || label;
  return token
    .replace(/^global-/, "")
    .replace(/^ast-/, "")
    .replace(/\.(?:toml|md|json)$/i, "");
}

function specialistName(label, managers) {
  const name = artifactName(label);
  for (const manager of managers) {
    if (name.startsWith(`${manager}-`)) return name.slice(manager.length + 1);
  }
  return name;
}

/**
 * `combined-rules` targets (aider, windsurf) merge every role and Skill into one
 * rules file, so their plan carries no per-role artifact to count. The selection
 * is what lands in that file, so it is seeded from the catalog instead.
 */
function mergedSelection(catalog, options, tools, agentIds, subagentManagers) {
  if (!tools.some((tool) => tool.agentMode === "combined-rules")) return null;
  const agents = options.includeAgents
    ? (agentIds ? catalog.agents.filter((agent) => agentIds.has(agent.id)) : catalog.agents)
    : [];
  const specialists = options.includeAgents
    ? [...subagentManagers].flatMap((manager) => catalog.specialistGroups[manager].specialists)
    : [];
  return {
    agents: agents.map((agent) => agent.id),
    specialists: specialists.map((specialist) => specialist.id),
    skills: options.includeSkills ? catalog.skills.map((skill) => `skill:${skill}`) : [],
  };
}

function planCounts(plan, catalog, merged = null) {
  const managers = Object.keys(catalog.specialistGroups);
  const agents = new Set();
  const specialists = new Set();
  const skills = new Set();
  for (const item of plan) {
    const label = item.label || "";
    if (SKILL_LABEL.test(label)) { skills.add(label); continue; }
    if (SPECIALIST_LABEL.test(label)) { specialists.add(specialistName(label, managers)); continue; }
    if (AGENT_LABEL.test(label)) {
      const name = artifactName(label);
      if (managers.some((manager) => name.startsWith(`${manager}-`))) specialists.add(specialistName(label, managers));
      else agents.add(name);
    }
  }
  if (merged) {
    for (const id of merged.agents) agents.add(id);
    for (const id of merged.specialists) specialists.add(id);
    for (const label of merged.skills) skills.add(label);
  }
  return {agents: agents.size, specialists: specialists.size, skills: skills.size};
}

function nextInstallCommand(options, tools, supportsConnect) {
  const parts = ["npx -y agi-super-team"];
  if (options.legacy) {
    // The legacy Codex interface has its own flags; repeat the ones in use so the
    // suggested command reproduces the same selection.
    if (options.codexHome) parts.push("--codex-home", options.codexHome);
    for (const team of options.teams) parts.push("--team", team);
    if (options.allAgents) parts.push("--all-agents");
    if (!options.globalCeo) parts.push("--no-global-ceo");
  } else if (options.allTools) {
    parts.push("--all-tools");
  } else {
    for (const tool of tools) parts.push("--tool", tool.id);
  }
  if (!options.includeAgents) parts.push("--no-agents");
  if (!options.includeSkills) parts.push("--no-skills");
  if (options.allSubagents) parts.push("--all-subagents");
  else for (const manager of options.subagentManagers) parts.push("--with-subagents", manager);
  if (options.plugin) parts.push("--plugin");
  if (options.homeExplicit) parts.push("--home", options.home);
  if (options.projectDir && resolve(options.projectDir) !== resolve(process.cwd())) {
    parts.push("--project-dir", options.projectDir);
  }
  parts.push("--install");
  if (supportsConnect) parts.push("--connect");
  return parts.join(" ");
}

function overwriteWarning(replaced) {
  const noun = replaced.length === 1 ? "file" : "files";
  const backupRoots = [...new Set(replaced.map((item) => join(item.root, BACKUP_DIRECTORY)))].sort();
  const lines = [
    `!! WARNING: ${replaced.length} existing ${noun} will be REPLACED — current content is copied to`,
    ...backupRoots.map((root) => `     ${join(root, "<timestamp>-XXXXXX")}/`),
    "   before anything is written. Files written by a previous AGI Super Team run are included.",
    "   Backups are a local recovery aid, not an uninstall system, so keep your own copy of anything you cannot lose.",
  ];
  for (const item of replaced.slice(0, WARNING_FILE_LIMIT)) {
    lines.push(`     update ${item.tool.padEnd(14)} ${item.destination}`);
  }
  if (replaced.length > WARNING_FILE_LIMIT) {
    lines.push(`     … and ${replaced.length - WARNING_FILE_LIMIT} more (pass --verbose for the full list)`);
  }
  return lines;
}

function leafWarning() {
  return [
    "!! WARNING: no specialist leaves selected — managers will have nobody to delegate to,",
    "   so L1/L2 routing stops at the manager layer.",
    "   Add every leaf with `--all-subagents`, or one group with `--with-subagents <id>` (e.g. cto, cco).",
  ];
}

function printPlan(plan, options, tools, counts) {
  const statusCounts = Object.fromEntries(["add", "update", "unchanged"].map((status) => [status, plan.filter((item) => item.status === status).length]));
  const replaced = plan.filter((item) => item.status === "update");
  const roots = [...new Set(plan.map((item) => item.root))].sort();
  // Mirrors the install-time check: --connect needs a generated connection spec per
  // target, which legacy Codex TOML installs do not produce.
  const supportsConnect = tools.every((tool) => plan.some((item) => item.label === `adapter:${tool.id}/connection`));
  const mergedRoles = tools.every((tool) => tool.agentMode === "combined-rules") ? " (merged into the target rules file)" : "";
  console.log(`AGI Super Team — ${options.install ? "INSTALL" : "PREVIEW"}   (target: ${tools.map((tool) => tool.id).join(", ")})`);
  if (tools.some((tool) => tool.id === "codex")) {
    console.log(`Codex plugin: ${options.plugin ? "explicitly requested" : "disabled (add --plugin to opt in)"}`);
  }
  console.log("");
  console.log(`  ${(roots.length === 1 ? "Root" : "Roots").padEnd(12)}: ${roots[0] || "(none)"}`);
  for (const root of roots.slice(1, ROOT_LIMIT)) console.log(`  ${"".padEnd(12)}  ${root}`);
  if (roots.length > ROOT_LIMIT) console.log(`  ${"".padEnd(12)}  … and ${roots.length - ROOT_LIMIT} more`);
  console.log(`  ${"Agents".padEnd(12)}: ${counts.agents} canonical + ${counts.specialists} specialists${mergedRoles}`);
  console.log(`  ${"Skills".padEnd(12)}: ${counts.skills}`);
  console.log(`  ${"Overwrites".padEnd(12)}: ${replaced.length}`);
  console.log(`  ${"Files".padEnd(12)}: add=${statusCounts.add} update=${statusCounts.update} unchanged=${statusCounts.unchanged}${options.verbose ? "" : " — pass --verbose for every planned file"}`);
  const warnings = [];
  if (replaced.length) warnings.push(...overwriteWarning(replaced));
  const leavesRequested = options.allSubagents || options.subagentManagers.length > 0 || options.includeCcoSpecialists;
  // --install repeats this warning after the writes, so the preview only carries it
  // once; the overwrite warning always shows because it must precede the write.
  if (!options.install && options.includeAgents && !leavesRequested) warnings.push(...leafWarning());
  if (warnings.length) {
    console.log("");
    for (const line of warnings) console.log(line);
  }
  if (!options.install) {
    const client = tools.length === 1 ? tools[0].label : "the selected CLI";
    console.log("");
    console.log(`  Next: ${nextInstallCommand(options, tools, supportsConnect)}`);
    console.log(`  Then: restart ${client}, then start a task with: Swarm agents: <your outcome>`);
  }
  if (options.verbose) {
    console.log("");
    for (const item of plan) if (item.status !== "unchanged") {
      console.log(`  ${item.status.padEnd(6)} ${item.tool.padEnd(14)} ${item.destination}`);
    }
  }
}

function main() {
  try {
    const options = parseArgs(process.argv.slice(2));
    const catalog = loadCatalog(PACKAGE_ROOT);
    if (options.listTools) { listTools(catalog); return; }
    if (options.listTeams) { listTeams(catalog); return; }
    let tools = selectTools(catalog, options.tools, options.allTools);
    if (options.connect) {
      const unsupported = tools.filter((tool) => !tool.adapterModule);
      if (unsupported.length) {
        throw new Error(`${unsupported.map((tool) => tool.id).join(", ")} does not support --connect`);
      }
    }
    const configured = options.legacy
      ? configureLegacyCodex(tools, options)
      : { tools, home: safeRoot(options.home, "home") };
    tools = configureCodexRoot(configured.tools, options, configured.home);
    const home = configured.home;
    tools = configureHarnessRoots({
      tools,
      home,
      homeExplicit: options.homeExplicit,
      environment: process.env,
      runtimePlatform: platform(),
    });
    const projectDir = options.projectDir ? safeRoot(options.projectDir, "project directory") : null;
    const legacyCodex = options.legacy && tools.length === 1 && tools[0].id === "codex";
    const agentIds = selectedAgentIds(catalog, options);
    const subagentManagers = selectedSubagentManagers(catalog, options);
    if (agentIds) {
      const missingManagers = [...subagentManagers].filter((id) => !agentIds.has(id));
      if (missingManagers.length) {
        throw new Error(`subagent manager is not in the selected Team: ${missingManagers.join(", ")}`);
      }
    }
    const plan = tools.flatMap((tool) => {
      const codexUsesCustomRoot = tool.id === "codex" && tool.installationRoot;
      const common = {
        packageRoot: PACKAGE_ROOT,
        catalog,
        tools: [tool],
        projectDir,
        agentIds,
        subagentManagers,
        includeCcoSpecialists: options.includeCcoSpecialists,
        codexPayloadAll: options.allAgents,
      };
      const artifacts = buildPlan({
        ...common,
        home: tool.installationRoot || home,
        includeAgents: options.includeAgents,
        includeSkills: codexUsesCustomRoot ? false : legacyCodex ? false : options.includeSkills,
      });
      if (!codexUsesCustomRoot || !options.includeSkills) return artifacts;
      const userSkills = buildPlan({
        ...common,
        tools: [{...tool, installationRoot: undefined}],
        home,
        includeAgents: false,
        includeSkills: true,
      }).filter((item) => item.label !== "adapter:codex/connection");
      return [...artifacts, ...userSkills];
    });
    if (options.doctor) {
      const result = doctor(plan, tools);
      console.log(`AGI Super Team doctor: ${result.ok ? "FILES_HEALTHY" : "FILES_FAIL"} (${result.files} files, ${result.issues.length} issues)`);
      console.log("File checks only; connection/runtime status requires a receipt and harness canary.");
      for (const issue of result.issues.slice(0, 20)) console.log(`  ${issue}`);
      if (!result.ok) process.exitCode = 1;
      return;
    }
    const counts = planCounts(plan, catalog, mergedSelection(catalog, options, tools, agentIds, subagentManagers));
    printPlan(plan, options, tools, counts);
    if (!options.install) { console.log("\nPreview only. Add --install to apply."); return; }
    if (options.connect) {
      for (const tool of tools) {
        const item = plan.find((entry) => entry.label === `adapter:${tool.id}/connection`);
        if (!item) throw new Error(`missing generated connection spec for ${tool.id}`);
        preflightHarnessConnection({
          tool,
          home: item.root,
          connection: JSON.parse(item.content.toString("utf8")),
        });
      }
    }
    if (options.plugin && tools.some((tool) => tool.id === "codex")) {
      const codexTool = tools.find((tool) => tool.id === "codex");
      const codexHome = codexTool.installationRoot
        || (options.codexHome ? resolve(options.codexHome) : join(home, ".codex"));
      const cleanupEmptyDirectories = ensureDirectoryForExternalStage(codexHome);
      const {version} = JSON.parse(readFileSync(join(PACKAGE_ROOT, "package.json"), "utf8"));
      try {
        installCodexPlugin(codexHome, version);
      } catch (error) {
        try {
          cleanupEmptyDirectories();
        } catch (cleanupError) {
          throw new AggregateError(
            [error, cleanupError],
            `${error.message}; failed to clean the empty Codex plugin staging directory: ${cleanupError.message}`,
          );
        }
        throw error;
      }
    }
    const installation = applyPlanTransaction(plan);
    const connections = [];
    const receipts = [];
    const connectedMessages = [];
    try {
      for (const backup of installation.backups) console.log(`Backup: ${backup}`);
      if (options.connect) {
        for (const tool of tools) {
          const item = plan.find((entry) => entry.label === `adapter:${tool.id}/connection`);
          if (!item) throw new Error(`missing generated connection spec for ${tool.id}`);
          const connection = JSON.parse(item.content.toString("utf8"));
          const connectionSha256 = createHash("sha256")
            .update(item.content)
            .digest("hex");
          const transaction = connectHarnessTransaction({
            tool,
            home: item.root,
            connection,
          });
          connections.push(transaction);
          const receipt = {
            ...transaction.receipt,
            ...distributionMetadata(PACKAGE_ROOT),
            connectionSha256,
            generatedAt: new Date().toISOString(),
          };
          const receiptTransaction = writeHarnessReceiptTransaction({
            root: item.root,
            connectionPath: tool.connectionPath,
            receipt,
          });
          receipts.push(receiptTransaction);
          connectedMessages.push(`Connected: ${tool.id} (${receipt.status}); receipt: ${receiptTransaction.path}`);
        }
      } else if (tools.some((tool) => tool.id === "openclaw")) {
        console.log("OpenClaw note: artifacts were installed but workspaces were not registered; register them explicitly after review.");
      }
      for (const connection of connections) connection.commit();
      for (const receipt of receipts) receipt.commit();
      installation.commit();
      for (const message of connectedMessages) console.log(message);
    } catch (error) {
      const rollbackErrors = [];
      for (const receipt of [...receipts].reverse()) {
        try { receipt.rollback(); } catch (rollbackError) { rollbackErrors.push(rollbackError); }
      }
      for (const connection of [...connections].reverse()) {
        try { connection.rollback(); } catch (rollbackError) { rollbackErrors.push(rollbackError); }
      }
      try { installation.rollback(); } catch (rollbackError) { rollbackErrors.push(rollbackError); }
      if (rollbackErrors.length) {
        throw new AggregateError(
          [error, ...rollbackErrors],
          `${error.message}; rollback failed: ${rollbackErrors.map((item) => item.message).join("; ")}`,
        );
      }
      throw error;
    }
    console.log("\nInstalled. Restart the selected CLI to load new Agents and Skills.");
    const leafGroupsRequested =
      options.allSubagents || options.subagentManagers.length > 0 || options.includeCcoSpecialists;
    if (options.includeAgents && !leafGroupsRequested) {
      console.log(
        "\nNote: only the C-suite was installed — no specialist leaves.\n" +
        "      Managers will have nobody to delegate to, so L1/L2 routing stops at the manager layer.\n" +
        "      Add every leaf with `--all-subagents`, or one group with `--with-subagents <id>` (e.g. cto, cco).",
      );
    }
  } catch (error) {
    console.error(`error: ${error.message}`);
    process.exitCode = 2;
  }
}

main();
