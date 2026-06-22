# Stage 8.8 Conditional Policy Objective-Loop Rerun

创建日期：2026-06-22  
执行者：Codex  
阶段边界：Stage 8.8 把 Stage 8.7 的 `overlap_reward_reliability_switch_v1` 放回 objective-level LOCO-CC synthetic panel 中真实执行。它会产生新的 objective evaluations 并计入 FE，但不调用 LLM，不生成新 candidate，不修改 selected operator，不使用 validation/test feedback，不修改 BaseOpt，也不声称 SOTA 或 final objective-value performance improvement。

## 1. Goal

Stage 8.8 回答：

```text
Stage 8.7 的 conditional policy 进入 objective loop 后，
是否真的恢复 simple_consensus 更强的 cases，
同时不破坏 weighted_consensus 已经足够的 cases？
```

## 2. Inputs

Stage 8.8 读取：

```text
configs/stage7_0_objective_eval_protocol.yaml
artifacts/selection_audit/stage8_3/objective_utility_selection_decision.json
artifacts/selected/stage5_1/selected_operator.json
artifacts/selected/stage5_1/selected_operator_ast.json
artifacts/objective_eval/stage8_7/conditional_policy_report.json
artifacts/objective_eval/stage8_7/case_policy_table.jsonl
```

## 3. Methods

Stage 8.8 使用 7 个方法：

```text
identity_no_coord
simple_consensus
weighted_consensus
best_reward_select
frozen_stage5_selected_operator
stage8_3_selected_operator
stage8_7_conditional_policy
```

The conditional policy method executes:

```text
overlap_reward_reliability_switch_v1
```

## 4. Result

```text
status = PASS
objective_loop_executed = true
new_objective_evaluation_used = true
trace_row_count = 756
FE_total = 1512
conditional_vs_stage8_3_selected_operator = 12 win / 24 tie / 0 loss
conditional_vs_weighted_consensus = 12 win / 24 tie / 0 loss
conditional_vs_simple_consensus = 24 win / 12 tie / 0 loss
conditional_vs_best_baseline = 0 win / 36 tie / 0 loss
simple_preferred_case_recovery_count = 12
weighted_sufficient_case_regression_count = 0
```

大白话：Stage 8.8 说明 conditional policy 在 objective loop 里确实修复了 Stage 8.4/8.6 发现的缺口。它相对 Stage 8.3 selected operator 和 weighted_consensus 赢了 12 个原本 simple_consensus 更强的 cases，同时在 24 个 weighted-sufficient cases 上没有回退。它追平 best baseline，但还没有超过 best baseline，所以仍然不能说 SOTA 或 final benchmark success。

## 5. Boundary

Stage 8.8 preserves:

```text
no LLM call
no new candidate generation
no selected-operator revision
no evolution/search
no validation feedback
no test feedback
no BaseOpt modification
not a final objective-value performance claim
not a SOTA claim
```

## 6. Next Step

Recommended next stage:

```text
Stage 8.9 failure-honest interpretation before official claims
```

Stage 8.9 should explain the exact meaning of the Stage 8.8 result: the conditional policy removes the regression against simple_consensus and matches the best baseline on the synthetic panel, but it still does not beat the best baseline or support an official benchmark claim.
