import { dirname, join } from "node:path";
import {
  BEGIN_MARKER,
  END_MARKER,
  codexAgent,
  codexSpecialist,
  globalCeoPayload,
} from "../installer/render.mjs";


export const ADAPTER_ID = "codex";

// Codex 的团队深度由 ~/.codex/config.toml 的 [agents] max_depth 强制。
// 默认值是 1 —— 装完不改，C-suite 派发叶子时会被 Codex 原生拒绝
// （"Agent depth limit reached. Solve the task yourself."），且是静默的：
// 装完看起来一切正常，直到真让团队干活才发现派不出去。所以必须由安装器写入。
//
// 值 = 2，不是 3：Codex 的 root session 本身就是 CEO（本 adapter 不写 ast-ceo.toml），
// 因此链条是 root(CEO)=0 → C-suite=1 → leaf=2。
// 对比 Claude Code：main=0 → ast-ceo=1 → C-suite=2 → leaf=3，那边才需要 3。
export const CODEX_CONFIG_BEGIN = "# AGI-SUPER-TEAM:CODEX-CONFIG:BEGIN";
export const CODEX_CONFIG_END = "# AGI-SUPER-TEAM:CODEX-CONFIG:END";
export const CODEX_MAX_DEPTH = 2;
export const CODEX_MAX_THREADS = 12;

/** 用户已有的 [agents] 表会与托管块里的 [agents] 冲突（TOML 不允许重复定义表）。
 *  没有 warning 通道，所以宁可不写也不能写出一个 Codex 解析不了的配置。 */
export function hasForeignAgentsTable(existing) {
  if (existing === null || existing === undefined) return false;
  const text = Buffer.isBuffer(existing) ? existing.toString("utf8") : String(existing);
  const begin = text.indexOf(CODEX_CONFIG_BEGIN);
  const end = text.indexOf(CODEX_CONFIG_END);
  const outside =
    begin >= 0 && end > begin
      ? text.slice(0, begin) + text.slice(end + CODEX_CONFIG_END.length)
      : text;
  return /^\s*\[agents\]\s*$/m.test(outside);
}

export function codexConfigPayload() {
  return `${CODEX_CONFIG_BEGIN}\n[agents]\nmax_depth = ${CODEX_MAX_DEPTH}\nmax_threads = ${CODEX_MAX_THREADS}\n${CODEX_CONFIG_END}`;
}

function jsonSkill(assignedSkills, id) {
  return assignedSkills?.byAgent?.[id] || [];
}

function orchestratorSkill() {
  return `---
name: agi-super-team-orchestrator
description: 在 Codex 中按 CEO→C-suite→Leaf→Governor 路由复杂任务；需要跨职能并行、独立复核或完整团队交付时使用。
---

# AGI Super Team｜Codex Adapter

这是 Codex 的运行时包装 Skill。开始前必须读取同一 Skill 根目录中的 \`../orchestrate-agi-super-team/SKILL.md\`，并按需读取其 references；canonical Skill 决定是否组队、通用任务包、Governor 和人工批准契约，本文件只补充 Codex 调度方式。

你是主会话中的 CEO 协调者。先定义结果、约束和验收，再按任务选择最小充分团队。

- 使用 \`spawn_agent\` 调用已安装的 \`ast-*\` Agent。
- CEO 只能调用 C-suite、PE 和 Governor。
- Manager 只能调用自己在配置中列出的直属叶子，最多两个并发。
- Leaf 和 Governor 不得继续创建 Agent，总深度不得超过二。
- Governor 必须独立审查重大结论；主 Agent 保留其有证据支持的异议。
- 登录、发布、部署、资金、凭证、法律承诺和其他不可逆动作必须由用户最终批准。
- 最终回传决策、证据、验证、限制、剩余风险和下一步。
`;
}

export function renderAdapterArtifacts({
  packageRoot,
  tool,
  agents,
  groups,
  specialists,
  includeAgents = true,
  includeSkills = true,
}) {
  const artifacts = [];
  if (includeAgents) {
    const ceo = agents.find((agent) => agent.id === "ceo");
    if (ceo) {
      const payload = globalCeoPayload(packageRoot);
      artifacts.push({
        relativePath: join(dirname(tool.agentPaths[0]), "AGENTS.md"),
        content: payload,
        label: "adapter:codex/global-ceo",
        managed: {begin: BEGIN_MARKER, end: END_MARKER},
      });
      const codexDir = dirname(tool.agentPaths[0]);
      artifacts.push({
        relativePath: join(codexDir, "config.toml"),
        content: codexConfigPayload(),
        label: "adapter:codex/config-depth",
        managed: {begin: CODEX_CONFIG_BEGIN, end: CODEX_CONFIG_END},
        skipIf: hasForeignAgentsTable,
      });
    }
    for (const agent of agents.filter((item) => item.id !== "ceo")) {
      artifacts.push({
        relativePath: join(tool.agentPaths[0], `ast-${agent.id}.toml`),
        content: codexAgent(packageRoot, agent, groups[agent.id] || null),
        label: `adapter:codex/agent:${agent.id}`,
      });
    }
    for (const specialist of specialists) {
      artifacts.push({
        relativePath: join(
          tool.agentPaths[0],
          `ast-${specialist.manager}-${specialist.id}.toml`,
        ),
        content: codexSpecialist(packageRoot, specialist),
        label: `adapter:codex/specialist:${specialist.manager}/${specialist.id}`,
      });
    }
  }
  if (includeSkills) {
    for (const skillPath of tool.skillPaths) {
      artifacts.push({
        relativePath: join(
          skillPath,
          "agi-super-team-orchestrator",
          "SKILL.md",
        ),
        content: orchestratorSkill(),
        label: `adapter:codex/skill:orchestrator:${skillPath}`,
      });
    }
  }
  return artifacts;
}

export function buildConnectionSpec({
  agents,
  groups,
  specialists,
  assignedSkills,
}) {
  const selectedIds = new Set(agents.map((agent) => agent.id));
  const agentMap = Object.fromEntries(
    agents.map((agent) => [agent.id, `ast-${agent.id}`]),
  );
  const managerAgentMap = {};
  for (const [manager, group] of Object.entries(groups || {})) {
    managerAgentMap[manager] = {
      agent: `ast-${manager}`,
      requiredMaxDepth: 2,
      maxConcurrentChildren: 2,
      delegates: Object.fromEntries(
        group.specialists.map((item) => [
          item.id,
          `ast-${manager}-${item.id}`,
        ]),
      ),
      roleRefs: Object.fromEntries(
        (group.roleRoutes || [])
          .filter((item) => selectedIds.has(item.id))
          .map((item) => [item.id, `ast-${item.id}`]),
      ),
    };
  }
  return {
    schemaVersion: 1,
    harness: ADAPTER_ID,
    runtimeEvidence: "pending",
    coordinator: "ceo",
    coordinatorRuntime: "current-session-global-agents-md",
    independentReviewer: "ast-governor",
    requiredMaxDepth: 2,
    maxConcurrentChildren: 2,
    agentMap,
    managerAgentMap,
    specialistAgents: specialists.map(
      (item) => `ast-${item.manager}-${item.id}`,
    ),
    assignedSkills: Object.fromEntries(
      agents.map((agent) => [agent.id, jsonSkill(assignedSkills, agent.id)]),
    ),
    activation: {
      mode: "codex-custom-agents",
      entrySkill: "agi-super-team-orchestrator",
      pluginOptional: true,
    },
    revisionMatchedReceipt: {
      status: "pending",
      required: true,
      configEnvironmentVariable: "CODEX_HOME",
      requiredFields: [
        "sourceRevision",
        "sourceDirty",
        "connectionSha256",
        "revisionMatched",
      ],
      mustUseCleanSourceRevision: true,
      requiredChecks: [
        "fresh-codex-home",
        "agents-discovered",
        "orchestrator-semantic-trigger",
        "ceo-manager-leaf-dispatch-observed",
        "governor-independent-review-observed",
      ],
    },
  };
}
