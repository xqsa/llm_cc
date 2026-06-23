# Stage 8.31 Behavior-distinct Checkpoint Failure Diagnosis

Created by Codex on 2026-06-23.

## Purpose

Stage 8.31 reads the Stage 8.30 CEC2013 F13/F14 checkpoint artifacts and
diagnoses why the frozen behavior-distinct ownership-aware policy is exercised
but not promising. This is a read-only diagnosis stage.

It does not revise the selected policy, call an LLM, run a new objective loop,
launch a formal 25-run panel, or make a SOTA claim.

## Result

```text
stage = 8.31
status = PASS
source_stage = 8.30
diagnosis_scope = read_only_behavior_distinct_checkpoint_failure_diagnosis
stage8_30_checkpoint_promising = false
stage8_30_behavior_policy_vs_best_reward_select = 1 win / 2 tie / 3 loss
stage8_30_behavior_policy_vs_best_baseline = 1 win / 2 tie / 3 loss
overcorrection_confirmed = true
overcorrection_type = contribution_leader_break_overcorrection
policy_branch_collapse_confirmed = true
formal_25_run_recommended_now = false
FE_total = 0
inherited_stage8_30_FE_total = 72030
recommended_next_stage = Stage 8.32
recommended_next_work = design_overcorrection_guard_or_conditional_owner_trust_repair
```

## Diagnosis

Stage 8.30 did not fail because the behavior-distinct policy was unused. The
policy was exercised, but its behavior collapsed to a narrow branch pattern:

```text
owner_proposal_select_count = 3600
shrinkage_repair_count = 3600
contribution_leader_count = 7200
break_count = 7200
trust_best_reward_count = 0
preserve_count = 0
best_reward_group_count = 0
```

In plain terms, the frozen policy over-applies `contribution_leader + break`
with owner-proposal selection or shrinkage behavior. It does not preserve or
trust the `best_reward_select` path in CEC F13/F14 cases where that baseline is
favored. This supports the Stage 8.31 diagnosis:

```text
overcorrection_confirmed = true
overcorrection_type = contribution_leader_break_overcorrection
```

## Required Artifacts

```text
artifacts/analysis/stage8_31/failure_diagnosis_report.json
artifacts/analysis/stage8_31/overcorrection_diagnosis.json
artifacts/analysis/stage8_31/case_delta_table.jsonl
artifacts/analysis/stage8_31/branch_usage_diagnosis.json
artifacts/analysis/stage8_31/fe_ledger.json
artifacts/analysis/stage8_31/runtime_boundary.json
artifacts/analysis/stage8_31/next_route_decision.json
```

## Boundary

Stage 8.31 is not a policy repair and not a benchmark claim.

```text
llm_call_used = false
new_candidate_generation_used = false
new_llm_strategy_generation_used = false
objective_loop_executed = false
new_objective_evaluation_used = false
selected_policy_revision_used = false
evolution_search_used = false
validation_feedback_used = false
test_feedback_used = false
reported_results_used_as_runtime_feedback = false
baseopt_modified = false
optimizer_generation_used = false
controller_scheduler_generation_used = false
not a final objective-value performance claim
not a SOTA claim
```

## Next Route

Do not run the 25-run panel yet. The next stage should repair the diagnosed
failure mode:

```text
Stage 8.32: overcorrection guard / conditional owner-trust repair
```

The repair should add a guarded path that can preserve or trust best-reward
behavior when CEC-like regimes favor it, while keeping the ownership-aware idea
active for genuinely conflicting shared-variable states.
