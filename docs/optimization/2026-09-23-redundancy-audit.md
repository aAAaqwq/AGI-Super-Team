# 冗余与质量审计（2026-09-23）

> **问题**：最新提交后，项目效果是否变差了？以及有多少冗余在拖累质量？
> **方法**：只列可复现的数字与命令。每条结论附证据。发现的核心问题分四类：**回归 / 体积 / 冗余 / 治理**。

---

## 结论先行

| # | 发现 | 严重度 | 状态 |
|---|---|---|---|
| 1 | **main 自 2026-09-21 起 CI 是红的** —— 加 skill 时漏了重新生成 catalog，3 项派生数据漂移 | 🔴 高 | ✅ 本次已修 |
| 2 | **CI 抓到了失败，但拦不住** —— branch protection 关闭，红的提交照样进 main | 🔴 高 | ❌ 未修（治理问题）|
| 3 | **`.git` = 160 MB，比整个工作区（~80 MB）大一倍** —— 历史里躺着 ~90 MB 早已删除的死重 | 🟠 中 | ❌ 未修（需 history rewrite）|
| 4 | **一个 16.33 MB 的回测原始 dump 仍在跟踪** —— 其结论已存在 5 KB 的 summary 里 | 🟠 中 | ❌ 未修 |
| 5 | **运行产物当源码提交** —— `skills/*/data/` + scan 结果 JSON，合计约 5.3 MB | 🟠 中 | ❌ 未修 |
| 6 | **834 个 skill 里 712 个（85.4%）未被任何配置引用** | 🟡 低（但影响 npm 包体积）| ❌ 未修 |
| 7 | **npm 包从 12.9 MB → 49 MB unpacked、1609 → 5026 文件**（v1.7.x 全量打包）| 🟡 低 | 有意为之（见 ADR-0008）|

**对"是否变差了"的回答**：**是，但变差的不是架构，是流程** —— 有人加了 content 却漏跑生成器，而 CI 未能阻止。
本次审计已修复 #1；#2 是根因，不修则同类事故会复发。

---

## 一、回归事件（已修复）

### 症状

```
$ npm test
FAILED (failures=3, skipped=1)

FAIL: test_generated_catalog_is_current_and_uses_portable_links
      AssertionError: 1 != 0 : STALE catalog/README.md
                              STALE catalog/skill-index.json
FAIL: test_machine_index_matches_markdown_membership_and_runtime_counts
      AssertionError: 833 != 834
FAIL: test_check_fails_when_baseline_is_missing_or_malformed
```

### 定位

```
64f9845a  2026-09-21  feat: add viral-product-demo skill   → CI failure  ← main 从这条开始红
410913ba  2026-09-18  release 1.6.1 → 1.7.1               → CI success
682a82af  2026-09-19  docs: 修正 Codex 深度 3 → 2          → CI success
```

该提交只加了 3 个文件，**没碰 `catalog/`、没碰 `config/team-manifest.json`**：

```
skills/viral-product-demo/SKILL.md                 |  83 +++
skills/viral-product-demo/references/script-template.md | 142 +++
skills/viral-product-demo/references/viral-structure.md | 108 +++
```

### 根因：一个 content 提交漏跑四个生成器

这个仓库的**派生数据是手工同步的**。新增一个 skill 要连带更新四处：

| 派生数据 | 漏跑后果 |
|---|---|
| `catalog/README.md` + `catalog/skill-index.json` | `build_skill_catalog.py --check` 报 STALE |
| `config/team-manifest.json` → `physicalSkillCount` | `validate:strict` 报计数不符 |
| `config/skill-quality-baseline.json` | `audit_skill_quality.py --check` 报 regression |
| `catalog/skill-quality.json` | 同上 |

而 `viral-product-demo` 本身还带了两个质量缺陷（**同一文件同时触发三项回归**）：

```
description 长度 = 262 字符（上限 180）        → description-over-180      294 → 295
description 缺触发词（use/when/for/适用/用于/触发）→ description-missing-trigger 264 → 265
```

> ⚠️ **这不是小事**：description 缺触发词 = **这个 skill 永远不会被 agent 选中**。
> 和此前修复的 C-suite incidence（`任务主要属于 X 的职责范围时调用`）是**同一类缺陷** ——
> 装了但不会触发。

### 修复动作（本次已做）

```bash
# 1. 重新生成三个 catalog 产物
uv run --python 3.11 --with 'PyYAML>=6.0,<7' --with 'jsonschema>=4.23,<5' \
  python scripts/build_skill_catalog.py
uv run ... python scripts/build_original_skills_index.py
uv run ... python scripts/audit_skill_quality.py

# 2. 改 description（262 → 94 字符，补触发词）—— 改内容，不抬基线
# 3. config/team-manifest.json: physicalSkillCount 833 → 834
```

**验证**：

```
npm test              → 477 tests, OK (skipped=1)
catalog --check       → 通过
audit_skill_quality   → report is current
audit_architecture    → 100/100
validate:strict       → SUMMARY errors=0 warnings=0
```

---

## 二、治理缺口（根因，未修）

### CI 检测到了，但没有任何东西阻止它

```
$ gh api repos/…/commits/64f9845a/check-runs
Test and validate repository contracts:  completed/failure   ← 确实红了
Test packed ubuntu-latest CLI …:          completed/success
Build and deploy GitHub Pages:            success             ← 照样部署
```

且 `main` 分支**未设保护**：

```
$ gh api repos/…/branches/main/protection
{"message":"Branch not protected", "status":"404"}
```

**后果**：红着 2 天没人发现 —— 因为 **Pages 部署成功、npm 发布成功**，表面看一切正常。

### 三个可选修法（按成本排序）

| 修法 | 成本 | 效果 |
|---|---|---|
| **A. 开 branch protection**，要求 `Test and validate repository contracts` 通过才可合 | 5 分钟（仓库设置） | 根治，但**会挡住直接 push 到 main 的工作流**（当前两个 agent 都直接 push） |
| **B. 加 pre-commit hook**：改 `skills/` 时自动跑生成器 | 半小时 | 治本，但只对本地生效，绕过 CI 的 agent 不受约束 |
| **C. 加一个"生成器新鲜度"的显式检查入口** ——`npm run build:all` 一条命令跑全部生成器 | 15 分钟 | **降低漏跑概率**，不强制 |

> **建议 B + C**：当前是"两个 agent 并行直接 push main"的形态，A 会打断它；
> 而 B/C 直接消除"忘记跑生成器"这个动作本身。

---

## 三、体积账本

```
工作区           ~80 MB        .git             160 MB   ← 是工作区的 2 倍
├─ skills/        69 MB        跟踪文件           5,364
├─ docs/         3.9 MB        npm 包 (unpacked)   49 MB   (v1.5 时 12.9 MB)
├─ plugins/      3.4 MB        npm 包 (tarball)  17.3 MB   (v1.5 时  4.7 MB)
├─ catalog/      1.6 MB        npm 文件数         5,026   (v1.5 时  1,609)
└─ agents/       1.6 MB
```

### 3.1 `.git` 里的死重（~90 MB，已从工作区删除但永久留在历史）

```
20.20 MB  skills/.trash/skillshare/.github/assets/demo.gif
16.33 MB  skills/5minbtc/backtest/results/backtest_20260527_2328.json   ← 仍在跟踪
15.87 MB  skills/documents/pptx/scripts/node_modules/@img/sharp-libvips-linux-x64/lib/libvips-cpp.so.8.17.3
 5.49 MB  skills/orchestra-research-skills/video-promo/…/public/music.wav
 4.85 MB  skills/orchestra-research-skills/docs/assets/promo.gif
 4.80 MB  skills/ClawBio-skills/genome-compare/data/manuel_corpas_23andme.txt.gz
 4.76 MB  skills/ClawBio-skills/genome-compare/data/george_church_23andme.txt.gz
 4.52 MB  skills/inference-optimizer/banner.png
 3.96 MB  skills/openclaw-crypto-ai-quant/docs/screenshots/grid-view.gif
 3.83 MB  skills/last30days-skill/assets/dog-original.jpeg
 2.69 MB  skills/last30days-skill/assets/aging-portrait.jpeg
```

复现命令：

```bash
git rev-list --objects --all \
  | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' \
  | awk '$1=="blob" {print $3, $4}' | sort -rn | head -12
```

**第一性原理**：**删除工作区文件不会减小 `.git`。** 这些对象一旦进过历史就永久存在，
只有 `git filter-repo` 重写历史才能回收 —— 代价是所有协作者必须重新克隆。

> **建议**：**暂时不做** history rewrite（当前有两个并行工作线，重写历史会打断它们）。
> 但**从现在起不再新增**：见 3.2。

### 3.2 仍在跟踪的运行产物（可立即处理，共约 21.6 MB）

| 路径 | 体积 | 性质 | 建议 |
|---|---|---|---|
| `skills/5minbtc/backtest/results/backtest_20260527_2328.json` | **16.33 MB** | v5.6 回测**原始逐笔 dump**。其 `stats` 段（48.6% 准确率等全部结论）**已被 `latest_summary.json`（5.1 KB）完整保留**。唯一独有的是 `predictions` 数组 | **删**（结论无损）|
| `skills/elon-tweets/*.json` × 4 | ~2.1 MB | `scan_output` / `scan_results` / `el_scan_result` / `el_scan_temp` —— 运行结果 | 删 + gitignore |
| `skills/*/data/` × 86 文件 | 3.2 MB | polymarket-profit(31) / healthcare-monitor(23) / crypto-hunt(9) / content-factory(9) 等**带日期的运行数据** | 删 + gitignore |
| `package-lock.json` × 8 | 0.5 MB | 依赖锁文件（子项目用） | 视情况 gitignore |

复现命令：

```bash
git ls-files | grep -iE "\.(json|jsonl|csv)$" | while read f; do wc -c < "$f"; done \
  | awk '{s+=$1} END {printf "%.1f MB / %d 文件\n", s/1048576, NR}'
# → 25.0 MB / 651 文件（其中配置/契约类是正当的）
```

### 3.3 npm 包增长是**有意的**（见 ADR-0008）

```
v1.5.0:  1,609 文件   12.9 MB unpacked    4.7 MB tarball
v1.7.1:  5,026 文件   49.0 MB unpacked   17.3 MB tarball
```

**原因**：此前只打包 `team-manifest` 里引用的 skill 的完整目录，其余 700+ skill **只带 `SKILL.md` 不带 `scripts/`、`references/`** —— 而那些正文里就写着"运行 `scripts/xxx.py`"。**装到 npm 后是一堆点了就报错的 skill。**

ADR-0008 权衡后选择"全量打包"。**这个决定是对的**（半个 skill 比大包更糟），
但它把 3.2 节那些**运行产物也一起带进了 npm 包** —— 这才是值得处理的冗余。

---

## 四、内容层冗余

```
835 个 skill 目录 / 834 个含 SKILL.md
  ├─ 被 config/ 引用：  122 个（14.6%）
  └─ 未被引用：         712 个（85.4%）
```

复现命令（引用来源含 `team-manifest.json` 的 `agents[].skills` 与各 `*-specialists.json`）：

```bash
python3 - <<'PY'
import json, re, pathlib
tm = json.load(open('config/team-manifest.json')); used = set()
for a in tm.get('agents', []):
    sk = a.get('skills') or {}
    for k in ('required','optional'): used.update(sk.get(k) or [])
for f in pathlib.Path('config').glob('*.json'):
    for m in re.finditer(r'"(?:skills|skill)"\s*:\s*\[([^\]]*)\]', f.read_text(encoding='utf-8')):
        used.update(re.findall(r'"([a-z0-9][a-z0-9-]*)"', m.group(1)))
all_ = {p.parent.name for p in pathlib.Path('skills').glob('*/SKILL.md')}
print(f'全部 {len(all_)} | 被引用 {len(used & all_)} | 未引用 {len(all_ - used)}')
PY
```

**重要的反面证据**：**同内容重复 = 0 组**（834 个 `SKILL.md` 的 SHA-256 无碰撞）。

```
完全同内容的 SKILL.md 组数: 0
```

> **所以"85% 未被引用"不等于"85% 是垃圾"，而是"这是一个通用 skill 库，不是团队专用包"。**
> 关键在于**它们与 `skills` 这个定位是否自洽** —— 如果这个仓库同时想当
> ①agent 团队契约 ②通用 skill 市场，那这 712 个是货；
> 如果只想当 ①，那它们是税（且已经体现在 npm 包体积上）。

**这是需要你拍板的定位问题，不是技术问题。**

---

## 五、建议的动作清单（按性价比排序）

| # | 动作 | 收益 | 成本 | 风险 |
|---|---|---|---|---|
| 1 | **加 `npm run build:all`** 一条命令跑全部生成器 + 在 CONTRIBUTING 写明"改 skills/ 后必须跑" | 消除"忘记同步派生数据"这类回归 | 15 分钟 | 无 |
| 2 | **加 pre-commit hook** 检测 `skills/` 变更并提示跑生成器 | 同上，且更早 | 30 分钟 | 可 `--no-verify` 绕过 |
| 3 | **删 `backtest_20260527_2328.json`（16.33 MB）**，在 `backtest-findings.md` 注明结论位置 | 工作区 −16 MB、npm 包 −16 MB | 10 分钟 | 低（结论已在 5 KB summary）|
| 4 | **给 `skills/*/data/` 加 .gitignore 并删除** 已提交的 86 个文件 + elon-tweets 的 4 个 scan JSON | 工作区 −5.3 MB、npm 包 −5.3 MB | 20 分钟 | 低 |
| 5 | **开 branch protection**（或至少让 CI 失败时通知） | 根治"红着没人知" | 5 分钟 | **会挡住直接 push main** —— 需先确认两个工作线的推送方式 |
| 6 | `git filter-repo` 重写历史回收 ~90 MB | `.git` 160 MB → ~70 MB | 数小时 + 协作者重克隆 | **高** —— 当前有并行工作线，建议暂缓 |
| 7 | 决定"通用 skill 库"还是"团队专用包" | 决定 712 个 skill 的去留 | 决策 | —— |

**我建议先做 1 + 3 + 4**：零风险、纯收益、且直接减小 npm 包（对使用者是真实的下载成本）。
5 需要你先确认推送方式；6 暂缓；7 是你的定位决策。

---

## 附：本次审计用到的复现命令

```bash
# 体积
du -sh skills docs plugins catalog agents
du -sh .git
git ls-files | wc -l

# 历史死重
git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' \
  | awk '$1=="blob" {print $3, $4}' | sort -rn | head -12

# 运行产物
git ls-files | grep -iE "\.(json|jsonl|csv)$" | while read f; do wc -c < "$f"; done \
  | awk '{s+=$1} END {printf "%.1f MB / %d\n", s/1048576, NR}'

# 回归
npm test
uv run --python 3.11 --with 'PyYAML>=6.0,<7' --with 'jsonschema>=4.23,<5' python scripts/build_skill_catalog.py --check
gh api repos/aAAaqwq/AGI-Super-Team/branches/main/protection
```
