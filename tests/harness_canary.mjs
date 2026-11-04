#!/usr/bin/env node
// Opt-in runtime canary for harnesses whose CLI is installed and authenticated.
// Discovery: ask the client to list loaded subagents.
// Route: ask which C-suite owns a task, then compare with the intent-routing table.
//
// Never runs by default. Exits 0 with status "skipped" when the CLI or
// credentials are absent, so it can be wired into a manual workflow without
// turning missing secrets into a false failure.

import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const args = process.argv.slice(2);
const option = (name, fallback) => {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] : fallback;
};

const harness = option("--harness", "claude-code");
const mode = option("--mode", "discovery");
const receiptPath = option("--receipt", "");
const routeConfig = JSON.parse(
  readFileSync(join(root, "config", "intent-routing.json"), "utf8"),
);
const roleIds = routeConfig.routes.map((route) => route.primary);

const clients = {
  "claude-code": {
    binary: process.env.CLAUDE_CLI || "claude",
    env: (home) => ({ CLAUDE_CONFIG_DIR: join(home, ".claude") }),
    discovery: () => ["-p", "List every available subagent name in this session, one per line. Do not run any other tool.", "--output-format", "json"],
    route: (task) => ["-p", `先读取 agi-super-team-orchestrator Skill 的意图路由表。只输出一个主责 C-suite 角色 ID，不要解释。任务：${task}`, "--output-format", "json"],
  },
  codex: {
    binary: process.env.CODEX_CLI || "codex",
    env: (home) => ({ CODEX_HOME: join(home, ".codex") }),
    discovery: () => ["exec", "List every available agent name in this session, one per line."],
    route: (task) => ["exec", `先读取 agi-super-team-orchestrator Skill 的意图路由表。只输出一个主责 C-suite 角色 ID，不要解释。任务：${task}`],
  },
};

function finish(status, details, exitCode = 0) {
  const receipt = { harness, mode, status, timestamp: new Date().toISOString(), ...details };
  if (receiptPath) {
    mkdirSync(dirname(receiptPath), { recursive: true });
    writeFileSync(receiptPath, `${JSON.stringify(receipt, null, 2)}\n`);
  }
  console.log(JSON.stringify(receipt, null, 2));
  process.exit(exitCode);
}

const client = clients[harness];
if (!client) finish("failed", { error: `unsupported harness: ${harness}` }, 2);

const home = process.env.AST_CANARY_HOME || process.env.RUNNER_TEMP;
if (!home) finish("skipped", { reason: "AST_CANARY_HOME or RUNNER_TEMP is required for isolation" });

const probe = spawnSync(client.binary, ["--version"], { encoding: "utf8" });
if (probe.status !== 0) {
  finish("skipped", { reason: `${client.binary} is not installed` });
}

const task = option("--task", "设计一个 A 股量化回测假设，并检查是否存在过拟合。");
const expected = option("--expect", "cqo");
const command = mode === "route" ? client.route(task) : client.discovery();
const result = spawnSync(client.binary, command, {
  encoding: "utf8",
  env: { ...process.env, ...client.env(home) },
  timeout: Number(option("--timeout-ms", "600000")),
});
if (result.error) finish("failed", { error: result.error.message }, 1);

const output = `${result.stdout || ""}\n${result.stderr || ""}`;
const discovered = [...output.matchAll(/\bast-[a-z][a-z-]*/g)].map((match) => match[0]);
const matchedRole = roleIds.find((id) => new RegExp(`\\b${id}\\b`, "i").test(output));

if (mode === "discovery") {
  const ok = result.status === 0 && new Set(discovered).size >= 10;
  finish(ok ? "verified" : "failed", {
    command,
    exitCode: result.status,
    agentsSeen: [...new Set(discovered)].sort(),
    reason: ok ? undefined : "fewer than 10 ast-* agents were reported",
  }, ok ? 0 : 1);
}

const ok = result.status === 0 && matchedRole === expected;
finish(ok ? "verified" : "failed", {
  command,
  exitCode: result.status,
  expected,
  matchedRole,
  excerpt: output.trim().slice(0, 400),
}, ok ? 0 : 1);
