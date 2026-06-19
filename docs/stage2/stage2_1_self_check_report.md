# Stage 2.1 Multi-setting Conflict Evidence Gate

生成日期：2026-06-20
执行者：Codex

## 边界

No LLM / no evolution / no optimizer。Stage 2.1 只扩展 synthetic multi-setting evidence panel，不生成 coordination operator，不修改 BaseOpt，不实现 scheduler/controller。

## 指标诚实性

`proposal_consensus_collapse_ratio` 仍然只是当前 proposal set 的 consensus collapse 诊断，不是 longitudinal conflict reduction。`post_coordination_regenerated_conflict` 是 Stage 2.1 的 deterministic regenerated-conflict proxy，用于 evidence gate，不是 SOTA claim。

## Panel 摘要

- settings: 45
- runs: 135
- operators: 5
- summary rows: 675

| Operator | Mean proposal collapse | Mean regenerated conflict | Mean persistence | Low-overlap regressions |
|---|---:|---:|---:|---:|
| NoCoordination | 0.000000 | 0.246519 | 0.800000 | 0 |
| AverageConsensus | 0.800000 | 0.000000 | 0.000000 | 0 |
| BestRewardSelection | 0.800000 | 0.000000 | 0.000000 | 0 |
| WeightedConsensus | 0.800000 | 0.000000 | 0.000000 | 0 |
| ConflictDampening | 0.800000 | 0.000000 | 0.000000 | 0 |

## 通过标准

- JSON/CSV/report 三类产物可生成，且使用 LF line endings。
- 所有 baseline 作为独立 method run 汇报 FE，不共享 cross-baseline evaluations。
- no-overlap / low-overlap case 必须显式标记，不能被伪装成 conflict-resolution 成功。
- 该阶段仍不进入 LLM/evolution/operator discovery。
