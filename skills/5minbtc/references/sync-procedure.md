# 5minbtc 仓库同步 (AGI-Super-Team)

## 路径映射 (两台机器)

| 角色 | hermes 机 (Linux) | Mac (daniel 本机) |
|------|------------------|------------------|
| 运行副本 (源) | `/home/aa/.hermes/profiles/cqo/skills/5minbtc/` | `~/.claude/skills/5minbtc/` |
| 共享仓库 | `/home/aa/clawd/repos/AGI-Super-Team/` | `~/AGI-Super-Team/` |

⚠️ 仓库分支是 **`main`**（不是 master）。下面命令按 hermes 机写，Mac 上把两个路径换成上表右侧即可。

## 同步命令

```bash
# 1. rsync 源码到共享仓库
#    -c 按「内容校验和」比较, 不看 mtime
rsync -avc \
  --exclude='data/' --exclude='/archive/' --exclude='reviews/' --exclude='__pycache__/' \
  --exclude='logs/*.jsonl' --exclude='logs/*.jsonl.*' \
  --exclude='backtest/results/' \
  /home/aa/.hermes/profiles/cqo/skills/5minbtc/ \
  /home/aa/clawd/repos/AGI-Super-Team/skills/5minbtc/

# 2. 校验：必须只有「刻意排除的东西」有差异
diff -rq ~/.claude/skills/5minbtc/ ~/AGI-Super-Team/skills/5minbtc/ \
  | grep -v 'logs/5minbtc-log.jsonl'     # 只应剩下 live 日志这一条

# 3. 提交推送
cd /home/aa/clawd/repos/AGI-Super-Team
git add -A skills/5minbtc/
git commit -m "sync(skills/5minbtc): <变更简述>"
git pull --rebase origin main    # 另一台机器可能已推过
git push origin main
```

### 为什么用 `-c` 而不是 `-u`

`-u`（只允许源更新覆盖）是为了防止本机旧副本反向覆盖仓库里更新的文件 —— **这个动机没错，但判据错了**：
`-u` 比的是 **mtime**，而 git 的 `rebase` / `checkout` / `clone` 都会**重写工作区文件**，
把仓库副本的 mtime 顶得比源还新。此时 `-u` 会**静默跳过真实改动**，只打印 `Skip newer`，看起来一切正常。

实际踩过（2026-09-10）：`git pull --rebase` 后 rsync 对 5 个 `scripts/*.py` 报 `Skip newer`，
但 `diff` 显示内容其实一致 —— 那次侥幸没事，但同一机制会在真有改动时静默漏同步。

`-c` 用内容校验和判断，与 mtime 无关，既保留"不反向覆盖"的效果，又不会漏。
代价是要读全部文件（本 skill 约 1MB，可忽略）。

**兜底原则：无论用什么参数，同步后必须跑一次 `diff -rq` 校验。**

## 重命名/删除文件时

rsync **不带 `--delete`**，所以删掉/改名的文件不会自动从仓库移除，必须显式删：

```bash
git rm skills/5minbtc/<旧文件名>
```

（2026-09-10 引擎改名 `-v5.7.py` → `-v6.0.py` 时即如此处理。）

## 同步内容 / 排除

**同步**：引擎 `5minbtc-engine*.py`、`5minbtc-log.py`、`5minbtc-news.py`、`SKILL.md`、
`README.md`、`.env.example`、`.gitignore`、`references/`、`scripts/`、`backtest/`、`reports/`、
**`logs/archive/*.jsonl.gz`**（月度压缩归档）。

**排除**：

| 排除项 | 原因 |
|--------|------|
| `logs/*.jsonl`（live） | 每 5 分钟追加，进 git 会产生巨大且无意义的 diff |
| `data/`、`backtest/results/` | 运行时产物 / 回测产物 |
| `reviews/` | 该目录实际不存在（见 [archive.md](archive.md)） |
| `/archive/` | 旧版本引擎（本地不保留，只留 archive.md 文字归档） |
| `__pycache__/` | Python 缓存 |

> ⚠️ `--exclude='/archive/'` **必须带前导 `/`**（锚定到传输根）。
> 写成 `--exclude='archive/'` 会把 `logs/archive/` 一起排掉，日志归档就再也同步不上去了。

## 日志归档入库的 .gitignore 要点

仓库根的 `.gitignore` 有 `logs/`（会匹配任意层级的 `logs/` 目录）。**父目录被排除时，只写 `!文件` 是无效的**，必须逐级反忽略目录本身：

```gitignore
!skills/5minbtc/logs/
skills/5minbtc/logs/*
!skills/5minbtc/logs/archive/
!skills/5minbtc/logs/archive/*.gz
```

skill 内还有一份嵌套 `.gitignore`（同样忽略 `*.gz`），也需加 `!logs/archive/` + `!logs/archive/*.gz`。两处都改完，用下面命令确认（`git add -n` 是权威判据，`check-ignore` 的退出码在负向规则下会误导）：

```bash
cd ~/AGI-Super-Team
git add -n skills/5minbtc/logs/          # 应只列出 .gz；live jsonl 不应出现
```

## Commit message 惯例

`sync(skills/5minbtc): <版本> 全量同步 — 引擎+回测+复盘+参考文档`

## 推送前检查

- 不含敏感数据（密钥、API 凭证）—— 特别确认没把 `~/bb-auto/prediction.env` 带进来
- 不含市场数据（`data/`、`backtest/results/`）
- 不含 live 日志（只应有 `logs/archive/*.jsonl.gz`）
- `diff -rq` 校验通过（见上文第 2 步）
