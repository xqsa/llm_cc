# Stage 8.21 LLM vs Non-LLM Contribution Ablation

Created by: Codex  
Date: 2026-06-23

## Purpose

Stage 8.21 tests whether the Stage 8.20 LLM-reflective policy pool contributes
more than deterministic non-LLM alternatives under the same train-side evaluator.
It is not a CEC2013 formal benchmark, not a final objective-value performance
claim, and not a SOTA claim.

The stage answers a narrow question:

```text
Did the LLM-reflective pool produce stronger beat-best_reward candidates than
hand-designed, random-mutation, literature-inspired, and Stage 8.16 human-repair
policy pools under the same train-side evidence surface?
```

## Inputs

Stage 8.21 reads only Stage 8.20 artifacts:

```text
artifacts/selection_audit/stage8_20/llm_reflective_search_report.json
artifacts/selection_audit/stage8_20/accepted_candidates.jsonl
artifacts/selection_audit/stage8_20/candidate_evaluator_report.json
artifacts/selection_audit/stage8_20/fe_ledger.json
artifacts/selection_audit/stage8_20/runtime_boundary.json
artifacts/selection_audit/stage8_20/next_route_decision.json
```

No new LLM candidate generation is allowed in Stage 8.21.

## Compared Pools

Stage 8.21 evaluates five pools:

```text
llm_reflective_pool
hand_designed_pool
random_mutation_pool
literature_inspired_pool
stage8_16_human_repair_policy
```

The LLM pool is loaded from Stage 8.20 accepted candidates. The non-LLM pools
are deterministic bounded comparison pools and are not treated as LLM outputs.

## Evidence

Stage 8.21 records:

```text
status = PASS
stage8_20_selected_candidate_id = stage8_20_round_candidate_8
pool_count = 5
candidate_count = 34
llm_pool_best_rank = 1
llm_pool_beats_non_llm_pool_best = true
best_non_llm_pool_id = stage8_16_human_repair_policy
best_non_llm_candidate_id = stage8_21_stage8_16_human_repair
llm_pool_non_degenerate_candidate_count = 24
llm_pool_train_objective_win_count_vs_best_reward = 3
llm_pool_train_objective_loss_count_vs_best_reward = 0
FE_total = 408
```

Plain meaning: under the Stage 8.20 train-side evaluator, the LLM-reflective
pool's best candidate ranks ahead of the best non-LLM pool candidate. This is
contribution evidence for the LLM-reflective search loop, not official benchmark
performance evidence.

## Boundary

Stage 8.21 keeps these boundaries:

```text
llm_call_used = false
new_llm_candidate_generation_used = false
fake_llm_candidates_used = false
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

## Artifacts

Stage 8.21 writes:

```text
artifacts/selection_audit/stage8_21/llm_contribution_ablation_report.json
artifacts/selection_audit/stage8_21/pool_summary.json
artifacts/selection_audit/stage8_21/pool_candidate_table.jsonl
artifacts/selection_audit/stage8_21/win_loss_report.json
artifacts/selection_audit/stage8_21/fe_ledger.json
artifacts/selection_audit/stage8_21/runtime_boundary.json
artifacts/selection_audit/stage8_21/next_route_decision.json
```

## Next Route

Stage 8.21 routes to:

```text
Stage 8.22: freeze_llm_origin_beat_best_reward_policy
```

The freeze stage should preserve the selected LLM-origin policy and prepare it
for CEC2013 F13/F14 multiseed evidence. It should not jump directly to a SOTA
claim.
