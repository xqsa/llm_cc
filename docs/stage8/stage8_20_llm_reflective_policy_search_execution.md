# Stage 8.20 LLM-reflective Coordination Policy Search Execution

创建日期：2026-06-22
执行者：Codex

## 1. Boundary

Stage 8.20 is the executable stage after the Stage 8.19 design lock. Its job is
to run an LLM-reflective shared-variable coordination policy search loop, or to
stop honestly with `BLOCKED_NEEDS_REAL_LLM_API` when a real LLM API cannot be
used.

This stage must not fabricate LLM candidates. Unit tests may inject a fake
provider to test the execution path, but committed runtime artifacts must record
whether a real provider was actually used.

Stage 8.20 is not a final objective-value performance claim and not a SOTA
claim.

## 2. What Changed

Stage 8.19 rejected static one-shot LLM candidate generation. Stage 8.20
therefore implements a loop:

```text
Stage 8.19 contracts
-> API preflight
-> reflection prompt context
-> LLM policy batch
-> DSL / boundary audit
-> train-side objective evaluator
-> feedback into next reflection round
-> beat-best_reward gate
```

If the API cannot be reached, the stage writes blocked artifacts instead of
pretending that LLM generation happened.

## 3. Required Policy Program Scope

The LLM output is constrained to shared-variable coordination policy programs.
It is not allowed to generate optimizers, schedulers, controllers, BaseOpt
changes, benchmark objectives, or validation/test feedback logic.

Allowed actions:

```text
trust_best_reward
damp_best_reward
weighted_consensus
simple_consensus
shrinkage_repair
reject_unstable_best_reward
```

The target scope remains:

```text
shared_variables_only
```

## 4. Blocked State

The legal blocked state is:

```text
status = BLOCKED_NEEDS_REAL_LLM_API
llm_call_used = false
real_llm_api_called = false
new_llm_candidate_generation_used = false
fake_llm_candidates_used = false
FE_total = 0
next_route = WAIT_FOR_REAL_LLM_API
```

This is an honest execution result, not a failure of the research idea. It means
the next meaningful step requires a usable real LLM API.

## 5. Pass Gate

A true Stage 8.20 `PASS` requires:

```text
reflection_round_count >= 2
raw_llm_candidate_count >= 24
quality_pass_candidate_count >= 8
coordination_family_count >= 4
selected_candidate_origin = llm_reflective_generated
selected_candidate_not_equivalent_to_best_reward = true
non_trust_best_reward_branch_exercised = true
train_objective_win_count_vs_best_reward >= 1
train_objective_loss_count_vs_best_reward = 0
objective_evaluator_feedback_used = true
```

In plain terms, tying `best_reward_select` is not enough. The selected policy
must have a non-degenerate mechanism and must beat `best_reward_select` on at
least one train-side case without losing on the train-side gate.

## 6. Artifacts

```text
configs/stage8_20_llm_reflective_policy_search_execution.yaml
docs/stage8/stage8_20_llm_reflective_policy_search_execution.md
docs/stage8/stage8_20_self_check_report.md
loco/coordination/llm_reflective_policy_search_execution.py
scripts/stage8/run_stage8_20_llm_reflective_policy_search_execution.py
tests/stage8/test_stage8_20_llm_reflective_policy_search_execution.py
artifacts/selection_audit/stage8_20/llm_reflective_search_report.json
artifacts/selection_audit/stage8_20/api_preflight_report.json
artifacts/selection_audit/stage8_20/reflection_prompt_context.json
artifacts/selection_audit/stage8_20/reflection_rounds.jsonl
artifacts/selection_audit/stage8_20/raw_llm_candidates.jsonl
artifacts/selection_audit/stage8_20/accepted_candidates.jsonl
artifacts/selection_audit/stage8_20/rejected_candidates.jsonl
artifacts/selection_audit/stage8_20/static_audit_report.json
artifacts/selection_audit/stage8_20/candidate_evaluator_report.json
artifacts/selection_audit/stage8_20/fe_ledger.json
artifacts/selection_audit/stage8_20/runtime_boundary.json
artifacts/selection_audit/stage8_20/next_route_decision.json
```

## 7. Next Step

If Stage 8.20 is blocked, rerun it after providing a real LLM API.

If Stage 8.20 passes with a real LLM API, the next stage is:

```text
Stage 8.21: llm_vs_non_llm_contribution_ablation
```

Stage 8.20 remains not a SOTA claim and not a final objective-value performance
claim.
