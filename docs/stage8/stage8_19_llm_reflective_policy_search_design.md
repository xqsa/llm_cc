# Stage 8.19 LLM-reflective Coordination Policy Search Design Lock

创建日期：2026-06-22
执行者：Codex

## 1. Boundary

Stage 8.19 is a design-lock stage. It changes the next research route from a
static or one-shot LLM candidate expansion into an evaluator-grounded
LLM-reflective shared-variable coordination policy search.

It does not call an LLM, generate new candidates, execute objective loops,
revise the selected operator, or make a final performance / SOTA claim.

## 2. Why This Stage Exists

Stage 8.18 showed that `reward_trust_gated_coordination_v1` no longer loses to
`best_reward_select` on the CEC2013 F13/F14 single-run re-smoke. But it also
showed a serious mechanism problem:

```text
stage8_18_policy_equivalent_to_best_reward = true
non_trust_best_reward_branch_exercised_on_stage8_18 = false
trust_best_reward = 2400
weighted_safety = 0
simple_safety = 0
shrinkage_repair = 0
```

That means the current repaired policy behaves like `best_reward_select` on the
F13/F14 re-smoke. This is not enough for a SOTA-facing research claim, and it
does not make the LLM contribution convincing.

Stage 8.19 therefore rejects the old next step of simply running a multiseed
pilot. It locks a new route:

```text
failure mining
-> reflection prompt
-> LLM-generated coordination policy programs
-> static DSL / boundary audit
-> train-side objective evaluator
-> feedback to LLM
-> repaired / mutated policy programs
-> LLM vs non-LLM contribution ablation
-> freeze a non-degenerate beat-best_reward candidate
```

## 3. Design Contract

```text
llm_reflective_design_loop_locked = true
static_one_shot_llm_candidate_generation_rejected = true
objective_evaluator_feedback_required = true
llm_contribution_ablation_required = true
beat_best_reward_required = true
implementation_status = DESIGN_LOCK_ONLY
```

In plain terms:

```text
static one-shot LLM candidate generation is rejected.
fake LLM candidates are forbidden.
```

The next executable stage must use a real LLM API. If the LLM API is
unavailable, the next execution stage must report a blocked / needs-LLM state
instead of manufacturing fake candidates.

## 4. Reflection Prompt Contract

The future Stage 8.20 execution must build prompts from these failure patterns:

```text
best_reward_short_horizon_regret
shared_variable_oscillation
low_reward_margin_unreliability
direction_flip_under_conflicting_overlap
stage8_18_always_trust_best_reward_degeneracy
```

Minimum future execution requirements:

```text
minimum_reflection_round_count = 2
minimum_raw_llm_candidate_count = 24
minimum_quality_pass_candidate_count = 8
minimum_coordination_family_count = 4
real_llm_api_required_for_execution = true
```

The future loop must feed evaluator results back into the LLM. A single static
batch is not enough.

## 5. Coordination Policy DSL

The future LLM output must be a shared-variable coordination policy program,
not an optimizer.

Allowed features:

```text
reward_margin
reward_concentration
conflict_intensity
proposal_dispersion
direction_consistency
shared_variable_oscillation
recent_best_reward_regret
```

Allowed actions:

```text
trust_best_reward
damp_best_reward
weighted_consensus
simple_consensus
shrinkage_repair
reject_unstable_best_reward
```

Forbidden capabilities:

```text
optimizer_generation
baseopt_modification
controller_scheduler_generation
benchmark_objective_rewrite
validation_feedback_access
test_feedback_access
reported_results_runtime_feedback
```

## 6. LLM Contribution Ablation

Stage 8.20 must compare the LLM-reflective pool against non-LLM pools:

```text
llm_reflective_pool
hand_designed_pool
random_mutation_pool
literature_inspired_pool
stage8_16_human_repair_policy
```

The Stage 8.16 repaired policy is now treated as a human diagnostic repair
baseline, not as proof that the LLM found the final policy.

Required evidence:

```text
llm_vs_non_llm_ablation_required = true
llm_pool_beats_non_llm_pool_required_for_pass = true
```

## 7. Beat-best_reward Gate

The future executable stage cannot pass by merely tying `best_reward_select`.

```text
selected_candidate_origin_required = llm_reflective_generated
selected_candidate_not_equivalent_to_best_reward_required = true
non_trust_best_reward_branch_exercised_required = true
win_count_vs_best_reward_select_min = 1
loss_count_vs_best_reward_select_max = 0
pass_condition_is_not_no_loss = true
```

This makes "not losing" insufficient. The candidate must show a concrete
mechanism for beating `best_reward_select`.

## 8. FE Accounting

```text
FE_total = 0
inherited_stage8_18_FE_total = 28812
objective_loop_executed = false
new_objective_evaluation_used = false
llm_call_used = false
new_llm_candidate_generation_used = false
```

Stage 8.19 only locks the design. Future Stage 8.20 execution must count all
objective-consuming FE.

## 9. Artifacts

```text
configs/stage8_19_llm_reflective_policy_search_design.yaml
docs/stage8/stage8_19_llm_reflective_policy_search_design.md
docs/stage8/stage8_19_self_check_report.md
loco/coordination/llm_reflective_policy_search_design.py
scripts/stage8/run_stage8_19_llm_reflective_policy_search_design.py
tests/stage8/test_stage8_19_llm_reflective_policy_search_design.py
artifacts/selection_audit/stage8_19/llm_reflective_policy_search_design.json
artifacts/selection_audit/stage8_19/reflection_prompt_contract.json
artifacts/selection_audit/stage8_19/coordination_policy_dsl_contract.json
artifacts/selection_audit/stage8_19/llm_contribution_ablation_plan.json
artifacts/selection_audit/stage8_19/beat_best_reward_gate.json
artifacts/selection_audit/stage8_19/fe_ledger.json
artifacts/selection_audit/stage8_19/runtime_boundary.json
artifacts/selection_audit/stage8_19/next_route_decision.json
```

## 10. Next Step

```text
recommended_next_stage = Stage 8.20
recommended_next_work = execute_llm_reflective_coordination_policy_search
```

Stage 8.20 should execute the LLM-reflective loop with real LLM calls. If API
access is unavailable, it should stop honestly instead of faking an LLM result.

Stage 8.19 is not a final objective-value performance claim and not a SOTA
claim.

