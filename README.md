# LOCO-LSGO

LLM-Evolved Coordination Operators for Overlapping Large-Scale Global Optimization.

LOCO-LSGO studies a deliberately narrow problem in overlapping LSGO:

```text
shared-variable conflict -> coordination operator -> more stable cooperative coevolution
```

The project does **not** use LLMs to generate a new optimizer. It does not generate DE, CMA-ES, PSO, SHADE, schedulers, controllers, optimizer selectors, or benchmark objectives. The intended Stage 3 role of LLM + evolution is only to discover reusable **coordination operator ASTs** that act on shared variables in overlapping subcomponents.

## Current Status

Current repository state: `Stage 8.2 PASS` — Stage 8.2 has embedded the Stage 8.1 selection-ready operator set into a fixed objective-level LOCO-CC loop, compared it against the frozen Stage 5.1 selected operator, and produced objective-level utility evidence under the locked Stage 7.0 protocol without turning the result into a final performance claim.

Stage 8.0 is not a final objective-value performance claim and not a SOTA claim. It is a train-only improvement record, not a CEC2013 benchmark run. It does not use LLM calls, new candidate generation, selected-operator revision, evolution/search, new objective evaluation, benchmark execution, reported-results reuse as runtime feedback, paper table extraction into runtime logic, test-feedback tuning, BaseOpt modification, or optimizer/controller/scheduler generation.

Historical checkpoint: Current repository state: `Stage 7.4 PASS` remains the prior milestone that introduced the optional CEC2013 F13/F14 decision gate.
Historical checkpoint: Current repository state: `Stage 7.6 PASS` remains the prior comparator-audit milestone before Stage 8.0.

Current stage map:

```text
Stage 0      research contract and boundary lock                 PASS
Stage 1      benchmark/data layer and CEC2013 LSGO semantics      PASS
Stage 2      conflict-state, metrics, FE accounting, readiness    PASS
Stage 3      LLM candidate supply, audit, freeze, family lock      PASS
Stage 4.0    deterministic train-only search over frozen pool      PASS
Stage 4.1    train-search audit and tie-hardened promotion rule    PASS
Stage 5.0    validation-only selection                            PASS
Stage 5.1    selected operator freeze                             PASS
Stage 6.0    sealed test reporting protocol and minimal runner     PASS
Stage 6.1    baseline ablation and failure analysis                PASS
Stage 7.0    objective-level evaluation protocol lock              PASS
Stage 7.1    minimal LOCO-CC objective loop pilot                  PASS
Stage 7.2    synthetic large-scale objective panel                 PASS
Stage 7.3    objective result polish and paper-ready tables         PASS
Stage 7.4    optional CEC2013 F13/F14 objective panel decision      PASS
Stage 7.5    SOTA-targeted real benchmark protocol lock             PASS
Stage 7.6    reported-results comparator audit                      PASS
Stage 8.0    train-only operator improvement                        PASS
Stage 8.1    train-only selection audit                             PASS
Stage 8.2    objective-level utility pilot                          PASS
Stage 8.3    train-only or validation selection over utility evidence NEXT
```

The project is now past candidate generation, train-search promotion, validation-only selection, selected-operator freeze, the first sealed-test reporting surface, the baseline/ablation/failure-analysis layer, the Stage 7.0 objective-level evaluation protocol lock, the Stage 7.1 minimal objective-loop pilot, the Stage 7.2 synthetic large-scale objective panel, the Stage 7.3 paper-ready result polish, the Stage 7.4 optional CEC2013 F13/F14 panel decision, the Stage 7.5 SOTA-targeted real benchmark protocol lock, the Stage 7.6 reported-results comparator audit, Stage 8.0 train-only operator improvement, Stage 8.1 train-only selection audit, and Stage 8.2 objective-level utility pilot. The next frontier is Stage 8.3: train-only or validation selection over objective-level utility evidence.

## What Stage 3 Established

Stage 3 should be read as a candidate-generation, audit, freeze, and search-boundary locking phase. It did not run evolution, execute candidate ASTs in an optimization loop, evaluate objectives for performance, or use validation/test feedback.

1. Protocol and firewall lock

   Stage 3.0 locked the boundary-constrained typed-AST search protocol, including the LLM candidate wrapper schema, prompt contract, train/validation/test firewall, and protocol-lock report.

```text
status = PASS
stage3_allowed = true
no_llm_call = true
no_evolution_run = true
not_performance_claim = true
```

2. Train-only LLM candidate supply

   Stage 3.1 to Stage 3.3 proved that typed-AST candidate wrappers can be captured, parsed, logged, rejected or accepted, deduplicated, and replayed through the audit chain. Stage 3.2 made one real DeepSeek-compatible chat API smoke call, and Stage 3.3 made three real train-only API calls. Sanitized response artifacts were saved with secret redaction.

```text
split = train
stage3_1_accepted_count = 1
stage3_1_rejected_count = 2
stage3_2_api_called = true
stage3_2_accepted_count = 1
stage3_3_api_call_count = 3
stage3_3_raw_candidate_count = 9
stage3_3_unique_accepted_count = 9
no_evolution_run = true
no_objective_evaluation = true
secret_redacted = true
not_performance_claim = true
```

3. Candidate audit and prompt-space hardening

   Stage 3.4 showed that the first real multi-batch corpus was boundary-valid but structurally narrow, mostly `weighted_consensus->clip`. Stage 3.5 then hardened the prompt space and produced a broader quality-pass pool with projection, dampening, reweighting, repair, and best_reward_select coverage.

```text
status = PASS
stage3_4_quality_pass_count = 7
stage3_4_low_diversity_warning = true
stage3_5_raw_candidate_count = 12
stage3_5_quality_pass_count = 12
stage3_5_unique_kind_sequence_count = 8
stage3_5_operator_family_count = 8
dominant_ratio = 0.25
must_include_projection = true
must_include_dampening = true
must_include_reweighting = true
must_include_repair = true
must_include_best_reward_select = true
not_performance_claim = true
```

4. Frozen train-only input for Stage 4

Stage 3.6 froze the Stage 3.5 quality-pass candidate pool as immutable train-only input and prepared the Stage 4 search protocol boundary.

```text
status = PASS
source_stage = 3.5
frozen_candidate_count = 12
quality_pass_only = true
family_count = 8
candidate_pool_frozen = true
train_only_search_protocol_prepared = true
next_status = READY_FOR_STAGE4_TRAIN_ONLY_SEARCH
no_llm_call = true
no_evolution_run = true
no_objective_evaluation = true
no_test_feedback = true
not_performance_claim = true
```

## What Stage 7 Established

Stage 7 is the objective-evaluation and claim-boundary phase. It keeps strict separation between protocol locks, optional panel decisions, and reported-results audit.

1. Objective protocol lock

   Stage 7.0 locked the objective-level evaluation protocol before any new large-scale objective claims.

2. Minimal LOCO-CC objective loop

   Stage 7.1 established the smallest objective-loop pilot without converting it into a performance claim.

3. Synthetic large-scale objective panel

   Stage 7.2 ran a synthetic large-scale objective panel to explore the objective surface under the frozen coordination-operator line.

4. Paper-ready result polish

   Stage 7.3 consolidated the paper-facing result layer while keeping the claim boundary explicit.

5. Optional CEC2013 decision gate

   Stage 7.4 decided whether a real F13/F14 objective panel was warranted.

6. SOTA-targeted protocol lock

   Stage 7.5 locked the same-setting comparator contract for reported results.

7. Reported-results comparator audit

   Stage 7.6 classified published results into direct comparator and background-only buckets under the Stage 7.5 contract. It did not turn those reported values into runtime feedback or performance claims.

8. Train-only operator improvement

   Stage 8.0 ranked the frozen Stage 3.6 candidates with deterministic train-only signals while preserving the Stage 7.6 comparator boundary. It did not use validation/test feedback, objective evaluation, benchmark execution, or reported results as runtime feedback.

```text
status = PASS
source_stage = 7.6
candidate_pool_source_stage = 3.6
candidate_count = 12
improvement_candidate_count = 4
train_only_improvement_executed = true
comparator_contract_used = true
next_status = READY_FOR_STAGE8_1_TRAIN_ONLY_SELECTION_AUDIT
FE_total = 12
not_performance_claim = true
```

5. Literature-grounded family vocabulary lock

   Stage 3.7 added the Coordination Family Literature Grounding and Allowed Vocabulary Lock. It defines the allowed F0-F9 coordination families, legal train-time signals, forbidden vocabulary, shared-variable-only scope, split firewall, and FE accounting boundary that Stage 4 must preserve.

```text
status = READY_FOR_STAGE4_TRAIN_ONLY_SEARCH_AFTER_FAMILY_LOCK
families = F0..F9
target_scope = shared_variables_only
allowed_split = train
validation_usage = selection only after train search
test_usage = sealed final reporting only
fe_accounting_policy = count_all_extra_function_evaluations
no_llm_call = true
no_evolution_run = true
no_ast_execution = true
no_objective_evaluation = true
no_test_feedback = true
not_performance_claim = true
```

In compact form, Stage 3 completed the following chain:

```text
typed-AST protocol lock
-> train-only LLM candidate capture
-> replay and wrapper audit
-> static quality/diversity audit
-> prompt-space hardening
-> frozen quality-pass pool
-> literature-grounded family vocabulary lock
```

Stage 3 therefore proves supply-chain legality and vocabulary coverage. It does **not** prove operator utility, benchmark improvement, or SOTA performance.

## What Stage 4 Established

Historical Stage 4 gate: Do not run Stage 4 evolution/search before the Stage 3.7 family lock is preserved.

Stage 4 train-only evolution/search became allowed only after the Stage 3.7 family lock was preserved. Stage 4 then converted the frozen Stage 3 candidate pool into a deterministic train-only ranking and audited the promotion decision. It still did not use validation feedback, sealed-test feedback, objective evaluation, or AST execution.

The Stage 4.0 train-only search currently records:

```text
status = PASS
source_stage = 3.6
family_lock_stage = 3.7
candidate_count = 12
promotion_candidate_count = 3
allowed_split = train
train_only_search_executed = true
next_status = READY_FOR_STAGE4_1_TRAIN_SEARCH_AUDIT
FE_total = 12
llm_call_used = false
new_candidate_generation_used = false
validation_feedback_used = false
test_feedback_used = false
ast_execution_used = false
objective_evaluation_used = false
baseopt_modified = false
not_performance_claim = true
```

Stage 4.1 found that the original top-k promotion rule would cut through a score tie. The hardened rule now includes every candidate tied at the cutoff instead of selecting an arbitrary subset.

The Stage 4.1 train search audit currently records:

```text
status = PASS
source_stage = 4.0
candidate_count = 12
original_promotion_top_k = 3
top_score_tie_count = 6
boundary_tie_detected = true
promotion_rule_hardened = true
hardened_promotion_candidate_count = 6
rule_name = include_all_candidates_tied_at_cutoff
next_status = READY_FOR_STAGE5_VALIDATION_SELECTION
validation_feedback_used = false
test_feedback_used = false
objective_evaluation_used = false
ast_execution_used = false
not_performance_claim = true
```

Stage 4 therefore establishes a validation-ready set, not a final operator. The direct Stage 5.0 input is:

```text
artifacts/search/stage4_1/promotion_decision.json
```

## Current Frontier And Next Step

The current frontier is no longer candidate generation, train search,
validation selection, selected-operator freeze, or protocol-only sealed-test
setup. LOCO-LSGO has completed the candidate-supply chain, frozen train-only
candidate pool, train-only search trace, promotion-rule hardening,
validation-only selection, selected operator freeze, and a minimal sealed-test
coordination diagnostics runner. Stage 6.1 has also completed baseline
comparison, ablation-style deltas, failure-analysis cautions, and a claim
boundary for the sealed-test diagnostics. Stage 7.0 now locks how the next
objective-level large-scale evaluation must be run before any objective-loop
runner or benchmark result is produced. Stage 7.1 implemented the minimal
LOCO-CC objective loop pilot and ran all locked Stage 7 methods on a small
synthetic sphere objective loop. Stage 7.2 has now expanded that loop to the
locked synthetic panels under same FE budget. Stage 7.3 has converted those
traces into paper-ready tables, curve data, method ranking, and an explicit
claim boundary. Stage 7.4 has decided that the mixed synthetic evidence
warrants an optional CEC2013 F13/F14 objective panel before any strong empirical
claim. Stage 7.5 then locks how any published comparator result may be reused
under the same-setting contract.

Current Stage 6.1 diagnostic result:

```text
source_stage = 6.0
selected_candidate_id = stage3_5_batch_1_weighted_consensus_projection
analysis_scope = sealed-test baseline diagnostics only
method_count = 4
baseline_method_count = 3
selected_method_name = selected_loco_operator
selected_rank_by_distance_to_best = 1
selected_case_win_count_by_distance = 3 / 3
best_baseline_method_name = weighted_consensus
selected_minus_best_baseline_distance_to_best = -0.075959270594
failure_modes = selected_uses_larger_update_than_baselines, objective_value_not_observed
not_performance_claim = true
not_sota_claim = true
```

Stage 6.1 read only the Stage 6.0 sealed-test reporting artifacts:

```text
artifacts/sealed_test/stage6_0/sealed_test_trace.jsonl
artifacts/sealed_test/stage6_0/sealed_test_metrics.json
artifacts/sealed_test/stage6_0/fe_ledger.json
artifacts/sealed_test/stage6_0/final_reporting_boundary.json
artifacts/sealed_test/stage6_0/sealed_test_report.json
```

It analyzed the fixed method set:

```text
identity_no_coord
simple_consensus
weighted_consensus
selected_loco_operator
```

Stage 6.1 did not revise the Stage 5.0 validation rule, rerun train search,
add new candidates, or use test feedback to tune the method.

Stage 5.0 produced:

```text
artifacts/validation/stage5_0/validation_trace.jsonl
artifacts/validation/stage5_0/validation_metrics.json
artifacts/validation/stage5_0/selection_decision.json
artifacts/validation/stage5_0/fe_ledger.json
artifacts/validation/stage5_0/validation_report.json
```

Stage 5.1 produced:

```text
artifacts/selected/stage5_1/selected_operator.json
artifacts/selected/stage5_1/selected_operator_ast.json
artifacts/selected/stage5_1/selected_operator_manifest.json
artifacts/selected/stage5_1/sealed_test_readiness_protocol.json
artifacts/selected/stage5_1/freeze_report.json
```

Stage 6.0 produced:

```text
artifacts/sealed_test/stage6_0/sealed_test_trace.jsonl
artifacts/sealed_test/stage6_0/sealed_test_metrics.json
artifacts/sealed_test/stage6_0/fe_ledger.json
artifacts/sealed_test/stage6_0/final_reporting_boundary.json
artifacts/sealed_test/stage6_0/sealed_test_report.json
```

Stage 6.1 produced:

```text
artifacts/sealed_test/stage6_1/baseline_comparison_table.json
artifacts/sealed_test/stage6_1/ablation_summary.json
artifacts/sealed_test/stage6_1/failure_analysis.json
artifacts/sealed_test/stage6_1/claim_boundary.json
artifacts/sealed_test/stage6_1/analysis_report.json
```

Stage 7.0 produced:

```text
configs/stage7_0_objective_eval_protocol.yaml
docs/stage7/stage7_0_objective_eval_protocol.md
docs/stage7/stage7_0_self_check_report.md
tests/stage7/test_stage7_0_objective_eval_protocol.py
```

Stage 7.1 produced:

```text
configs/stage7_1_objective_loop_pilot.yaml
docs/stage7/stage7_1_objective_loop_pilot.md
docs/stage7/stage7_1_self_check_report.md
loco/coordination/objective_loop_pilot.py
scripts/stage7/run_stage7_1_objective_loop_pilot.py
tests/stage7/test_stage7_1_objective_loop_pilot.py
artifacts/objective_eval/stage7_1/objective_trace.jsonl
artifacts/objective_eval/stage7_1/method_summary.json
artifacts/objective_eval/stage7_1/fe_ledger.json
artifacts/objective_eval/stage7_1/runtime_boundary.json
artifacts/objective_eval/stage7_1/pilot_report.json
```

Current Stage 7.1 pilot result:

```text
stage = 7.1
status = PASS
pilot_scope = minimal_loco_cc_objective_loop_pilot
problem_dimension = 500
synthetic_panel = synthetic_conflicting_overlap_panel
method_count = 5
objective_step_count_per_method = 3
trace_row_count = 15
FE_proposal = 15
FE_global_objective = 15
FE_total = 30
objective_benchmark_run = false
not_final_performance_claim = true
next_status = READY_FOR_STAGE7_2_SYNTHETIC_LARGE_SCALE_PANEL
```

Stage 7.2 produced:

```text
configs/stage7_2_synthetic_objective_panel.yaml
docs/stage7/stage7_2_synthetic_objective_panel.md
docs/stage7/stage7_2_self_check_report.md
loco/coordination/synthetic_objective_panel.py
scripts/stage7/run_stage7_2_synthetic_objective_panel.py
tests/stage7/test_stage7_2_synthetic_objective_panel.py
artifacts/objective_eval/stage7_2/objective_trace.jsonl
artifacts/objective_eval/stage7_2/panel_summary.json
artifacts/objective_eval/stage7_2/method_summary.json
artifacts/objective_eval/stage7_2/fe_ledger.json
artifacts/objective_eval/stage7_2/runtime_boundary.json
artifacts/objective_eval/stage7_2/panel_report.json
```

Current Stage 7.2 synthetic objective-panel result:

```text
stage = 7.2
status = PASS
panel_scope = synthetic_large_scale_objective_panel
dimensions = [500, 1000]
seeds = [0]
synthetic_panel_count = 4
method_count = 5
objective_step_count_per_method_per_panel = 3
trace_row_count = 120
FE_proposal = 120
FE_global_objective = 120
FE_total = 240
same_budget_across_methods = true
objective_benchmark_run = false
not_final_performance_claim = true
next_status = READY_FOR_STAGE7_3_OBJECTIVE_RESULT_POLISH
```

Stage 7.0 locks the LOCO-CC objective-level evaluation protocol:

```text
LOCO-CC = fixed BaseOpt
        + oracle grouping / detected grouping
        + frozen selected_loco_operator
        + online shared-variable conflict states
        + global objective evaluation
```

Required Stage 7 baselines:

```text
identity_no_coord
simple_consensus
weighted_consensus
best_reward_select
selected_loco_operator
```

Required synthetic large-scale panels:

```text
synthetic_no_overlap_panel
synthetic_low_overlap_panel
synthetic_conflicting_overlap_panel
synthetic_high_overlap_panel
```

Objective-level FE accounting is now locked as:

```text
FE_total = FE_grouping + FE_proposal + FE_coordination_extra + FE_repair + FE_global_objective
```

Stage 6.1 preserves:

```text
no LLM call
no new candidate generation
no prompt revision
no train-search revision
no promotion-rule revision
no validation-rule revision
no test-feedback tuning
no objective evaluation
no BaseOpt modification
no optimizer/controller/scheduler generation
full FE accounting
oracle grouping and detected grouping reported separately
no SOTA overclaim
```

Stage 7.0 preserves:

```text
no LLM call
no new candidate generation
no selected-operator revision
no evolution/search run
no objective benchmark run
no test-feedback tuning
no BaseOpt modification
no optimizer/controller/scheduler generation
not a performance claim
not an objective-value performance claim
not a SOTA claim
```

Stage 7.1 preserves:

```text
no LLM call
no new candidate generation
no selected-operator revision
no evolution/search run
no test-feedback tuning
no BaseOpt modification
no optimizer/controller/scheduler generation
not a SOTA claim
not a final objective-value performance claim
```

Stage 7.2 preserves:

```text
no LLM call
no new candidate generation
no selected-operator revision
no evolution/search run
no test-feedback tuning
no BaseOpt modification
no optimizer/controller/scheduler generation
not a SOTA claim
not a final objective-value performance claim
```

Stage 7.3 produced:

```text
configs/stage7_3_objective_result_polish.yaml
docs/stage7/stage7_3_objective_result_polish.md
docs/stage7/stage7_3_self_check_report.md
loco/coordination/objective_result_polish.py
scripts/stage7/run_stage7_3_objective_result_polish.py
tests/stage7/test_stage7_3_objective_result_polish.py
artifacts/objective_eval/stage7_3/paper_objective_table.csv
artifacts/objective_eval/stage7_3/objective_curve_table.csv
artifacts/objective_eval/stage7_3/method_ranking.json
artifacts/objective_eval/stage7_3/claim_boundary.json
artifacts/objective_eval/stage7_3/paper_tables_report.json
```

Current Stage 7.3 objective result-polish summary:

```text
stage = 7.3
status = PASS
polish_scope = paper_ready_objective_tables
source_trace_row_count = 120
paper_objective_row_count = 40
objective_curve_row_count = 120
best_overall_method = simple_consensus
selected_loco_operator_rank_overall = 4
selected_loco_operator_best_panel_dimension_count = 2
new_objective_evaluation_used = false
stage7_2_artifacts_modified = false
not_final_performance_claim = true
next_status = READY_FOR_OPTIONAL_CEC2013_OR_PAPER_DRAFT
```

Stage 7.3 preserves:

```text
no LLM call
no new candidate generation
no selected-operator revision
no evolution/search run
no new objective evaluation
no test-feedback tuning
no BaseOpt modification
no optimizer/controller/scheduler generation
not a SOTA claim
not a final objective-value performance claim
```

The current synthetic result is mixed, not a victory lap:

```text
selected_loco_operator_rank_overall = 4
best_overall_method = simple_consensus
current synthetic evidence does not support final objective-value performance superiority
```

Recommended next step:

```text
Stage 7.4: Optional CEC2013 F13/F14 Objective Panel Decision
```

Stage 7.4 decided whether the paper needs an optional CEC2013 F13/F14 objective panel before drafting the empirical section. Stage 7.5 then locks the same-setting comparison protocol. If the paper remains a failure-honest prototype/methodology paper, Stage 7.3 is already enough to start writing the result section with clear limitations.

Stage 7.4 produced:

```text
configs/stage7_4_cec2013_panel_decision.yaml
docs/stage7/stage7_4_cec2013_panel_decision.md
docs/stage7/stage7_4_self_check_report.md
loco/coordination/cec2013_panel_decision.py
scripts/stage7/run_stage7_4_cec2013_panel_decision.py
tests/stage7/test_stage7_4_cec2013_panel_decision.py
artifacts/objective_eval/stage7_4/cec2013_panel_decision.json
artifacts/objective_eval/stage7_4/cec2013_optional_panel_protocol.json
artifacts/objective_eval/stage7_4/cec2013_readiness_summary.json
artifacts/objective_eval/stage7_4/claim_boundary.json
artifacts/objective_eval/stage7_4/decision_report.json
```

Current Stage 7.4 decision:

```text
stage = 7.4
status = PASS
decision = RUN_OPTIONAL_CEC2013_F13_F14_PANEL
decision_reason = stage7_3_mixed_synthetic_evidence_needs_real_overlap_panel
metabox_smoke_status = PASS
f13_ready = true
f14_ready = true
cec2013_panel_run = false
new_objective_evaluation_used = false
next_status = READY_FOR_STAGE7_5_OPTIONAL_CEC2013_PANEL_PROTOCOL_OR_PAPER_DRAFT
```

Prepared CEC2013 semantics:

```text
target_functions = F13, F14
D_formula = 905
D_api = 1000
shared_variable_count = 95
overlap_ratio = 95 / 905
F13 overlap_semantics = conforming_overlap
F14 overlap_semantics = conflicting_overlap
F13 adapter_mode = implementation_api_adapter
F14 adapter_mode = direct_metabox_dimension
```

Stage 7.4 preserves:

```text
no LLM call
no new candidate generation
no selected-operator revision
no evolution/search run
no new objective evaluation
no CEC2013 panel run in Stage 7.4
no test-feedback tuning
no BaseOpt modification
no optimizer/controller/scheduler generation
not a SOTA claim
not a final objective-value performance claim
```

## Completion Distance

This project is already a concrete research prototype rather than a loose idea:
the research boundary, benchmark/data layer, conflict-coordination
infrastructure, typed-AST candidate supply, frozen candidate pool, train-only
search trace, and promotion-rule audit are all in place.

Current estimated completion:

```text
Concept and contribution framing:       90%
Protocol and leakage-control boundary:  85%
Engineering prototype:                  80%
Candidate generation and audit chain:   90%
Train-only search and promotion audit:  80%
Validation evidence:                    65%
Selected-operator freeze:               90%
Sealed-test diagnostics surface:        70%
Objective-level protocol readiness:     90%
Minimal objective-loop integration:     85%
Large-scale objective-loop evidence:    35-45%
Paper-ready empirical case:             65-72%
```

In plain terms:

```text
Distance to a completed innovation prototype: about 82-86% done
Distance to a credible objective-level short paper: about 60-68% done
Distance to a strong final performance claim: about 25-35% done
```

The main remaining gap is not more LLM generation. The main remaining gap is
evidence:

```text
Stage 7.3 objective result polish and paper-ready tables
-> optional CEC2013 F13/F14 objective panel decision
```

Known benchmark boundary:

- MetaBox F13 is evaluated through an explicit `implementation_api_adapter`: LOCO preserves `D_formula=905` for official overlap semantics and uses `runtime_dimension=1000` because the MetaBox F13 implementation/API exposes 1000-length internal data (`Ovector`, `Pvector`, and `s` sum).
- F14 real conflicting-overlap smoke can pass in a properly prepared local MetaBox environment with direct `D_formula=905` evaluation, but real MetaBox smoke tests remain optional and may skip in CI-style environments when MetaBox is unavailable.

## What Stage 2 Established

Stage 2 should be read as an infrastructure and evidence-gate phase, not as an optimizer-performance phase. It established four pieces.

1. Conflict-state and baseline coordination evidence

   Stage 2 introduced shared-variable conflict-state construction, conflict metrics, deterministic baseline coordination rules, FE accounting, and synthetic runners. These runners are diagnostic harnesses: they create proposal conflicts, apply coordination rules, and record what happened under controlled synthetic overlap settings.

2. Metric honesty and regenerated-conflict separation

   Stage 2 separates same-round proposal collapse from longitudinal conflict behavior. `proposal_consensus_collapse_ratio` only measures how much the current proposal set collapses after coordination; it is not longitudinal conflict reduction. Regenerated-conflict reports and multi-round evidence are recorded separately as diagnostics, still without claiming SOTA optimizer performance.

3. Typed operator boundary

   Stage 2 defined a typed coordination-operator AST boundary for future Stage 3 work. The boundary is shared-variable-only and rejects attempts to generate optimizers, controllers, schedulers, arbitrary executable code, test-set metadata access, or benchmark-specific shortcuts. Frozen AST smoke paths exercise the runtime shell without calling an LLM or running evolution.

4. Artifact, replay, and readiness chain

   Stage 2 added candidate logging schemas, rejection corpus handling, sealed split replay audits, frozen candidate promotion, promotion replay, artifact registry checks, and the pre-Stage-3 readiness decision. This chain exists so future Stage 3 candidates can be audited by provenance, split discipline, fingerprint stability, and boundary legality.

Detailed Stage 2 records remain under:

```text
docs/stage2/
configs/
artifacts/
tests/stage2/
```

## Repository Layout

```text
configs/              Stage boundary and benchmark configuration drafts
artifacts/operators/  Frozen coordination-operator artifacts and registries
artifacts/candidates/ Candidate AST accepted/rejected logs and replay reports
artifacts/readiness/  Pre-Stage-3 readiness decision artifacts
artifacts/search/     Stage 4 train-only search and promotion audit artifacts
artifacts/validation/ Stage 5 validation-only selection artifacts
artifacts/selected/   Stage 5 selected-operator freeze artifacts
artifacts/sealed_test/ Stage 6 sealed-test reporting artifacts
docs/stage0/          Research boundary and mathematical contracts
docs/stage1/          Benchmark/data-layer reports and CEC2013 LSGO semantics
docs/stage2/          Stage 2 reports, result JSON, CSV summaries, and audits
docs/stage3/          Stage 3 protocol lock, search-space, selection, and firewall docs
docs/stage4/          Stage 4 family-space grounding, train-only search, and audit docs
docs/stage5/          Stage 5 validation-only selection docs
docs/stage6/          Stage 6 sealed-test reporting docs
loco/benchmarks/      LSGOProblem interface, MetaBox adapter, synthetic overlap generator
loco/conflict/        Shared-variable conflict state and metrics
loco/coordination/    Baseline coordination rules, typed AST boundary, artifact helpers
loco/evaluation/      FE accounting
loco/experiments/     Stage 2 diagnostic runners
loco/llm/             Stage 3 prompt contract, provider client, candidate wrappers, and batch audit helpers
scripts/stage1/       Real MetaBox CEC2013 LSGO smoke script
scripts/stage3/       Stage 3 candidate generation, audit, and freeze runners
scripts/stage4/       Stage 4 train-only search and audit runners
scripts/stage5/       Stage 5 validation-only selection runner
scripts/stage6/       Stage 6 sealed-test reporting runner
tests/                Stage 0/1/2/3/4/5/6 tests
```

## Installation

Create an environment with Python 3.10+.

```powershell
python -m pip install -r requirements.txt
```

MetaBox is optional for the core test suite. The project uses MetaBox as a dependency/adapter for CEC2013 LSGO and does not copy or rewrite CEC2013 objective code.

For real MetaBox CEC2013 LSGO smoke tests, install `metaevobox` in an isolated environment following MetaBox's own requirements. Missing trainer/agent dependencies should not affect LOCO's synthetic Stage 2 diagnostic runners.

## Key Verification Commands

Run the full local test suite:

```powershell
python -m pytest -p no:cacheprovider tests -q -rs
```

Expected latest local result after Stage 7.4:

```text
187 passed
```

Run the Stage 2 readiness gate directly:

```powershell
python -m pytest tests\stage2\test_stage2_10_readiness_gate.py -q
```

Run the Stage 3.0 protocol lock gate directly:

```powershell
python -m pytest tests\stage3\test_stage3_0_protocol_lock.py -q
```

Run the Stage 3.1 candidate batch gate directly:

```powershell
python -m pytest tests\stage3\test_stage3_1_llm_candidate_batch.py -q
```

Run the Stage 3.2 LLM API smoke gate directly:

```powershell
python -m pytest tests\stage3\test_stage3_2_llm_api_smoke.py -q
```

Run the Stage 3.3 multi-batch candidate generation gate directly:

```powershell
python -m pytest tests\stage3\test_stage3_3_multi_batch_candidate_generation.py -q
```

Run the Stage 3.4 static candidate audit gate directly:

```powershell
python -m pytest tests\stage3\test_stage3_4_static_candidate_audit.py -q
```

Run the Stage 3.5 prompt-space hardening gate directly:

```powershell
python -m pytest tests\stage3\test_stage3_5_prompt_space_hardening.py -q
```

Run the Stage 3.6 frozen candidate pool gate directly:

```powershell
python -m pytest tests\stage3\test_stage3_6_freeze_candidate_pool.py -q
```

Run the Stage 3.7 coordination family lock gate directly:

```powershell
python -m pytest tests\stage4\test_coordination_family_space.py -q
```

Run the Stage 4.0 train-only search gate directly:

```powershell
python -m pytest tests\stage4\test_stage4_0_train_only_search.py -q
```

Run the Stage 4.1 train search audit gate directly:

```powershell
python -m pytest tests\stage4\test_stage4_1_train_search_audit.py -q
```

Run the Stage 5.0 validation-only selection gate directly:

```powershell
python -m pytest tests\stage5\test_stage5_0_validation_selection.py -q
```

Run the Stage 5.1 selected operator freeze gate directly:

```powershell
python -m pytest tests\stage5\test_stage5_1_selected_operator_freeze.py -q
```

Run the Stage 6.0 sealed-test reporting gate directly:

```powershell
python -m pytest tests\stage6\test_stage6_0_sealed_test_reporting.py -q
```

Run the Stage 6.1 baseline ablation analysis gate directly:

```powershell
python -m pytest tests\stage6\test_stage6_1_baseline_ablation_analysis.py -q
```

Run the Stage 7.0 objective-level evaluation protocol gate directly:

```powershell
python -m pytest tests\stage7\test_stage7_0_objective_eval_protocol.py -q
```

Run the Stage 7.1 minimal objective-loop pilot gate directly:

```powershell
python -m pytest tests\stage7\test_stage7_1_objective_loop_pilot.py -q
```

Run the Stage 7.2 synthetic objective-panel gate directly:

```powershell
python -m pytest tests\stage7\test_stage7_2_synthetic_objective_panel.py -q
```

Run the Stage 7.3 objective result-polish gate directly:

```powershell
python -m pytest tests\stage7\test_stage7_3_objective_result_polish.py -q
```

Run the Stage 7.4 optional CEC2013 decision gate directly:

```powershell
python -m pytest tests\stage7\test_stage7_4_cec2013_panel_decision.py -q
```

Run Stage 2 diagnostic runners when regenerating reports:

```powershell
python loco\experiments\stage2_minimal_runner.py
python loco\experiments\stage2_panel_runner.py
python loco\experiments\stage2_multiround_runner.py
```

Optional real MetaBox tests are allowed to skip only when F12/F13/F14 are not all complete PASS. They must give a clear reason and must not fake a real benchmark success.

## Benchmark And License Boundary

LOCO-LSGO reuses external benchmark implementations through dependencies/adapters.

- MetaBox / `metaevobox`: used as an optional dependency for CEC2013 LSGO access.
- CEC2013 LSGO objective implementations: not copied into this repository and not rewritten here.
- Synthetic overlap benchmarks: LOCO-controlled supplements for topology, overlap ratio, and dimension generalization.

See [LICENSE_NOTICE.md](LICENSE_NOTICE.md) and [docs/reproducibility.md](docs/reproducibility.md) for license and reproduction notes.

## Metric Honesty Note

Stage 2 reports `proposal_consensus_collapse_ratio`, not a true longitudinal conflict reduction claim.

This value measures how much the current set of proposals collapses after applying a coordination rule. It does **not** prove that future regenerated conflicts are reduced. Regenerated-conflict and multi-round reports are diagnostic evidence gates, not final optimizer-loop performance claims.

## FE Accounting

The project keeps this accounting identity:

```text
FE_total = FE_grouping + FE_proposal + FE_coordination_extra + FE_repair
```

Stage 7 objective-level evaluation extends this identity:

```text
FE_total = FE_grouping + FE_proposal + FE_coordination_extra + FE_repair + FE_global_objective
```

Stage 2 evaluates each baseline or frozen artifact-backed operator as a separate method run. Cross-baseline comparison evaluations are not shared across methods.

## Next Recommended Stage

Recommended next step:

```text
Stage 8.3: Train-only or validation selection over objective-level utility evidence
```

Stage 8.3 should use the objective-level utility evidence from Stage 8.2 for train-only or validation selection, while keeping the utility traces sealed from runtime feedback, candidate regeneration, and any BaseOpt modification.
