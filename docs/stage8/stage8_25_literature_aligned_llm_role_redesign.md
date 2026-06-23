# Stage 8.25 Literature-aligned LLM Role Redesign

Created by: Codex
Date: 2026-06-23

## Purpose

Stage 8.25 is a read-only analysis and design-lock gate. It reads Stage 8.24
checkpoint artifacts, diagnoses why the frozen LLM-origin policy still does not
beat `best_reward_select`, aligns the next move with LSGO and LLM automatic
algorithm design literature, and locks a new ownership-aware strategy DSL
contract for Stage 8.26.

This stage does not run objectives, does not call an LLM, and does not generate
new candidates. It is not a final objective-value performance claim and not a
SOTA claim.

## Source Evidence

Stage 8.25 reads:

```text
artifacts/objective_eval/stage8_24/checkpoint_pilot_report.json
artifacts/objective_eval/stage8_24/win_loss_report.json
artifacts/objective_eval/stage8_24/policy_branch_report.json
artifacts/objective_eval/stage8_24/fe_ledger.json
artifacts/objective_eval/stage8_24/runtime_boundary.json
artifacts/objective_eval/stage8_24/next_route_decision.json
```

## Failure Diagnosis

Stage 8.24 showed:

```text
frozen_policy_vs_best_reward_select = 0 win / 6 tie / 0 loss
frozen_policy_vs_best_baseline = 0 win / 6 tie / 0 loss
```

The critical failure mode is not a loss. It is behavioral collapse:

```text
failure_mode = branch_collapse_to_best_reward_select
collapsed_branch = trust_best_reward
trust_best_reward_branch_count = 720000
non_trust_branch_count = 0
stage8_24_policy_behavior_equivalent_to_best_reward = true
formal_25_run_recommended_now = false
```

Plain interpretation: the frozen LLM-origin policy ties `best_reward_select`
because it behaves like `best_reward_select` on all policy steps. This is
no-loss evidence, not superiority evidence.

## Literature Alignment

Stage 8.25 records two literature signals:

```text
LSGO literature:
  DG / RDG3 / OEDG / FEA
  -> decomposition, shared-variable identification, linkage break/preserve,
     ownership, and overlapping factor treatment matter.

LLM automatic algorithm design literature:
  FunSearch / EoH / ReEvo / LLaMEA
  -> LLM should be inside an evaluator-in-the-loop reflective program search,
     not used as a one-shot static candidate generator.
```

The resulting design consequence is:

```text
Move from static shared-variable coordination action selection
to ownership-aware decomposition/coordination strategy programs.
```

## LLM Role Redesign

Rejected role:

```text
one_shot_or_static_coordination_action_generator
```

Old project role:

```text
static_shared_variable_coordination_policy_generator
```

New role:

```text
reflective_decomposition_ownership_coordination_strategy_program_designer
```

The LLM should generate programs that can make decomposition consequences
explicit, including shared-variable ownership, multi-assignment, linkage
break/preserve, coordination action, fallback repair, and behavior-equivalence
guards.

## New DSL Contract

Stage 8.25 locks the Stage 8.26 MVP DSL target scope:

```text
target_scope = shared_variables_and_decomposition_consequences
```

Allowed outputs:

```text
shared_variable_owner
allow_multi_assignment
linkage_break_or_preserve
contribution_based_owner_switch
coordination_action
fallback_repair_action
behavior_equivalence_guard
```

Behavior-equivalence guards:

```text
not_equivalent_to_best_reward_select
non_trust_branch_exercised
ownership_or_linkage_decision_exercised
```

Forbidden capabilities remain:

```text
generate_optimizer
modify_baseopt
rewrite_benchmark_objective
generate_scheduler_or_controller
use_validation_feedback
use_test_feedback
use_reported_sota_as_runtime_feedback
```

## Boundary

Stage 8.25 keeps these boundaries:

```text
FE_total = 0
objective_loop_executed = false
new_objective_evaluation_used = false
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
```

## Artifacts

Stage 8.25 writes:

```text
artifacts/analysis/stage8_25/stage8_24_failure_diagnosis.json
artifacts/analysis/stage8_25/literature_alignment_matrix.json
artifacts/analysis/stage8_25/llm_role_redesign.json
artifacts/analysis/stage8_25/ownership_aware_strategy_dsl_contract.json
artifacts/analysis/stage8_25/fe_ledger.json
artifacts/analysis/stage8_25/runtime_boundary.json
artifacts/analysis/stage8_25/next_route_decision.json
artifacts/analysis/stage8_25/stage8_25_report.json
```

## Next Route

Stage 8.25 routes to:

```text
Stage 8.26: MVP strategy DSL + evaluator + behavior-equivalence checker
```
