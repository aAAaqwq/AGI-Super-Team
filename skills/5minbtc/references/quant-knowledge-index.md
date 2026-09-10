# Quant Knowledge Bank Index

> 50 轮深度蒸馏（2026-05-23），14 份报告（R01–R14，约 80 KB）。
>
> ⚠️ **原始路径 `~/.hermes/profiles/cqo/quant-knowledge/` 已不存在**（2026-09-10 实测）。
> **本 skill 的 `reports/` 是唯一存活副本**，也是权威位置；AGI-Super-Team 仓库同步同一份。
> 下表文件名已与 `reports/` 实际文件核对一致（原先 R07/R10 两行写错了文件名）。

| 文件 | 主题 | 对 5minbtc 的可用点 | 状态 |
|------|------|-------------------|------|
| R01-factor-theory.md | Alpha101, IC衰减, Barra | IC 衰减监控方法；LLM 因子挖掘需防拥挤度 | 未落地 |
| R02-strategy-theory.md | OU过程, 协整, Kalman, OFI | Kalman 滤波动态参数 → 替代固定 EMA 权重 | 未落地 |
| R03-crypto-quant-defi.md | 资金费率, 链上, MEV | 资金费率极值=过热信号；HODL Waves 长周期 | 未落地 |
| R04-portfolio-theory.md | BL/HRP/Kelly | Kelly 分数下注 → 最优仓位大小框架 | 未落地 |
| R05-ml-quant-trading.md | LightGBM, TFT, RL | TFT 多时间尺度注意力；Purged K-Fold 防泄露 | 未落地 |
| R06-data-sources.md | Alt Data全景, 加密数据 | P0 免费源: Arkham(鲸鱼), Binance WS(OFI), Deribit(IV) | 部分（OFI） |
| R07-frontier-research-2024-2026.md | LLM因子, AI Agent | AlphaAgent 开源可用；RFT 技术；拥挤度风险 | 未落地 |
| R08-options-volatility.md | Greeks, 曲面, 隐含分布 | DVOL-RV spread → 波动率 regime 信号 | 未落地 |
| R09-market-microstructure.md | LOB, OFI, Kyle, Almgren | **OFI 5min R²~15-25%**；Microprice 优于 mid | **✅ 已落地（v6.0）** |
| R10-risk-management-frontier.md | CVaR, EVT, Regime, 压测 | HMM regime 检测 → regime-aware 仓位；GPD 尾部止损 | 未落地 |
| R11-institutional-methodology.md | Simons, Citadel, Two Sigma | 信号仪表板 + 衰减检测 + 弱信号组合；DSR 防过拟合 | 未落地 |
| R12-integration-blueprint.md | 知识图谱+升级蓝图 | 完整 5 阶段升级路径，P0→P2 优先级 | 路线图 |
| R13-accuracy-optimization-plan.md | 178笔回盘+优化方案 | bull bias 根因分析；Phase1 修复 | ⚠️ 针对 v4.x，已过时 |
| R14-engine-audit-report.md | 顶尖量化审查 | 4 个 Critical 缺陷（共线指标/过拟合/regime盲区/阈值硬编码） | 历史：v5.0 架构基础 |

## P0 升级优先级（来自 R12）—— 进度

1. ✅ **OFI 微结构因子** —— **已落地**：v6.0 引擎方向由真 OFI 净流一票决定。
   ⚠️ 但落地的是 **taker 买卖失衡**（`2*(tb/v)−1`），**不是** R09 说的订单簿 OFI；
   且只覆盖 Binance 现货单一市场 —— 见 [pitfalls.md #19](pitfalls.md)
2. ⬜ **免费数据源接入** —— Arkham(鲸鱼追踪) / Binance WS(LOB) / Deribit API(IV)
3. ⬜ **信号仪表板** —— 监控所有因子 IC/衰减率（Simons 哲学核心实践）

> **这份索引的价值 = 一份尚未做完的升级路线图**，不是历史存档。
> P0#1 已兑现但打了折扣（见 pitfalls #19）；P0#2/#3 与 R02/R04/R05/R10 仍是有效方向。
> **例外**：R13 是针对 v4.x 的优化方案，其结论已被 v5.9 对抗审查取代，不要当作现行依据。

## Delegate Research Pattern（研究委派经验，仍有效）

- **超时风险**：>35 次 web_search 的委派研究容易撞 600s 超时。缓解：拆成更小的批次，
  或直接用领域知识 + 已收集的搜索结果写报告。
- **产出不完整**：委派有时只回搜索轨迹、不回成文报告。缓解：基于已收集的搜索上下文自行成文。
