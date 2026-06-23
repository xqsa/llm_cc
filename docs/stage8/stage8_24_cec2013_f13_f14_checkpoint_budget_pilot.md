# Stage 8.24 CEC2013 F13/F14 Checkpoint-budget Pilot

Created by: Codex
Date: 2026-06-23

## Purpose

Stage 8.24 reruns the Stage 8.22 frozen LLM-origin policy on CEC2013 F13/F14
with a 120000-FE checkpoint budget before any formal 25-run or full F1-F15
panel.

This stage is not a final objective-value performance claim and not a SOTA
claim.

## Frozen Policy

```text
selected_candidate_id = stage8_20_round_candidate_8
freeze_status = FROZEN_FOR_CEC2013_F13_F14_MULTISEED_NOT_FINAL
method_name = stage8_22_frozen_llm_policy
```

No policy revision is allowed in Stage 8.24.

## Pilot Scope

```text
benchmark_suite = CEC2013_LSGO
function_ids = F13, F14
run_count = 3
seeds = 0, 1, 2
max_fe_per_method_per_function = 120000
methods = identity_no_coord, simple_consensus, weighted_consensus,
          best_reward_select, stage8_22_frozen_llm_policy
parallel_execution_used = true
max_workers = 8
```

This is a checkpoint-budget pilot, not the formal 25-run panel and not the full
F1-F15 panel.

To avoid committing oversized artifacts, Stage 8.24 writes compact checkpoint
trace rows only. It does not write the full 3600000-row objective trace.

## Result

```text
status = PASS
checkpoint_budget_pilot_executed = true
official_cec2013_problem_loaded = true
max_fe_per_method_per_function = 120000
raw_trace_row_count = 3600000
checkpoint_trace_row_count = 180
FE_total = 7200030
FE_global_objective = 3600030
frozen_policy_vs_best_reward_select = 0 win / 6 tie / 0 loss
frozen_policy_vs_best_baseline = 0 win / 6 tie / 0 loss
checkpoint_budget_pilot_promising = true
recommended_next_stage = Stage 8.25
recommended_next_work = formal_f13_f14_same_budget_decision_gate
```

Plain interpretation: the frozen LLM-origin policy still does not beat
`best_reward_select` or the best baseline at 120000 FE, but it also does not
lose on F13/F14 across the three seeds. This is a no-loss checkpoint signal,
not a superiority result.

## Failure-honest Finding

The branch report shows:

```text
policy_trace_row_count = 720000
trust_best_reward = 720000
damp_best_reward = 0
shrinkage_repair = 0
non_trust_branch_exercised = false
```

This means the frozen LLM policy collapses to `best_reward_select` throughout
the 120000-FE checkpoint on this F13/F14 setup. The tie result is therefore
expected and should not be interpreted as evidence that the LLM-origin policy
has surpassed the best simple baseline.

## Boundary

Stage 8.24 keeps these boundaries:

```text
llm_call_used = false
new_candidate_generation_used = false
selected_policy_revision_used = false
evolution_search_used = false
validation_feedback_used = false
test_feedback_used = false
reported_results_used_as_runtime_feedback = false
baseopt_modified = false
optimizer_generation_used = false
controller_scheduler_generation_used = false
not_sota_claim = true
not_final_performance_claim = true
not_full_25_run_panel = true
not_full_f1_f15_panel = true
```

## Artifacts

Stage 8.24 writes:

```text
artifacts/objective_eval/stage8_24/checkpoint_pilot_report.json
artifacts/objective_eval/stage8_24/checkpoint_trace.jsonl
artifacts/objective_eval/stage8_24/method_summary.json
artifacts/objective_eval/stage8_24/win_loss_report.json
artifacts/objective_eval/stage8_24/policy_branch_report.json
artifacts/objective_eval/stage8_24/fe_ledger.json
artifacts/objective_eval/stage8_24/runtime_boundary.json
artifacts/objective_eval/stage8_24/next_route_decision.json
```

## Next Route

Stage 8.24 routes to:

```text
Stage 8.25: formal F13/F14 same-budget decision gate
```

Stage 8.25 should not jump directly to a SOTA claim. It should decide whether
to spend the formal 25-run 3e6-FE F13/F14 budget, taking into account that the
current frozen policy ties by collapsing to `best_reward_select`.
