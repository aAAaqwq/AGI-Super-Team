#!/usr/bin/env node
// Install every declared adapter into an isolated home/project and verify the
// promised artifacts exist. Runs in CI on Linux, macOS, and Windows.

import { spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, readdirSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const cli = resolve(process.argv[2] || join(root, "bin", "agi-super-team.mjs"));
const adapters = JSON.parse(readFileSync(join(root, "config", "cli-adapters.json"), "utf8")).tools;

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
  if (process.platform === "win32") {
    env.LOCALAPPDATA = join(home, "AppData", "Local");
  }
  for (const name of ["OPENCLAW_HOME", "OPENCLAW_STATE_DIR", "HERMES_HOME", "DSH_HOME"]) {
    delete env[name];
  }
  return env;
}
const failures = [];

function run(args) {
  return spawnSync(process.execPath, [cli, ...args], {
    encoding: "utf8",
    env: environment(),
  });
}

function hasFiles(path) {
  return existsSync(path) && statSync(path).isDirectory() && readdirSync(path).length > 0;
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

  if (tool.agentMode === "harness-adapter") {
    if (!tool.connectionPath || !existsSync(join(base, tool.connectionPath))) {
      problems.push(`missing connection ${tool.connectionPath}`);
    }
  }

  if (tool.agentMode === "combined-rules") {
    if (!existsSync(agentRoot)) problems.push(`missing rules file ${tool.agentPaths[0]}`);
  }

  return problems;
}

try {
  for (const tool of adapters) {
    const result = run([
      "--tool", tool.id,
      "--home", home,
      "--project-dir", project,
      "--install",
    ]);
    if (result.status !== 0) {
      failures.push(`${tool.id}: install exited ${result.status}: ${(result.stderr || result.stdout).trim().split("\n").slice(-3).join(" | ")}`);
      continue;
    }
    const problems = verify(tool);
    if (problems.length) failures.push(`${tool.id}: ${problems.join("; ")}`);

    const doctor = run([
      "--tool", tool.id,
      "--home", home,
      "--project-dir", project,
      "--doctor",
    ]);
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
    console.log(`Platform install smoke passed: ${adapters.length} adapters installed and verified.`);
  }
} finally {
  rmSync(home, { recursive: true, force: true });
  rmSync(project, { recursive: true, force: true });
}
