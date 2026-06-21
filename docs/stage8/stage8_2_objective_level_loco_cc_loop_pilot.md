# Stage 8.2 Objective-Level LOCO-CC Loop Pilot

创建日期：2026-06-21  
执行者：Codex  
阶段边界：Stage 8.2 只在 objective-level LOCO-CC loop 里运行 Stage 8.1 selection-ready operators，并与 frozen Stage 5.1 selected operator 做 utility-level 对比。它不调用 LLM，不生成新候选，不修改 BaseOpt，不做 validation/test feedback，也不把结果说成 SOTA 或 final performance claim。

## 1. Goal

Stage 8.2 的目标不是再做静态审计，而是证明新选出的 operator 能进入 objective-level LOCO-CC loop，并在受控的 objective-level pilot 中形成 utility evidence：

This objective-level LOCO-CC loop pilot is the first stage where a selection-ready operator is exercised as a real runtime candidate rather than only being audited statically.

```text
fixed BaseOpt proposals
-> online shared-variable conflict states
-> frozen Stage 5.1 selected operator
-> selection-ready Stage 8.1 operator
-> global objective evaluation
-> FE ledger
-> utility report
```

本阶段只证明 objective-level utility pilot 成立。它不证明 large-scale benchmark success。
在当前受控 pilot 下，selection-ready candidate 的最终 objective-level 结果优于 frozen Stage 5.1 selected operator。

## 2. Inputs

Stage 8.2 只读取：

```text
configs/stage7_0_objective_eval_protocol.yaml
artifacts/selection_audit/stage8_1/selection_decision.json
artifacts/selected/stage5_1/selected_operator.json
artifacts/selected/stage5_1/selected_operator_ast.json
```

Stage 8.2 also uses the frozen Stage 8.1 selection-ready operator set encoded in the selection decision.

## 3. Pilot Setup

Pilot problem:

```text
objective_name = synthetic_sphere
synthetic_panel = synthetic_conflicting_overlap_panel
dimension = 500
grouping_mode = oracle grouping
selected_operator_target_variable = 6
objective_step_count_per_method = 3
```

Method set:

```text
identity_no_coord
simple_consensus
weighted_consensus
best_reward_select
frozen_stage5_selected_operator
selection_ready_stage8_operator
```

BaseOpt is fixed as a deterministic proposal generator. LOCO does not choose it, modify it, or generate a replacement optimizer.

## 4. FE Accounting

Stage 8.2 records the objective-level FE identity:

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
FE_proposal = 18
FE_coordination_extra = 0
FE_repair = 0
FE_global_objective = 18
FE_total = 36
```

Cross-method evaluations are not shared. Each method receives the same number of proposal and global objective steps.

## 5. Outputs

Stage 8.2 produces:

```text
artifacts/objective_eval/stage8_2/objective_trace.jsonl
artifacts/objective_eval/stage8_2/method_summary.json
artifacts/objective_eval/stage8_2/fe_ledger.json
artifacts/objective_eval/stage8_2/runtime_boundary.json
artifacts/objective_eval/stage8_2/pilot_report.json
artifacts/objective_eval/stage8_2/utility_trace.jsonl
artifacts/objective_eval/stage8_2/utility_report.json
artifacts/objective_eval/stage8_2/next_route_decision.json
```

## 6. Boundary Flags

Stage 8.2 preserves:

```text
no LLM call
no new candidate generation
no selected-operator revision
no evolution/search run
no validation feedback
no test-feedback tuning
no test feedback
no BaseOpt modification
no optimizer/controller/scheduler generation
not a SOTA claim
not a final objective-value performance claim
```

## 7. Current Result

```text
status = PASS
source_stage = 8.1
pilot_scope = objective_level_loco_cc_loop_pilot
method_count = 6
objective_step_count_per_method = 3
trace_row_count = 18
utility_trace_row_count = 6
objective_utility_evaluated = true
baseline_comparison_made = true
selection_ready_improved_over_frozen_selected_operator = true
next_status = READY_FOR_STAGE8_3_TRAIN_ONLY_OR_VALIDATION_SELECTION
```

## 8. Next Step

The next stage can be:

```text
Stage 8.3: train-only or validation selection over objective-level utility evidence
```

Stage 8.3 must not feed utility traces back into candidate generation, improvement scoring, or BaseOpt.
