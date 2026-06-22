# Stage 8.17 Bounded Train-side Repaired-policy Objective Check

创建日期：2026-06-22
执行者：Codex

## 1. Boundary

Stage 8.17 evaluates the Stage 8.16 train-side repair candidate in a bounded
objective-level LOCO-CC loop:

```text
reward_trust_gated_coordination_v1
```

This stage is not an official CEC2013 benchmark run, not a full 25-run panel,
not a final objective-value performance claim, and not a SOTA claim.

Stage 8.17 does execute a bounded train-side objective loop and therefore counts
new objective FE.

## 2. Purpose

Stage 8.16 repaired the missing policy behavior:

```text
trust best-reward proposal when reward reliability is strong
fallback to weighted/simple/shrinkage repair when reward reliability is weak
```

Stage 8.17 checks whether that repair candidate is useful in objective-loop
execution before spending the CEC2013 F13/F14 re-smoke budget or any full
25-run panel.

## 3. Bounded Panel

The bounded check uses 8 train-side objective cases, 6 methods, and 4 objective
steps per method-case:

```text
case_count = 8
method_count = 6
objective_step_count_per_case = 4
trace_row_count = 192
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

The cases cover four repaired-policy regimes:

```text
trusted_best_reward
low_margin_weighted
direction_conflict_simple
oversized_best_reward_shrinkage
```

## 4. Result

Bounded objective-loop result:

```text
bounded_check_promising = true

repaired_vs_stage8_11_generalized_policy = 5 win / 3 tie / 0 loss
repaired_vs_best_reward_select = 6 win / 2 tie / 0 loss
repaired_vs_best_baseline = 2 win / 6 tie / 0 loss
```

Repair branch coverage:

```text
trust_best_reward = 8
weighted_safety = 2
simple_safety = 20
shrinkage_repair = 2
minimum_branch_coverage_count = 2
all_repair_branches_exercised = true
```

Interpretation:

```text
The Stage 8.16 repaired policy is not only a static train-side gate. It executes
inside a bounded objective loop, exercises all intended branches, and records
positive bounded utility evidence against the previous generalized policy and
best_reward_select.
```

This is still bounded train-side evidence only.

## 5. FE Accounting

```text
FE_proposal = 192
FE_global_objective = 192
FE_total = 384
same_budget_across_methods = true
cross_method_evaluations_shared = false
all_extra_fe_counted = true
objective_loop_executed = true
new_objective_evaluation_used = true
official_cec2013_panel_run = false
not_full_25_run_panel = true
```

## 6. Route Decision

```text
decision = PROMISING_BOUNDED_CHECK_ROUTE_TO_CEC2013_RESMOKE
recommended_next_stage = Stage 8.18
recommended_next_work = cec2013_f13_f14_repaired_policy_resmoke
run_full_25_run_panel_next = false
run_cec2013_resmoke_next = true
```

The next step is not the full 25-run panel. The next step is a bounded CEC2013
F13/F14 re-smoke for the repaired policy.

## 7. Artifacts

```text
configs/stage8_17_bounded_repaired_policy_objective_check.yaml
docs/stage8/stage8_17_bounded_repaired_policy_objective_check.md
docs/stage8/stage8_17_self_check_report.md
loco/coordination/bounded_repaired_policy_objective_check.py
scripts/stage8/run_stage8_17_bounded_repaired_policy_objective_check.py
tests/stage8/test_stage8_17_bounded_repaired_policy_objective_check.py
artifacts/objective_eval/stage8_17/objective_trace.jsonl
artifacts/objective_eval/stage8_17/method_summary.json
artifacts/objective_eval/stage8_17/panel_summary.json
artifacts/objective_eval/stage8_17/win_loss_report.json
artifacts/objective_eval/stage8_17/policy_branch_report.json
artifacts/objective_eval/stage8_17/fe_ledger.json
artifacts/objective_eval/stage8_17/runtime_boundary.json
artifacts/objective_eval/stage8_17/next_route_decision.json
artifacts/objective_eval/stage8_17/objective_check_report.json
```

## 8. Forbidden Scope

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

Stage 8.17 does not support:

```text
SOTA improvement
official full CEC2013 benchmark success
final objective-value performance improvement
full 25-run statistical claim
```
