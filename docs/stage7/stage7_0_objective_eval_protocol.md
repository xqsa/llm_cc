# Stage 7.0 Objective-Level Large-Scale Evaluation Protocol Lock

创建日期：2026-06-21
执行者：Codex
阶段边界：Stage 7.0 只锁定 objective-level evaluation protocol，不实现 objective-loop runner，不跑 objective benchmark，不调用 LLM，不生成新候选，不修改 selected operator，不做 evolution/search，不做 no test-feedback tuning，不修改 BaseOpt，也不是 not a performance claim、not an objective-value performance claim 或 not a SOTA claim。

## 1. Goal

Stage 7.0 的目标是把 LOCO-LSGO 从 Stage 6.1 的 sealed coordination diagnostics 推向真正的大规模 objective-level evaluation，但本阶段只做协议锁。

要锁定的最终在线方法是：

```text
LOCO-CC = fixed BaseOpt + overlapping decomposition + frozen selected_loco_operator
          + online shared-variable conflict coordination
          + global objective evaluation with full FE accounting
```

Stage 7.0 不证明 LOCO-CC 在大规模问题上有效。它只定义 Stage 7.1/7.2 应该如何证明。

## 2. Objective Loop Contract

Stage 7.1 之后的 objective loop 必须遵循：

```text
objective f(x)
-> oracle grouping / detected grouping
-> fixed BaseOpt produces subcomponent proposals
-> online shared-variable conflict states are constructed
-> frozen selected_loco_operator coordinates shared variables only
-> non-shared variables follow standard fixed BaseOpt / CC update
-> global candidate is merged
-> global objective evaluation is recorded
-> FE ledger is updated
```

关键边界：

```text
BaseOpt 是 fixed BaseOpt
selected operator 是 frozen selected_loco_operator
LOCO 不能选择 BaseOpt
LOCO 不能修改 BaseOpt
LOCO 不能生成 optimizer/controller/scheduler
LOCO 只作用于 shared variables
```

## 3. Required Baselines

Stage 7 objective-level comparison 必须至少包含：

```text
identity_no_coord
simple_consensus
weighted_consensus
best_reward_select
selected_loco_operator
```

`best_reward_select` 是必要 baseline，因为 Stage 6.1 的 primary diagnostic 是 `distance_to_best_reward_proposal`。如果不比较它，无法说明 selected LOCO operator 是否超出简单 winner rule。

## 4. Required Large-Scale Panels

Stage 7.1/7.2 的 synthetic panel 至少要覆盖：

```text
synthetic_no_overlap_panel
synthetic_low_overlap_panel
synthetic_conflicting_overlap_panel
synthetic_high_overlap_panel
```

建议首批维度：

```text
D = 500, 1000
```

no-overlap / low-overlap panel 是 safeguard，不是可选装饰。它们用于确认 LOCO 不会在没有 shared-variable conflict 的场景里明显退化。

真实 benchmark 可作为后续 optional panel：

```text
CEC2013 F13/F14 optional
```

其中 F13/F14 必须继续遵守已有 CEC2013 LSGO semantics boundary。

## 5. Required Metrics

Objective-level metrics：

```text
final_best_objective
best_so_far_curve
anytime_auc
mean_std_over_seeds
win_tie_loss_vs_baselines
```

Mechanism-level metrics：

```text
conflict_intensity_over_time
proposal_disagreement_over_time
shared_variable_oscillation
coordination_update_size
distance_to_best_reward_proposal
shared_conflict_frequency
```

机制指标必须和 objective metrics 一起报告。否则即使 objective value 改善，也不能说明改善来自 shared-variable conflict coordination。

## 6. FE Accounting

Stage 7 必须使用新的 objective-level FE identity：

```text
FE_total = FE_grouping
         + FE_proposal
         + FE_coordination_extra
         + FE_repair
         + FE_global_objective
```

必须记录：

```text
FE_grouping
FE_proposal
FE_coordination_extra
FE_repair
FE_global_objective
FE_total
```

所有 methods 必须 same FE budget，cross-method evaluations 不共享，所有额外 FE 都计数。

## 7. Grouping Reports

Stage 7 必须把以下两类结果分开：

```text
oracle grouping
detected grouping
```

oracle grouping 用于隔离 coordination operator 本身的效果。detected grouping 用于评估完整 pipeline 在 decomposition error 下的实际表现。两者不能混在一个 claim 里。

## 8. Forbidden Scope

Stage 7.0 preserves：

```text
no LLM call
no new candidate generation
no selected-operator revision
no evolution/search run
no objective benchmark run
no test-feedback tuning
no BaseOpt modification
no optimizer/controller/scheduler generation
not a performance claim
not an objective-value performance claim
not a SOTA claim
```

Stage 7.0 does not run objective benchmark and does not implement the objective-loop runner.

## 9. Allowed Claims

Stage 7.0 只能 claim：

```text
objective-level evaluation protocol is locked
LOCO-CC objective-loop contract is specified
required baselines, panels, metrics, and FE accounting are defined
Stage 7.1 is ready to implement a minimal objective-loop pilot
```

不能 claim：

```text
objective-value improvement
large-scale benchmark success
SOTA improvement
BaseOpt improvement
optimizer generation
```

## 10. Next Step

Stage 7.0 的 next status：

```text
READY_FOR_STAGE7_1_MINIMAL_OBJECTIVE_LOOP_PILOT
```

下一步应该是：

```text
Stage 7.1: Minimal LOCO-CC Objective Loop Pilot
```

paper claim polishing should wait for Stage 7.1/7.2 evidence if the paper's central claim is objective-level large-scale optimization effectiveness.
