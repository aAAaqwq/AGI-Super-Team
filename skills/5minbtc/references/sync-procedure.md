# 5minbtc 仓库同步 (AGI-Super-Team)

## 路径映射 (两台机器)
| 角色 | hermes 机 (Linux) | Mac (daniel 本机) |
|------|------------------|------------------|
| 运行副本 (源) | `/home/aa/.hermes/profiles/cqo/skills/5minbtc/` | `~/.claude/skills/5minbtc/` |
| 共享仓库 | `/home/aa/clawd/repos/AGI-Super-Team/` | `~/AGI-Super-Team/` |

⚠️ 仓库分支是 **`main`** (不是 master)。下面命令按 hermes 机写, Mac 上把两个路径换成上表右侧即可。

## 同步命令
```bash
# 1. rsync 本地最新版到共享仓库 (排除运行时数据和日志)
#    -u 只允许"源更新"覆盖 — 防止本机旧副本反向覆盖仓库里更新的文件
rsync -avu \
  --exclude='data/' --exclude='logs/' --exclude='reviews/' --exclude='archive/' --exclude='__pycache__/' \
  --exclude='*.jsonl' --exclude='*.jsonl.*' --exclude='*.gz' \
  /home/aa/.hermes/profiles/cqo/skills/5minbtc/ \
  /home/aa/clawd/repos/AGI-Super-Team/skills/5minbtc/

# 2. 提交推送
cd /home/aa/clawd/repos/AGI-Super-Team
git add skills/5minbtc/
git commit -m "sync(skills/5minbtc): <变更简述>"
git push origin main
```

## 重命名/删除文件时
rsync **不带 `--delete`**, 所以删掉/改名的文件不会自动从仓库移除, 必须显式删:
```bash
git rm skills/5minbtc/<旧文件名>
```

## Commit message 惯例
`sync(skills/5minbtc): <版本> 全量同步 — 引擎+回测+复盘+参考文档`

## 同步内容
- 引擎 (`5minbtc-engine*.py`), 日志模块 (`5minbtc-log.py`), 新闻模块 (`5minbtc-news.py`)
- `SKILL.md` (含冲突裁决规则同步)
- `backtest/` (含脚本、结果 JSON、README)
- `references/` (含黑天鹅防御、Dreaming 恢复、Binance 地理、性能历史)
- `review-*.md` 全量复盘记录

## 排除
- `data/`, `__pycache__/` (运行时产物)
- `logs/`, `reviews/` (归档产物, 仅本地保留)
- `archive/` (旧版本引擎, 仅本地保留, 不上传共享仓库)
- `*.jsonl`, `*.jsonl.*.gz` (海量预测日志, 按需同步)

## 推送前检查
- 不含敏感数据 (密钥、API 凭证)
- 不含市场数据 (data/)
- 不含海量日志 (*.jsonl.gz)
