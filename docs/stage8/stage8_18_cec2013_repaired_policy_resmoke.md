# Stage 8.18 CEC2013 F13/F14 Repaired-policy Re-smoke

创建日期：2026-06-22
执行者：Codex

## 1. Boundary

Stage 8.18 reruns a bounded CEC2013 F13/F14 single-seed smoke with the Stage
8.16 repaired policy:

```text
reward_trust_gated_coordination_v1
```

This stage executes the objective loop and counts new objective FE. It is not a
full 25-run panel, not a full F1-F15 CEC2013 panel, not a final
objective-value performance claim, and not a SOTA claim.

## 2. Purpose

Stage 8.14 showed that the previous generalized policy lost to direct
best-reward proposal selection on the CEC2013 F13/F14 smoke. Stage 8.15
diagnosed that failure, Stage 8.16 created a reward-trust repaired policy, and
Stage 8.17 verified that repaired policy in a bounded train-side objective
loop.

Stage 8.18 checks whether the repaired policy still looks promising when moved
back into the CEC2013 F13/F14 smoke before spending the full 25-run budget.

## 3. Resmoke Panel

```text
benchmark_suite = CEC2013_LSGO
function_ids = F13, F14
run_count = 1
smoke_seed = 0
smoke_max_fe_per_method_per_function = 1200
method_count = 6
trace_row_count = 14400
```

Compared methods:

```text
identity_no_coord
simple_consensus
weighted_consensus
best_reward_select
stage8_11_generalized_policy
stage8_16_reward_trust_gated_policy
```

## 4. Result

```text
status = PASS
repaired_policy_resmoke_promising = true

repaired_vs_stage8_11_generalized_policy = 2 win / 0 tie / 0 loss
repaired_vs_best_reward_select = 0 win / 2 tie / 0 loss
repaired_vs_best_baseline = 0 win / 2 tie / 0 loss
```

Per-function outcome:

```text
F13:
  repaired_policy_final_best = 8.714428967708853e+16
  best_reward_select_final_best = 8.714428967708853e+16
  stage8_11_generalized_policy_final_best = 8.716559195496776e+16
  repaired_vs_best_reward_select = tie
  repaired_vs_stage8_11_generalized_policy = win

F14:
  repaired_policy_final_best = 5.074322565106659e+18
  best_reward_select_final_best = 5.074322565106659e+18
  stage8_11_generalized_policy_final_best = 5.074322808381155e+18
  repaired_vs_best_reward_select = tie
  repaired_vs_stage8_11_generalized_policy = win
```

Interpretation:

```text
The repaired policy no longer loses to best_reward_select on the CEC2013
F13/F14 single-run smoke. It ties best_reward_select on both functions and beats
the Stage 8.11 generalized policy on both functions.
```

This is still only a single-seed re-smoke. It does not prove multi-seed
stability, full 25-run performance, full CEC2013 F1-F15 performance, or SOTA
superiority.

## 5. Policy Branch Evidence

```text
policy_trace_row_count = 2400
trust_best_reward = 2400
weighted_safety = 0
simple_safety = 0
shrinkage_repair = 0
trust_best_reward_exercised = true
```

The CEC2013 F13/F14 re-smoke routes entirely through the trust-best-reward
branch. This is acceptable for Stage 8.18 because the immediate failure in
Stage 8.14 was under-trusting direct best-reward proposals. It also means Stage
8.19 must check whether this behavior remains stable across multiple seeds
before any full panel.

## 6. FE Accounting

```text
FE_initial_objective = 12
FE_proposal = 14400
FE_global_objective = 14412
FE_coordination_extra = 0
FE_repair = 0
FE_total = 28812
inherited_stage8_17_FE_total = 384
same_budget_across_methods = true
cross_method_evaluations_shared = false
all_extra_fe_counted = true
official_cec2013_panel_run = false
not_full_25_run_panel = true
```

## 7. Route Decision

```text
decision = PROMISING_RESMOKE_ROUTE_TO_CEC2013_MULTISEED_PILOT
recommended_next_stage = Stage 8.19
recommended_next_work = cec2013_f13_f14_repaired_policy_multiseed_pilot
run_full_25_run_panel_next = false
run_multiseed_pilot_next = true
```

The next step is still not the full 25-run panel. The next step is a multi-seed
pilot on CEC2013 F13/F14 to test stability before spending the formal budget.

## 8. Artifacts

```text
configs/stage8_18_cec2013_repaired_policy_resmoke.yaml
docs/stage8/stage8_18_cec2013_repaired_policy_resmoke.md
docs/stage8/stage8_18_self_check_report.md
loco/coordination/cec2013_repaired_policy_resmoke.py
scripts/stage8/run_stage8_18_cec2013_repaired_policy_resmoke.py
tests/stage8/test_stage8_18_cec2013_repaired_policy_resmoke.py
artifacts/objective_eval/stage8_18/objective_trace.jsonl
artifacts/objective_eval/stage8_18/method_summary.json
artifacts/objective_eval/stage8_18/win_loss_report.json
artifacts/objective_eval/stage8_18/policy_branch_report.json
artifacts/objective_eval/stage8_18/fe_ledger.json
artifacts/objective_eval/stage8_18/runtime_boundary.json
artifacts/objective_eval/stage8_18/next_route_decision.json
artifacts/objective_eval/stage8_18/repaired_policy_resmoke_report.json
```

## 9. Forbidden Scope

```text
llm_call_used = false
new_llm_candidate_generation_used = false
selected_operator_revision_used = false
evolution_search_used = false
validation_feedback_used = false
test_feedback_used = false
reported_results_used_as_runtime_feedback = false
baseopt_modified = false
optimizer_generation_used = false
controller_scheduler_generation_used = false
not_sota_claim = true
not_final_performance_claim = true
```

Stage 8.18 does not support:

```text
SOTA improvement
official full CEC2013 benchmark success
final objective-value performance improvement
full 25-run statistical claim
```

