# Stage 8.26 MVP Strategy DSL and Behavior-Equivalence Checker

Created by Codex on 2026-06-23.

## Purpose

Stage 8.26 implements the MVP ownership-aware strategy DSL required by Stage 8.25.
The goal is not to run another CEC checkpoint and not to make a SOTA claim.
The goal is to make the next LLM loop designable and auditable:

```text
shared-variable conflict state
-> ownership/linkage/coordination strategy program
-> synthetic conflict-regime evaluator
-> behavior-equivalence checker
```

## What Changed

The DSL now represents a bounded strategy program with rules that can decide:

```text
shared_variable_owner
allow_multi_assignment
linkage_decision
coordination_action
fallback_repair_action
```

The evaluator runs a small train-side synthetic conflict-regime search over:

```text
trusted_best_reward
conflicting_overlap
conforming_overlap
unstable_best_reward
```

The behavior-equivalence checker rejects strategies that are behaviorally
equivalent to `best_reward_select`. A strategy must be not equivalent to
best_reward_select, must exercise a non-trust branch, and must exercise an
ownership or linkage decision.

## Selected MVP Strategy

```text
selected_strategy_id = ownership_conflict_guard_v1
```

The selected MVP strategy uses:

```text
conflicting_overlap -> contribution_leader + linkage break + owner_proposal_select
conforming_overlap  -> multi_owner + linkage preserve + multi_owner_weighted_vote
unstable_best_reward -> historical_owner + reject_unstable_best_reward fallback
trusted_best_reward -> trust_best_reward
```

This is deliberately small. It is a DSL/evaluator/checker proof, not a final
policy.

## Boundary

Stage 8.26 records:

```text
FE_total = 0
objective_loop_executed = false
new_objective_evaluation_used = false
llm_call_used = false
new_candidate_generation_used = false
baseopt_modified = false
not a final objective-value performance claim
not a SOTA claim
```

## Next Stage

Stage 8.27 should use the Stage 8.26 DSL and evaluator for real LLM reflective
ownership-aware strategy search.
