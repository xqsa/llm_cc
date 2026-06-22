# Stage 8.11 Policy Generalization Beyond Best Simple Baseline

创建日期：2026-06-22
执行者：Codex
阶段边界：Stage 8.11 在锁定的 objective-level LOCO-CC panel 中执行一个 generalized coordination policy，目标不是再证明它比旧 frozen operator 更好，而是验证它能否稳定超过 best simple baseline。它不调用 LLM，不生成新 candidate，不修改 selected operator，不使用 validation/test feedback，不修改 BaseOpt，也不声称 SOTA 或 final objective-value performance improvement。

## 1. Goal

Stage 8.11 回答：

```text
能否把 Stage 8.7/8.8 的 conditional policy 再往前推一步，
做成一个 regime-safe 的 generalized policy，
并且在 locked panel 上压过 best simple baseline？
```

## 2. Policy Shape

本阶段引入 `regime_safe_adaptive_shrinkage_v1`。它先判断当前 conflict regime 是否更适合 weighted branch 还是 simple branch，然后在需要时用 conflict-aware shrinkage 对 shared variable proposal 做收缩。这个策略不是简单地在两个旧 baseline 之间切换，而是允许一个新的 shrinkage branch 介入，只要它比 base branch 更安全。

## 3. Inputs

Stage 8.11 读取：

```text
artifacts/objective_eval/stage8_10/route_decision.json
artifacts/objective_eval/stage8_10/policy_generalization_requirements.json
artifacts/selection_audit/stage8_3/objective_utility_selection_decision.json
artifacts/selected/stage5_1/selected_operator.json
artifacts/selected/stage5_1/selected_operator_ast.json
artifacts/objective_eval/stage8_7/conditional_policy_report.json
artifacts/objective_eval/stage8_7/case_policy_table.jsonl
```

## 4. Methods

Stage 8.11 使用 7 个方法：

```text
identity_no_coord
simple_consensus
weighted_consensus
best_reward_select
frozen_stage5_selected_operator
stage8_3_selected_operator
stage8_11_generalized_policy
```

## 5. Expected Result Shape

```text
status = PASS
objective_loop_executed = true
new_objective_evaluation_used = true
panel_count = 4
dimension_count = 3
seed_count = 3
method_count = 7
comparison_case_count = 36
FE_total = 1512
generalized_vs_best_baseline = 27 win / 9 tie / 0 loss
best_baseline_beaten = true
recommended_next_stage = Stage 8.12
```

大白话：Stage 8.11 的目标是把前面“conditional policy 能补洞”的能力，升级成“generalized policy 能稳定压过最强简单基线”。如果它真的做到 27/9/0，这一步就说明主线已经从“修复特例”往“可复用泛化策略”推进了一截。

## 6. Boundary

Stage 8.11 preserves:

```text
no LLM call
no new candidate generation
no selected-operator revision
no evolution/search
no validation feedback
no test feedback
no BaseOpt modification
no optimizer/controller/scheduler generation
not a final objective-value performance claim
not a SOTA claim
```

## 7. Next Step

Recommended next stage:

```text
Stage 8.12 official-like panel or SOTA-facing protocol
```
