#!/usr/bin/env node
// Bridge that exposes the existing `bin/adapters/<id>.mjs` renderers to the
// Python package builders.
//
// Why this exists: the curated per-harness packages under `plugins/` must be
// byte-identical to what the installer writes, or the repository ends up with
// two renderers that drift. Rewriting the five adapters in Python would create
// exactly that second source of truth. Instead the package builders shell out
// to this bridge, which calls the same `renderAdapterArtifacts` /
// `buildConnectionSpec` the installer calls, and hands back the bytes.
//
// The adapters are intentionally *not* imported at module scope so a missing
// adapter id fails with a readable message rather than a stack trace.
//
// Usage:
//   node scripts/util/render_harness_artifacts.mjs --root <repo> --harness <id> \
//     [--environment KEY=VALUE]...
//
// `--environment` pins values the adapters read from the process environment
// (DSH reads `DSH_PROFILE`). Package builds pass an empty environment so a
// contributor's own `DSH_PROFILE` cannot change what lands in the repository;
// the installer path passes the real one, which is what a user actually runs.
//
// Output (stdout, JSON):
//   {
//     "harness": "claude-code",
//     "home": "/tmp/agi-super-team-package-home",
//     "artifacts": [{"relativePath": "...", "label": "...", "contentBase64": "..."}],
//     "connection": {...}
//   }
//
// `home` is a throwaway absolute path used only so path-building code has
// something valid to resolve against; package outputs never embed it (the
// Python side rewrites the connection spec to repository-relative paths).

import { randomBytes } from "node:crypto";
import { argv, exit, platform, stdout } from "node:process";
import { join, resolve } from "node:path";

import { adapterFor } from "../../bin/adapters/index.mjs";
import { loadCatalog } from "../../bin/installer/catalog.mjs";


function parseEnvironment(entries) {
  const environment = {};
  for (const entry of entries) {
    const separator = entry.indexOf("=");
    if (separator < 1) throw new Error(`--environment expects KEY=VALUE: ${entry}`);
    environment[entry.slice(0, separator)] = entry.slice(separator + 1);
  }
  return environment;
}

function parseArguments(tokens) {
  const options = { root: null, harness: null, environment: [] };
  for (let index = 0; index < tokens.length; index += 1) {
    const token = tokens[index];
    if (token === "--root") options.root = tokens[++index];
    else if (token === "--harness") options.harness = tokens[++index];
    else if (token === "--environment") options.environment.push(tokens[++index]);
    else throw new Error(`unknown argument: ${token}`);
  }
  return options;
}

function fail(message) {
  process.stderr.write(`render_harness_artifacts: ${message}\n`);
  exit(1);
}

const options = parseArguments(argv.slice(2));
if (!options.root) fail("--root is required");
if (!options.harness) fail("--harness is required");

const packageRoot = resolve(options.root);

// A resolved, non-root scratch home satisfies every adapter's path-safety
// guard (hermes refuses `/` and `null`, openclaw refuses relative paths)
// without touching anything real. Nothing is written through it.
const home = join(
  resolve(platform === "win32" ? process.env.TEMP || "/tmp" : "/tmp"),
  `agi-super-team-package-home-${randomBytes(8).toString("hex")}`,
);

const catalog = loadCatalog(packageRoot);
const configured = catalog.tools.find((candidate) => candidate.id === options.harness);
if (!configured) fail(`unknown harness in config/cli-adapters.json: ${options.harness}`);

// The CLI resolves the harness root (DSH's `$DSH_HOME`, OpenClaw's state dir)
// and hands it to the adapters as `installationRoot`; without it the adapters
// fall back to deriving a sub-directory under `home`, which would make the
// package root and the artifact layout disagree. Pinning it to the scratch
// home keeps one root for both, so a package reads "everything here is
// relative to your harness root".
const tool = { ...configured, installationRoot: configured.installationRoot ?? home };

const adapter = adapterFor(options.harness);
const environment = parseEnvironment(options.environment);

// The curated package mirrors the full install: every canonical agent, no
// specialist pyramid, and no Skill bodies (the installer vendors those from
// the canonical `skills/` root, so copying them here would duplicate
// canonical source merely to satisfy a harness layout -- see ADR-0002).
const agents = catalog.agents;
const groups = {};
const specialists = [];
const assignedSkills = catalog.assignedSkills;

const artifacts = adapter.renderAdapterArtifacts({
  packageRoot,
  home,
  environment,
  tool,
  agents,
  groups,
  specialists,
  assignedSkills,
  includeAgents: true,
  includeSkills: true,
});

const connection = adapter.buildConnectionSpec({
  packageRoot,
  home,
  environment,
  tool,
  agents,
  groups,
  specialists,
  assignedSkills,
});

stdout.write(
  `${JSON.stringify(
    {
      harness: options.harness,
      home,
      artifacts: artifacts.map((artifact) => ({
        relativePath: artifact.relativePath,
        label: artifact.label,
        contentBase64: Buffer.from(artifact.content).toString("base64"),
      })),
      connection,
    },
    null,
    2,
  )}\n`,
);
