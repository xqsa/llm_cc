# Stage 8.28 LLM vs Non-LLM Ownership-strategy Ablation

Created by Codex on 2026-06-23.

## Purpose

Stage 8.28 tests whether the Stage 8.27 LLM-reflective ownership-aware strategy
pool contributes something beyond non-LLM alternatives.

The comparison pools are:

```text
LLM-reflective
hand-designed
random mutation
literature-inspired
```

All candidates are evaluated with the Stage 8.26 ownership-aware strategy DSL
evaluator and behavior-equivalence checker.

## Result

```text
llm_pool_best_rank = 1
llm_pool_beats_non_llm_pool_best = true
best_pool_name = llm_reflective_pool
selected_strategy_id = stage8_27_1
selected_strategy_origin = llm_reflective_generated
```

The selected strategy remains behavior-distinct:

```text
selected_strategy_not_equivalent_to_best_reward_select = true
non_trust_branch_exercised = true
ownership_or_linkage_decision_exercised = true
```

## Boundary

Stage 8.28 does not call an LLM and does not run an objective loop. It uses the
already generated Stage 8.27 LLM strategies and compares them against local
non-LLM pools.

```text
FE_total = 0
llm_call_used = false
new_llm_strategy_generation_used = false
objective_loop_executed = false
new_objective_evaluation_used = false
not a final objective-value performance claim
not a SOTA claim
```

## Next Stage

Stage 8.29 should freeze the exact behavior-distinct LLM-origin ownership-aware
strategy selected by Stage 8.28.
