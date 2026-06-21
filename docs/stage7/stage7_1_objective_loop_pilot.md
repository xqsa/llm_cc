# Stage 7.1 Minimal LOCO-CC Objective Loop Pilot

创建日期：2026-06-21
执行者：Codex
阶段边界：Stage 7.1 在 Stage 7.0 protocol 下实现并运行一个最小 LOCO-CC objective loop pilot。它使用 fixed BaseOpt proposal generator、synthetic sphere objective、frozen selected_loco_operator 和完整 `FE_global_objective` 计数。它不是大规模 benchmark，不是 not a final objective-value performance claim，也不是 not a SOTA claim。

## 1. Goal

Stage 7.1 的目标是第一次把 frozen selected LOCO operator 放进 objective-level loop：

```text
fixed BaseOpt proposals
-> online shared-variable conflict states
-> coordination method
-> global candidate merge
-> global objective evaluation
-> FE ledger
```

本阶段只证明 integration legality 和最小 runtime closure。它不证明 large-scale benchmark success。

## 2. Legal Inputs

Stage 7.1 只读取：

```text
configs/stage7_0_objective_eval_protocol.yaml
artifacts/selected/stage5_1/selected_operator.json
artifacts/selected/stage5_1/selected_operator_ast.json
```

它不重新生成 candidate，不修改 selected operator，不回改 train/validation/promotion rule。

## 3. Pilot Setup

Pilot problem：

```text
objective_name = synthetic_sphere
synthetic_panel = synthetic_conflicting_overlap_panel
dimension = 500
grouping_mode = oracle grouping
selected_operator_target_variable = 6
objective_step_count_per_method = 3
```

Method set：

```text
identity_no_coord
simple_consensus
weighted_consensus
best_reward_select
selected_loco_operator
```

BaseOpt is fixed as a deterministic proposal generator. LOCO does not choose it, modify it, or generate a replacement optimizer.

## 4. FE Accounting

Stage 7.1 records the objective-level FE identity:

```text
FE_total = FE_grouping
         + FE_proposal
         + FE_coordination_extra
         + FE_repair
         + FE_global_objective
```

Current pilot totals:

```text
FE_grouping = 0
FE_proposal = 15
FE_coordination_extra = 0
FE_repair = 0
FE_global_objective = 15
FE_total = 30
```

Cross-method evaluations are not shared. Each method receives the same number of proposal and global objective steps.

## 5. Outputs

Stage 7.1 produces:

```text
artifacts/objective_eval/stage7_1/objective_trace.jsonl
artifacts/objective_eval/stage7_1/method_summary.json
artifacts/objective_eval/stage7_1/fe_ledger.json
artifacts/objective_eval/stage7_1/runtime_boundary.json
artifacts/objective_eval/stage7_1/pilot_report.json
```

## 6. Boundary Flags

Stage 7.1 preserves:

```text
no LLM call
no new candidate generation
no selected-operator revision
no evolution/search run
no test-feedback tuning
no BaseOpt modification
no optimizer/controller/scheduler generation
not a SOTA claim
not a final objective-value performance claim
```

## 7. Next Step

Stage 7.1 next status:

```text
READY_FOR_STAGE7_2_SYNTHETIC_LARGE_SCALE_PANEL
```

The next stage should scale from this minimal pilot into the Stage 7.0 locked synthetic panel:

```text
Stage 7.2: Synthetic Large-Scale Objective Panel
```
