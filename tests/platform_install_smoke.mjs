#!/usr/bin/env node
// Install every declared adapter into an isolated home/project, then verify the
// discovery contract each client relies on: agent artifacts parse, connection
// manifests point at real skills, the orchestrator routes to real roles, and
// Skill links resolve. This is structural discovery, not a live model canary.

import { spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, readdirSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const cli = resolve(process.argv[2] || join(root, "bin", "agi-super-team.mjs"));
const adapters = JSON.parse(readFileSync(join(root, "config", "cli-adapters.json"), "utf8")).tools;
const manifest = JSON.parse(readFileSync(join(root, "config", "team-manifest.json"), "utf8"));
const routing = JSON.parse(readFileSync(join(root, "config", "intent-routing.json"), "utf8"));
const expectedAgentIds = manifest.agents.map((agent) => agent.id);

const home = mkdtempSync(join(tmpdir(), "ast-platform-home-"));
const project = mkdtempSync(join(tmpdir(), "ast-platform-project-"));

// These harnesses keep their own state root; the CLI resolves the same defaults.
const HARNESS_ROOT = {
  openclaw: ".openclaw",
  hermes: ".hermes",
  dsh: ".dsh",
};

function baseFor(tool) {
  if (tool.id === "hermes" && process.platform === "win32") {
    return join(home, "AppData", "Local", "hermes");
  }
  return HARNESS_ROOT[tool.id] ? join(home, HARNESS_ROOT[tool.id]) : home;
}

function environment() {
  const env = { ...process.env, NO_COLOR: "1" };
  if (process.platform === "win32") env.LOCALAPPDATA = join(home, "AppData", "Local");
  for (const name of ["OPENCLAW_HOME", "OPENCLAW_STATE_DIR", "HERMES_HOME", "DSH_HOME"]) delete env[name];
  return env;
}

const failures = [];

function run(args) {
  return spawnSync(process.execPath, [cli, ...args], { encoding: "utf8", env: environment() });
}

function walk(directory) {
  if (!existsSync(directory)) return [];
  const files = [];
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) files.push(...walk(path));
    else if (entry.isFile()) files.push(path);
  }
  return files;
}

function hasFiles(path) {
  return existsSync(path) && statSync(path).isDirectory() && readdirSync(path).length > 0;
}

function frontmatter(text) {
  if (!text.startsWith("---")) return null;
  const end = text.indexOf("\n---", 3);
  if (end < 0) return null;
  const block = text.slice(3, end);
  const name = /^name:\s*"?([^"\n]+)"?/m.exec(block)?.[1]?.trim();
  const hasDescription = /^description:\s*(?:\||>|[^\n])/m.test(block);
  return name && hasDescription ? { name } : null;
}

function agentFiles(tool, agentRoot) {
  if (!agentRoot || !existsSync(agentRoot)) return [];
  if (statSync(agentRoot).isFile()) return [agentRoot];
  if (tool.agentMode === "combined-rules") return [agentRoot];
  return walk(agentRoot).filter((path) => {
    if (tool.id === "codex") return path.endsWith(".toml");
    if (tool.id === "dsh") return path.endsWith("AGENTS.md");
    return /\.(md|mdc|agent\.md)$/.test(path);
  });
}

function parseAgentArtifact(tool, path) {
  const text = readFileSync(path, "utf8");
  if (tool.id === "codex") {
    return {
      ok: /^name\s*=\s*"ast-[a-z-]+"/m.test(text) && /^description\s*=\s*"/m.test(text),
      routed: text.includes("典型信号"),
    };
  }
  const fields = frontmatter(text);
  if (!fields) return { ok: false, routed: false };
  // openclaw workspace files and DSH role bodies are not single-agent frontmatter.
  const routed = ["claude-code", "codex", "hermes", "pi", "oh-my-pi", "grok-build"].includes(tool.id)
    || tool.agentMode === "markdown"
    || tool.agentMode === "agent-as-skill"
    || tool.agentMode === "antigravity-agent"
    || tool.agentMode === "trae-rule";
  return { ok: true, routed: !routed || text.includes("典型信号") };
}

function agentArtifactMap(agentRoot) {
  const map = new Map();
  if (!agentRoot || !existsSync(agentRoot) || statSync(agentRoot).isFile()) return map;
  for (const path of walk(agentRoot)) {
    const parts = path.split(sep);
    const basename = parts[parts.length - 1];
    let key = basename;
    for (const suffix of [".agent.md", ".mdc", ".md", ".toml"]) {
      if (key.endsWith(suffix)) { key = key.slice(0, -suffix.length); break; }
    }
    if (basename === "SKILL.md" || basename === "agent.md") key = parts[parts.length - 2];
    key = key.replace(/^ast-/, "");
    if (expectedAgentIds.includes(key) && !map.has(key)) map.set(key, path);
  }
  return map;
}

function verifyAgentArtifacts(tool, agentRoot) {
  const problems = [];
  if (tool.agentMode === "combined-rules") {
    if (!existsSync(agentRoot)) return [`missing rules file ${agentRoot}`];
    const text = readFileSync(agentRoot, "utf8");
    const missing = expectedAgentIds.filter((id) => {
      return !new RegExp(`\\b${id}\\b`, "i").test(text) && !text.includes(id.toUpperCase());
    });
    if (missing.length) problems.push(`combined rules omit ${missing.join(", ")}`);
    return problems;
  }
  if (["dsh", "openclaw"].includes(tool.id)) {
    const files = agentFiles(tool, agentRoot);
    if (files.length < 14) problems.push(`expected at least 14 agent artifacts, found ${files.length}`);
    return problems;
  }
  const byName = agentArtifactMap(agentRoot);
  const ids = tool.id === "codex" ? expectedAgentIds.filter((id) => id !== "ceo") : expectedAgentIds;
  for (const id of ids) {
    if (!byName.has(id)) {
      problems.push(`missing agent artifact for ${id}`);
      continue;
    }
    const parsed = parseAgentArtifact(tool, byName.get(id));
    if (!parsed.ok) problems.push(`${id}: unparseable agent frontmatter`);
    else if (!parsed.routed) problems.push(`${id}: description lacks intent keywords`);
  }
  if (tool.id === "codex") {
    const ceo = join(agentRoot, "..", "AGENTS.md");
    if (!existsSync(ceo) || !readFileSync(ceo, "utf8").includes("CEO")) {
      problems.push("codex global AGENTS.md does not carry the CEO coordinator");
    }
  }
  return problems;
}

function orchestratorPath(tool, base) {
  if (tool.id === "hermes") return join(base, "skills", "agi-super-team-orchestrator", "SKILL.md");
  if (tool.id === "claude-code") return join(base, ".claude", "skills", "agi-super-team-orchestrator", "SKILL.md");
  if (tool.id === "codex") return join(base, ".agents", "skills", "agi-super-team-orchestrator", "SKILL.md");
  if (tool.id === "dsh" && tool.skillPaths[0]) {
    return join(base, tool.skillPaths[0], "agi-super-team-orchestrator", "SKILL.md");
  }
  return null;
}

function verifyConnection(tool, base, skillRoot) {
  const problems = [];
  if (tool.agentMode !== "harness-adapter") return problems;
  const path = tool.connectionPath ? join(base, tool.connectionPath) : null;
  if (!path || !existsSync(path)) return [`missing connection ${tool.connectionPath}`];
  let connection;
  try {
    connection = JSON.parse(readFileSync(path, "utf8"));
  } catch {
    return [`connection is not valid JSON: ${tool.connectionPath}`];
  }
  const agentCount = connection.agentMap
    ? Object.keys(connection.agentMap).length
    : connection.profileMap
      ? Object.keys(connection.profileMap).length
      : Array.isArray(connection.roleAgents)
        ? connection.roleAgents.length
        : null;
  if (agentCount !== null && agentCount < expectedAgentIds.length - 1) {
    problems.push(`connection maps ${agentCount} agents, expected at least ${expectedAgentIds.length - 1}`);
  }
  const assigned = connection.assignedSkills?.all || [];
  for (const skill of assigned) {
    if (!skillRoot || !existsSync(join(skillRoot, skill))) {
      problems.push(`connection references missing skill ${skill}`);
    }
  }
  return problems;
}

function verifyOrchestrator(tool, base) {
  const path = orchestratorPath(tool, base);
  if (!path) return [];
  if (!existsSync(path)) return [`missing orchestrator ${path}`];
  const text = readFileSync(path, "utf8");
  const problems = [];
  for (const route of routing.routes) {
    if (!text.includes(`\`${route.primary}\``)) {
      problems.push(`orchestrator does not route to ${route.primary}`);
    }
  }
  if (!text.includes("禁止默认")) problems.push("orchestrator lacks the no-default-CTO rule");
  return problems;
}

function verifySkillLinks(tool, agentRoot) {
  if (!agentRoot || !existsSync(agentRoot) || statSync(agentRoot).isFile()) return [];
  const missing = [];
  for (const path of agentFiles(tool, agentRoot)) {
    const text = readFileSync(path, "utf8");
    for (const match of text.matchAll(/\]\(([^)]+)\)/g)) {
      const link = match[1].split("#")[0];
      if (!link || link.startsWith("http") || !/skills?\//.test(link)) continue;
      if (!existsSync(resolve(dirname(path), link))) missing.push(`${relative(agentRoot, path)} -> ${link}`);
    }
  }
  return missing.length ? [`${missing.length} broken Skill link(s), e.g. ${missing[0]}`] : [];
}

function verify(tool) {
  const base = tool.scope === "project" ? project : baseFor(tool);
  // DSH's preset path in the adapter registry is home-relative, while its
  // skills and connection receipt live under the DSH state root.
  const agentBase = tool.id === "dsh" && tool.scope !== "project" ? home : base;
  const agentRoot = tool.agentPaths[0] ? join(agentBase, tool.agentPaths[0]) : null;
  const skillRoot = tool.skillPaths[0] ? join(base, tool.skillPaths[0]) : null;
  const problems = [];

  if (!agentRoot || !existsSync(agentRoot)) problems.push(`missing agent path ${tool.agentPaths[0]}`);
  else if (!hasFiles(agentRoot) && !statSync(agentRoot).isFile()) problems.push(`empty agent path ${tool.agentPaths[0]}`);

  if (tool.skillPaths.length) {
    if (!skillRoot || !existsSync(skillRoot)) problems.push(`missing skill path ${tool.skillPaths[0]}`);
    else if (!hasFiles(skillRoot)) problems.push(`empty skill path ${tool.skillPaths[0]}`);
  }

  problems.push(...verifyAgentArtifacts(tool, agentRoot));
  problems.push(...verifyConnection(tool, base, skillRoot));
  problems.push(...verifyOrchestrator(tool, base));
  problems.push(...verifySkillLinks(tool, agentRoot));
  return problems;
}

try {
  for (const tool of adapters) {
    const result = run(["--tool", tool.id, "--home", home, "--project-dir", project, "--install"]);
    if (result.status !== 0) {
      failures.push(`${tool.id}: install exited ${result.status}: ${(result.stderr || result.stdout).trim().split("\n").slice(-3).join(" | ")}`);
      continue;
    }
    const problems = verify(tool);
    if (problems.length) failures.push(`${tool.id}: ${problems.join("; ")}`);

    const doctor = run(["--tool", tool.id, "--home", home, "--project-dir", project, "--doctor"]);
    if (doctor.status !== 0) {
      failures.push(`${tool.id}: doctor exited ${doctor.status}: ${(doctor.stdout || doctor.stderr).trim().split("\n").slice(-3).join(" | ")}`);
    }
  }

  const list = run(["--list-tools"]);
  if (list.status !== 0 || !list.stdout.includes(`targets (${adapters.length})`)) {
    failures.push(`--list-tools did not report ${adapters.length} targets`);
  }

  if (failures.length) {
    console.error(`Platform install smoke failed (${failures.length}):`);
    for (const failure of failures) console.error(`  - ${failure}`);
    process.exitCode = 1;
  } else {
    console.log(`Platform install smoke passed: ${adapters.length} adapters installed, discovery contracts verified.`);
  }
} finally {
  rmSync(home, { recursive: true, force: true });
  rmSync(project, { recursive: true, force: true });
}
