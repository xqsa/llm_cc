# Stage 7.2 Synthetic Large-Scale Objective Panel

创建日期：2026-06-21
执行者：Codex
阶段边界：Stage 7.2 将 Stage 7.1 minimal LOCO-CC objective loop 扩展到 Stage 7.0 锁定的 synthetic panels。它运行 synthetic sphere objective loop、记录 `FE_global_objective`，并检查 same FE budget。它不是 official CEC2013 benchmark，不是 not a final objective-value performance claim，也不是 not a SOTA claim。

## 1. Goal

Stage 7.2 的目标是验证 Stage 7.1 的 fixed-BaseOpt objective loop 可以覆盖 Stage 7.0 锁定的 synthetic panel types：

```text
synthetic_no_overlap_panel
synthetic_low_overlap_panel
synthetic_conflicting_overlap_panel
synthetic_high_overlap_panel
```

本阶段回答的是一个工程和 protocol 问题：

```text
Can the frozen selected LOCO operator and locked baselines run under the same
objective-level FE budget across the required synthetic panel types?
```

它不回答最终论文里的强问题：

```text
Does LOCO-CC outperform strong optimizers on official large-scale benchmarks?
```

## 2. Legal Inputs

Stage 7.2 只读取：

```text
configs/stage7_0_objective_eval_protocol.yaml
configs/stage7_1_objective_loop_pilot.yaml
artifacts/selected/stage5_1/selected_operator.json
artifacts/selected/stage5_1/selected_operator_ast.json
```

它不重新调用 LLM，不生成新 candidate，不修改 frozen selected operator，不回写 train/validation/test decision。

## 3. Panel Setup

当前最小 synthetic panel 设置：

```text
objective_name = synthetic_sphere
dimensions = [500, 1000]
seeds = [0]
method_count = 5
objective_step_count_per_method_per_panel = 3
trace_row_count = 120
```

Method set：

```text
identity_no_coord
simple_consensus
weighted_consensus
best_reward_select
selected_loco_operator
```

Overlap handling：

```text
synthetic_no_overlap_panel:
  shared_conflict_present = false
  selected_loco_application_count = 0

synthetic_low_overlap_panel / synthetic_conflicting_overlap_panel / synthetic_high_overlap_panel:
  shared_conflict_present = true
  shared_variable_id = 6
```

This keeps the selected AST target variable legal without fabricating conflicts in the no-overlap safeguard panel.

## 4. FE Accounting

Stage 7.2 uses the objective-level FE identity:

```text
FE_total = FE_grouping
         + FE_proposal
         + FE_coordination_extra
         + FE_repair
         + FE_global_objective
```

Current totals:

```text
FE_grouping = 0
FE_proposal = 120
FE_coordination_extra = 0
FE_repair = 0
FE_global_objective = 120
FE_total = 240
same_budget_across_methods = true
```

Cross-method evaluations are not shared. Every locked method receives the same number of proposal and global objective steps.

## 5. Outputs

Stage 7.2 produces:

```text
artifacts/objective_eval/stage7_2/objective_trace.jsonl
artifacts/objective_eval/stage7_2/panel_summary.json
artifacts/objective_eval/stage7_2/method_summary.json
artifacts/objective_eval/stage7_2/fe_ledger.json
artifacts/objective_eval/stage7_2/runtime_boundary.json
artifacts/objective_eval/stage7_2/panel_report.json
```

## 6. Boundary Flags

Stage 7.2 preserves:

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

## 7. What This Means For The Research

Stage 7.2 is the first evidence that the LOCO-CC objective loop is not limited to a single toy trace. It covers no-overlap, low-overlap, conflicting-overlap, and high-overlap synthetic panels at D=500 and D=1000 under same FE budget.

The result is still not enough for the final paper claim. The next stage should turn these objective traces into clean tables, curves, and failure-honest interpretation before deciding whether an optional CEC2013 F13/F14 panel is needed.

## 8. Next Step

Stage 7.2 next status:

```text
READY_FOR_STAGE7_3_OBJECTIVE_RESULT_POLISH
```

Recommended next stage:

```text
Stage 7.3: Objective Result Polish And Paper-Ready Tables
```
