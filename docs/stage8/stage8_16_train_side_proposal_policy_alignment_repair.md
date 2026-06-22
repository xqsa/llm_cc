# Stage 8.16 Train-side Proposal/Policy Alignment Repair

创建日期：2026-06-22
执行者：Codex

## 1. Boundary

Stage 8.16 addresses the train-side/protocol cause exposed by Stage 8.15:

```text
dominant_failure_mode = best_reward_select_alignment_gap
```

It adds a train-side repair candidate named:

```text
reward_trust_gated_coordination_v1
```

This is not an official CEC2013 benchmark run, not a full 25-run panel, not a
selected-policy revision for the official panel, not a final objective-value
performance claim, and not a SOTA claim.

Stage 8.16 does not run an objective loop and does not use Stage 8.14 smoke as
direct policy-tuning feedback.

## 2. Motivation

Stage 8.15 diagnosed that the Stage 8.11 generalized policy lost the Stage 8.14
CEC2013 F13/F14 single-run smoke because it routed to safety branches instead
of exploiting the best-reward proposal:

```text
F13 -> simple_safety / simple_consensus equivalent
F14 -> zero_anchor / weighted_consensus equivalent
best baseline on both functions -> best_reward_select
```

The repair target is therefore not "make a new optimizer." The repair target is:

```text
shared-variable conflict state
-> reward reliability features
-> trust best-reward when reliable
-> otherwise fallback to consensus / weighted / shrinkage repair
```

## 3. Repair Candidate

Stage 8.16 defines `RewardTrustGatedCoordination` with policy name:

```text
reward_trust_gated_coordination_v1
```

The policy computes these train-side features:

```text
reward_top_margin
reward_concentration
best_reward_direction_agreement
best_reward_value_outlier_score
best_reward_update_fraction
```

The policy branches are:

```text
trust_best_reward
weighted_safety
simple_safety
shrinkage_repair
```

Plain interpretation:

```text
If reward is clearly concentrated on one proposal, the proposal direction is
consistent, and the update is not an oversized/outlier move, trust the
best-reward proposal.

If reward reliability is weak, fall back to weighted consensus.

If proposal directions are conflicting or conflict is high, fall back to simple
consensus.

If the best-reward update is oversized, use shrinkage repair rather than taking
the raw best-reward proposal.
```

## 4. Train-side Fixture Evidence

Stage 8.16 uses train-side fixtures only. It does not evaluate CEC2013 objectives.

Recorded branch counts:

```text
trust_best_reward = 1
weighted_safety = 1
simple_safety = 2
shrinkage_repair = 1
```

Key checks:

```text
trust_best_reward_fixture_passed = true
unsafe_best_reward_fallback_fixture_passed = true
best_reward_alignment_gap_addressed = true
```

This proves the repair candidate has the missing branch behavior. It does not
prove objective-level utility yet.

## 5. FE Accounting

```text
Stage 8.16 FE_total = 0
inherited_stage8_15_FE_total = 0
inherited_stage8_14_FE_total = 24010
objective_loop_executed = false
new_objective_evaluation_used = false
```

## 6. Route Decision

Stage 8.16 keeps the full 25-run panel blocked:

```text
run_full_25_run_panel_next = false
```

Next route:

```text
decision = ROUTE_TO_BOUNDED_TRAIN_SIDE_REPAIRED_POLICY_OBJECTIVE_CHECK
recommended_next_stage = Stage 8.17
recommended_next_work = bounded_train_side_repaired_policy_objective_check
```

The next step should run a bounded objective-loop check for the repaired
train-side policy before any formal 25-run CEC2013 panel.

## 7. Artifacts

```text
configs/stage8_16_train_side_proposal_policy_alignment_repair.yaml
docs/stage8/stage8_16_train_side_proposal_policy_alignment_repair.md
docs/stage8/stage8_16_self_check_report.md
loco/coordination/train_side_proposal_policy_alignment_repair.py
scripts/stage8/run_stage8_16_train_side_proposal_policy_alignment_repair.py
tests/stage8/test_stage8_16_train_side_proposal_policy_alignment_repair.py
artifacts/objective_eval/stage8_16/alignment_repair_report.json
artifacts/objective_eval/stage8_16/reward_reliability_feature_report.json
artifacts/objective_eval/stage8_16/policy_branch_alignment_report.json
artifacts/objective_eval/stage8_16/claim_boundary_report.json
artifacts/objective_eval/stage8_16/fe_ledger.json
artifacts/objective_eval/stage8_16/runtime_boundary.json
artifacts/objective_eval/stage8_16/next_route_decision.json
```

## 8. Forbidden Scope

```text
llm_call_used = false
new_llm_candidate_generation_used = false
selected_operator_revision_used = false
evolution_search_used = false
objective_loop_executed = false
new_objective_evaluation_used = false
validation_feedback_used = false
test_feedback_used = false
stage8_14_smoke_used_as_direct_tuning_feedback = false
reported_results_used_as_runtime_feedback = false
baseopt_modified = false
optimizer_generation_used = false
controller_scheduler_generation_used = false
not_sota_claim = true
not_final_performance_claim = true
```

Stage 8.16 does not support:

```text
SOTA improvement
official full CEC2013 benchmark success
final objective-value performance improvement
full 25-run statistical claim
CEC2013 policy repair success
```
