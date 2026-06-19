# Stage 2.1B Multi-round Post-Coordination Regenerated Conflict Evidence

生成日期：2026-06-20
执行者：Codex

## 边界

No LLM / no evolution / no optimizer。Stage 2.1B 只做固定轮数 deterministic evidence gate，不生成 coordination operator，不修改 BaseOpt，不修改 benchmark objective，不修改 MetaBox source。

## 指标诚实性

`proposal_consensus_collapse_ratio_mean` 仍是 same-round proposal-set collapse。`longitudinal_conflict_reduction_ratio` 使用下一轮 regenerated conflict，不是 same-round conflict-after，也不是 optimizer-loop performance claim。

## Panel 摘要

- settings: 36
- runs: 540
- rounds per run: 5
- summary rows: 540

| Operator | Mean longitudinal reduction | Mean proposal collapse | Mean persistence | Mean objective improvement / FE |
|---|---:|---:|---:|---:|
| NoCoordination | 0.000000 | 0.000000 | 1.000000 | 0.000000 |
| AverageConsensus | 0.000000 | 1.000000 | 1.087599 | 0.422936 |
| BestRewardSelection | 0.001871 | 1.000000 | 1.040518 | 0.224444 |
| WeightedConsensus | 0.000387 | 1.000000 | 1.048443 | 0.239048 |
| ConflictDampening | 0.000000 | 1.000000 | 1.086514 | 0.429053 |

## 通过标准

- 每个 baseline 独立运行，cross-baseline evaluations 不共享。
- FE_total 等于 FE_grouping + FE_proposal + FE_coordination_extra + FE_repair。
- coordination 只写 shared variables。
- no LLM / no evolution / no optimizer / no MetaBox source mutation。
