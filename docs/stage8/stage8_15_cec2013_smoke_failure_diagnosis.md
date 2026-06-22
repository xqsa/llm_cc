# Stage 8.15 Failure-Honest CEC2013 Smoke Diagnosis

创建日期：2026-06-22
执行者：Codex

## 1. Boundary

阶段边界：Stage 8.15 只解释 Stage 8.14 的 CEC2013 F13/F14 single-run smoke failure。它不运行 objective loop，不新增 objective evaluation，不调用 LLM，不生成新 candidate，不修改 selected policy/operator，不使用 validation/test feedback，不修改 BaseOpt，也不声称 final objective-value performance improvement 或 SOTA。

Stage 8.15 的核心问题是：

```text
为什么 Stage 8.11 generalized policy 在 Stage 8.14 的 F13/F14 smoke 中
不能赢 best simple/hand baseline，而是输给 best_reward_select？
```

## 2. Input Evidence

Stage 8.15 只读取 Stage 8.14 frozen artifacts：

```text
artifacts/objective_eval/stage8_14/single_run_smoke_report.json
artifacts/objective_eval/stage8_14/win_loss_report.json
artifacts/objective_eval/stage8_14/method_summary.json
artifacts/objective_eval/stage8_14/objective_trace.jsonl
artifacts/objective_eval/stage8_14/fe_ledger.json
artifacts/objective_eval/stage8_14/runtime_boundary.json
artifacts/objective_eval/stage8_14/next_route_decision.json
```

Stage 8.14 result:

```text
single_run_promising = false
policy_vs_best_baseline = 0 win / 0 tie / 2 loss
best_baseline_method_count = best_reward_select: 2
inherited_stage8_14_FE_total = 24010
```

## 3. Diagnosis

Main diagnosis:

```text
dominant_failure_mode = best_reward_select_alignment_gap
top_hypothesis_id = H1_best_reward_alignment_gap
```

Plain interpretation:

```text
CEC2013 F13/F14 smoke favors direct best-reward proposal selection.
The generalized policy instead routes to safety branches:
simple_safety / weighted_safety / zero_anchor.
So the current policy does not exploit the proposal that Stage 8.14 rewards most.
```

Branch evidence:

```text
F13:
  dominant_branch = simple_safety
  dominant_branch_count = 1200 / 1200
  policy final best equals simple_consensus final best

F14:
  dominant_branch = zero_anchor
  dominant_branch_count = 1198 / 1200
  policy final best equals weighted_consensus final best
```

Method-gap evidence:

```text
F13:
  best_baseline_method = best_reward_select
  policy_vs_best_baseline_result = loss

F14:
  best_baseline_method = best_reward_select
  policy_vs_best_baseline_result = loss
```

## 4. Root-Cause Hypotheses

Stage 8.15 records four failure-honest hypotheses:

```text
H1_best_reward_alignment_gap
  best_reward_select is the best baseline on both F13 and F14.

H2_branch_transfer_mismatch
  F13 collapses to simple_safety and F14 mostly to zero_anchor.

H3_proposal_construction_mismatch
  CEC2013 smoke may produce states where reward is more reliable than the
  synthetic panels assumed.

H4_single_shared_variable_scope_limit
  The smoke exercises one shared-variable update path and may underrepresent
  multi-shared-variable interaction benefits.
```

The important point is not “the whole LOCO idea failed.” The honest point is:

```text
Do not run the 25-run panel until this best-reward alignment gap is diagnosed
or repaired on the allowed train-side/protocol side.
```

## 5. Route Decision

```text
decision = ROUTE_TO_TRAIN_SIDE_PROPOSAL_POLICY_ALIGNMENT_REPAIR
recommended_next_stage = Stage 8.16
recommended_next_work = train_side_proposal_policy_alignment_repair
run_full_25_run_panel_next = false
```

Stage 8.16 should not use the Stage 8.14 smoke as test feedback to tune the final policy. It should work on the allowed train-side/protocol side: proposal construction, reward-reliability features, policy-branch alignment, or a train-side repair gate that can later be evaluated without contaminating the official benchmark claim.

## 6. FE Accounting

```text
Stage 8.15 FE_total = 0
inherited_stage8_14_FE_total = 24010
objective_loop_executed = false
new_objective_evaluation_used = false
```

## 7. Artifacts

```text
configs/stage8_15_cec2013_smoke_failure_diagnosis.yaml
docs/stage8/stage8_15_cec2013_smoke_failure_diagnosis.md
docs/stage8/stage8_15_self_check_report.md
loco/coordination/cec2013_smoke_failure_diagnosis.py
scripts/stage8/run_stage8_15_cec2013_smoke_failure_diagnosis.py
tests/stage8/test_stage8_15_cec2013_smoke_failure_diagnosis.py
artifacts/objective_eval/stage8_15/diagnosis_report.json
artifacts/objective_eval/stage8_15/method_gap_report.json
artifacts/objective_eval/stage8_15/branch_diagnostics.json
artifacts/objective_eval/stage8_15/root_cause_hypotheses.json
artifacts/objective_eval/stage8_15/claim_boundary_report.json
artifacts/objective_eval/stage8_15/fe_ledger.json
artifacts/objective_eval/stage8_15/runtime_boundary.json
artifacts/objective_eval/stage8_15/next_route_decision.json
```

## 8. Forbidden Scope

```text
llm_call_used = false
new_candidate_generation_used = false
selected_operator_revision_used = false
evolution_search_used = false
objective_loop_executed = false
new_objective_evaluation_used = false
validation_feedback_used = false
test_feedback_used = false
reported_results_used_as_runtime_feedback = false
baseopt_modified = false
optimizer_generation_used = false
controller_scheduler_generation_used = false
not_sota_claim = true
not_final_performance_claim = true
```

Stage 8.15 does not support:

```text
SOTA improvement
official full CEC2013 benchmark success
final objective-value performance improvement
full 25-run statistical claim
policy repair success
```
