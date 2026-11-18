# AGI Skills Atlas · AGI 技能星图

把仓库里的全部 Skills 变成一张可检索、可分享、面向人和 Agent 的星图。

- 站点：<https://aaaaqwq.github.io/AGI-Super-Team/skills-atlas/>
- 数据源：`catalog/skill-index.json`（853 个技能、14 个分类）
- 内容源：每个技能的 `skills/<id>/SKILL.md`
- 输出：`docs/skills-atlas/`，由 Pages 工作流在 CI 中生成，**不提交生成物**

## 它做什么

- **一一对应**：目录以 `catalog/skill-index.json` 为唯一清单；每个条目读取对应的 `SKILL.md`，不另建平行列表。
- **清晰分类**：14 个主分类、分类计数、原创标记（65 个 project-original 技能）。
- **快速检索**：⌘K / `/` 聚焦搜索；按领域、原创、名称排序筛选；结果分页渲染，避免一次性塞入 853 张卡片。
- **详情阅读**：Markdown 渲染、代码块复制、元数据、复制给 AI、下载 `.md`、跳转 GitHub 原文。
- **本地上传**：拖入或粘贴 `SKILL.md`，只在浏览器本地保存，可导出 JSON；不会上传到服务器。
- **AI 友好**：同时产出 `llms.txt`、`llms-full.txt`、`data/index.json`、`data/skills/<id>.json` 和 `data/originals.json`。
- **主题与动效**：浅色 / 深色、系统偏好、View Transition、星空 canvas、卡片聚光、滚动揭示；尊重 `prefers-reduced-motion`。

## 本地构建

```bash
python3 skills-atlas/scripts/build.py
```

默认读取仓库根的 `catalog/skill-index.json` 与 `skills/`，输出到 `docs/skills-atlas/`。

只做构建校验：

```bash
python3 skills-atlas/scripts/build.py --out /tmp/skills-atlas-preview
```

## 本地预览

```bash
python3 -m http.server 8787 -d docs
# 打开 http://localhost:8787/skills-atlas/
```

不要直接双击 `index.html`：页面通过 `fetch` 读取 `data/index.json`，`file://` 会被 CORS 拦截。

## 部署

现有 `.github/workflows/pages.yml` 在 `npm run test:site` 和 `build_site_data.py` 之后增加一步：

```yaml
- name: Build Skills Atlas
  run: python3 skills-atlas/scripts/build.py --out docs/skills-atlas
```

随后整个 `docs/`（包含 `docs/skills-atlas/`）作为 Pages artifact 上传。`docs/skills-atlas/` 是生成目录，已加入 `.gitignore`。

## 配置

编辑 `skills-atlas/atlas.config.json`：

- `site`：标题、描述、仓库与 Pages URL。
- `categories`：14 个分类的中文名、中文描述、浅色/深色强调色。
- `featured`：精选技能 ID，最多 6 个。
- `private_skills`：只保留索引、不发布正文的技能 ID。
- `exclude_skills`：完全排除的技能 ID。

分类的英文名、英文描述与计数来自 `catalog/skill-index.json`，不在配置里重复维护。

## 数据与安全

- 构建时会做一次防御性脱敏：常见 token / API key / 私钥 / URL 凭据会被替换为 `[REDACTED_*]`；`/Users/<name>`、`/home/<name>`、`~/.zshrc`、`~/.openclaw`、`/opt/data` 会归一化。
- 这不是完整的安全审计。正式发布前仍应审查 `SKILL.md` 内容；需要完全隐藏正文的技能请加入 `private_skills`。
- 上传功能完全在浏览器内解析和存储（localStorage），不会向任何服务器发送文件。
- 渲染 Markdown 时先经过 DOMPurify，再补充外链 `rel`、图片懒加载、表格横向滚动和代码复制按钮。
- CSP 通过 `<meta http-equiv="Content-Security-Policy">` 限制为同源脚本与数据。

## 目录

```text
skills-atlas/
├── atlas.config.json      # 站点与分类配置（单一事实源）
├── scripts/build.py       # 构建器（仅 Python 标准库）
└── src/
    ├── index.html         # 页面骨架
    ├── styles.css         # Celestial Apple 设计系统
    ├── app.js             # 检索、详情、上传、主题、动效
    ├── theme.js           # 首屏主题引导（避免 FOUC）
    ├── assets/favicon.svg
    └── vendor/            # marked (MIT) + DOMPurify (Apache-2.0 / MPL-2.0)
```

## Vendor

- [marked](https://github.com/markedjs/marked) v12.0.2 — MIT
- [DOMPurify](https://github.com/cure53/DOMPurify) v3.2.4 — Apache-2.0 / MPL-2.0

两者均自托管，避免运行时外部依赖。
