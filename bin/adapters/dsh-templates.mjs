/**
 * DSH-native payloads for the DeepSeek Harness adapter.
 *
 * DSH composes an agent from three separate mechanisms, and each string here
 * feeds exactly one of them:
 *
 *   - the user-global instruction chain (advisory text, no capabilities),
 *   - the profile patch layer (re-enables the `skill-filesystem` row),
 *   - the agent preset (tools, prompt sections, delegation).
 *
 * Kept apart from `dsh.mjs` because the compositions are large opaque strings;
 * the adapter module only decides where they land.
 */

export const DSH_PRESET_ID = "ast-team";
export const DSH_DEFAULT_PROFILE = "web";

/** YAML comment markers — this file is parsed as a top-level YAML array. */
export const DSH_PATCH_BEGIN = "# AGI-SUPER-TEAM:DSH-PATCH:BEGIN";
export const DSH_PATCH_END = "# AGI-SUPER-TEAM:DSH-PATCH:END";

export const ORCHESTRATOR_SKILL_DIR = "agi-super-team-orchestrator";

function yamlText(value) {
  return JSON.stringify(String(value));
}

export function dshSkillRoot(dshRoot) {
  return `${dshRoot}/skills/agi-super-team`;
}

/**
 * The user patch layer. `dsh-web-app` disables the host `skill-filesystem` row
 * so presets own local discovery, which means a decomposed path never loads
 * skills on its own. Re-enabling that host row (rather than adding a second
 * provider inside the preset) registers local discovery into the skill
 * registry's global layer, which every agent reads regardless of preset.
 *
 * The installer writes this file whole. It never merges into an existing one:
 * a patch list is a single YAML document, so the shipped `[]` placeholder plus
 * appended entries would not parse. If the file already holds entries of your
 * own, the installer leaves it entirely alone.
 */
export function dshPatchPayload(dshRoot) {
  const inner = [
    DSH_PATCH_BEGIN,
    `# Managed by the AGI Super Team installer. Edits inside this block are`,
    `# overwritten on reinstall; add your own entries above or below it.`,
    `- id: skill-filesystem`,
    `  name: ${yamlText("@deepseek-ai/dsh-skill-filesystem")}`,
    `  disabled: false`,
    `  config:`,
    `    customSkillDirs:`,
    `      - ${yamlText(dshSkillRoot(dshRoot))}`,
    DSH_PATCH_END,
  ].join("\n");
  return `${inner}\n`;
}

function roleRoute(agent) {
  return `- \`ast-${agent.id}\`（${agent.name}）：${agent.trigger} 不适用：${agent.doNotUseWhen}`;
}

function specialistRoute(specialist) {
  return `- \`ast-${specialist.manager}-${specialist.id}\`（${specialist.name}）：${specialist.trigger} 不适用：${specialist.doNotUseWhen}`;
}

/**
 * The composed persona. Every `ast-*` role shares one preset, so this routing
 * block is what carries the CEO→C-suite→leaf hierarchy; the harness itself
 * enforces no per-role boundary.
 */
export function dshPersonaSuffix(packageRoot, agents, specialists, skillRoot) {
  const routes = agents.map(roleRoute);
  const leaves = specialists.map(specialistRoute);
  return [
    `你是 AGI Super Team 的协调会话，canonical 角色定义在 \`${packageRoot}/agents\`。`,
    ``,
    `## 角色路由`,
    ``,
    `- 先判级再选队：单点任务自己做完或只调一个最匹配的角色；跨两个以上 C-suite 领域才并行组队。`,
    `- 只能调用下列已安装角色；Manager 最多两个并发直属叶子，总深度不超过二；叶子与 Governor 不得继续创建子 Agent。`,
    `- 重大结论、发布、资金、法律、安全与完成声明必须由 \`ast-governor\` 独立复核证据，被审方不能自证。`,
    `- 登录、发布、部署、凭证、资金、法律承诺和其他不可逆动作必须由用户最终批准。`,
    `- 不得声称未执行的测试、运行、浏览、部署或委派结果。`,
    ``,
    ...routes,
    ...(leaves.length ? [``, `## 直属叶子（按需装载）`, ``, ...leaves] : []),
    ``,
    `开始前按需读取 \`${skillRoot}/${ORCHESTRATOR_SKILL_DIR}/SKILL.md\`；它决定是否组队、通用任务包与人工批准契约。`,
  ].join("\n");
}

/**
 * The agent-plane composition. Mirrors the shipped `standard` preset's
 * model-facing rows, minus the goal/workflow/ralph machinery the team contract
 * does not need. Everything host-plane (sandbox, approval stack, persistence,
 * model route, the `subagents` registry) stays in the host composition —
 * a preset must not own those.
 */
export function dshAgentPreset(packageRoot, agents, specialists, skillRoot) {
  const prefix = dshPersonaSuffix(packageRoot, agents, specialists, skillRoot);
  return `# AGI Super Team｜DeepSeek Harness agent preset
#
# Generated from ${packageRoot}; rerun the AGI Super Team installer to update.
#
# This is a copy of the shipped \`standard\` preset's model-facing rows with the
# AGI Super Team routing persona. It is a copy on purpose: a user preset under
# \`<dshHome>/.agent-presets\` keeps working across DSH upgrades, while editing
# the shipped \`standard\` preset would be overwritten (and corrupting it would
# disable the mode entirely).
#
# Skills arrive through the HOST row, not from here. \`dsh-web-app\` disables the
# host \`skill-filesystem\` row so presets own local discovery; the adapter's
# \`cordis.patch.yml\` re-enables it with \`customSkillDirs\`, which registers into
# the skill registry's global layer that every agent reads. Adding a second
# \`skill-filesystem\` row here would register a competing provider.
#
# Known limitation: DSH gives no per-role tool restriction. Every \`ast-*\` role
# in the routing below runs on this one composition, and the C-suite/leaf
# boundary is enforced by the persona plus the host approval stack rather than
# by the harness. See the connection spec's \`limitations\`.

- id: persona
  name: '@deepseek-ai/dsh-persona'
  config:
    prefix: ${JSON.stringify(prefix)}

- id: agent-instructions
  name: '@deepseek-ai/dsh-agent-instructions'
  config:
    maxBytes: 65536

# ── shell ───────────────────────────────────────────────────────────────────

- id: tool-bash
  name: '@deepseek-ai/dsh-tool-bash'
  disabled: !!js process.platform === 'win32'

- id: tool-pwsh
  name: '@deepseek-ai/dsh-tool-pwsh'
  disabled: !!js process.platform !== 'win32'

# ── filesystem ──────────────────────────────────────────────────────────────

- id: tool-fs
  name: '@deepseek-ai/dsh-tool-fs'

- id: tool-fs-search
  name: '@deepseek-ai/dsh-tool-fs-search'
  config:
    sampleOverCapGlobResults: false

# ── background jobs ────────────────────────────────────────────────────────

- id: tool-jobs
  name: '@deepseek-ai/dsh-tool-jobs'

# ── skills ──────────────────────────────────────────────────────────────────

# The catalog and loader only; local-root discovery is the patched host row.
- id: tool-skill
  name: '@deepseek-ai/dsh-tool-skill'

# ── plan mode ───────────────────────────────────────────────────────────────

- id: planning
  name: cordis:group
  group: true
  isolate:
    planMode: true
  config:
    - id: plan-mode
      name: '@deepseek-ai/dsh-plan-mode'

# ── compaction ──────────────────────────────────────────────────────────────

- id: compaction
  name: cordis:group
  group: true
  isolate:
    compaction: true
    toolResultPruner: true
  config:
    - id: compaction-basic
      name: '@deepseek-ai/dsh-compaction-basic'

    - id: command-compact
      name: '@deepseek-ai/dsh-command-compact'

    - id: tool-result-pruner
      name: '@deepseek-ai/dsh-compaction-tool-result-pruner'
      config:
        thresholdChars: 8192
        headChars: 4096
        tailChars: 1024

# ── delegation ──────────────────────────────────────────────────────────────

# The \`subagents\` registry and its spawn/fork backends are host-plane; this
# preset contributes the delegation TOOLS that resolve it. The CEO→C-suite→leaf
# chain depends on these rows.
- id: delegation
  name: cordis:group
  group: true
  isolate:
    workflowEngine: true
  config:
    - id: tool-subagent-control
      name: '@deepseek-ai/dsh-tool-subagent-control'

    - id: tool-subagent-list-agents
      name: '@deepseek-ai/dsh-tool-subagent-control/list-agents'

    - id: tool-subagent
      name: '@deepseek-ai/dsh-tool-subagent'
      config:
        provider: spawn
        toolName: subagent
        modelSelectionSettings: true
        backgroundMode: continuable

    - id: tool-subagent-fork
      name: '@deepseek-ai/dsh-tool-subagent'
      config:
        provider: fork
        toolName: subagent_fork
        backgroundMode: continuable

# ── remaining model-facing rows ─────────────────────────────────────────────

- id: tool-ask-user
  name: '@deepseek-ai/dsh-tool-ask-user'

- id: tool-todo
  name: '@deepseek-ai/dsh-tool-todo'
  config:
    allowParallelInProgress: true

- id: tool-web
  name: '@deepseek-ai/dsh-tool-web'
  config:
    fetch: true
    searchTimeoutMs: 60000

- id: present
  name: '@deepseek-ai/dsh-tool-present'
`;
}

export function dshPresetMetadata() {
  return [
    "name: AGI Super Team",
    "description: 按 CEO→C-suite→Leaf→Governor 路由复杂任务的团队编排 Agent；需要跨职能并行、独立复核或完整团队交付时使用。",
    "",
  ].join("\n");
}

export function dshOrchestratorSkill(packageRoot, skillRoot) {
  return `---
name: ${ORCHESTRATOR_SKILL_DIR}
description: 在 DeepSeek Harness 中按 CEO→C-suite→Leaf→Governor 路由复杂任务；需要跨职能并行、独立复核或完整团队交付时使用。
---

# AGI Super Team｜DeepSeek Harness Adapter

这是 DSH 的运行时包装 Skill。开始前必须读取 canonical Skill：\`../orchestrate-agi-super-team/SKILL.md\`，并按需读取其 references。canonical Skill 决定是否组队、通用任务包、Governor 和人工批准契约；本文件只补充 DSH 的调度方式。

你是会话中的 CEO 协调者。先定义结果、约束和验收，再按任务选择最小充分团队。

- 通过 \`subagent\`（一次性/可续）与 \`subagent_control\`（\`send_message\` / \`interrupt_agent\` / \`list_agents\`）委派。子 Agent 加入父 Agent 的 preset 组合，因此与父 Agent 看到相同的工具与提示区段。
- CEO 只能调用 C-suite、PE 和 Governor。
- Manager 只能调用 persona 路由中列出的直属叶子，最多两个并发。
- Leaf 和 Governor 不得继续创建 Agent，总深度不得超过二。
- Governor 必须独立审查重大结论；主 Agent 保留其有证据支持的异议。
- 登录、发布、部署、资金、凭证、法律承诺和其他不可逆动作必须由用户最终批准。
- 最终回传决策、证据、验证、限制、剩余风险和下一步。

canonical 角色定义在 \`${packageRoot}/agents\`；DSH 不给每个角色单独的工具边界，角色区分由 preset 的 persona 路由与宿主审批栈共同承担。
`;
}

export function dshRoleEnvelope(agent, group) {
  const boundary = group?.specialists?.length
    ? `你是受限管理节点，只能调用 \`ast-${agent.id}-*\` 直属叶子和 canonical 角色引用，最多两个并发，总深度为二。`
    : "你是叶子 Agent，不得创建子 Agent。";
  return [
    `# ${agent.name}`,
    ``,
    `> 由 DSH Adapter 从 canonical \`${agent.path}\` 生成；canonical 内容仍由源目录拥有。runtimeEvidence: pending。`,
    ``,
    `DSH 不提供逐角色工具边界：真实约束来自 preset 的 persona 路由与宿主审批栈。${boundary}`,
  ].join("\n");
}
