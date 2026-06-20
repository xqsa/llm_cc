# LOCO-LSGO

LLM-Evolved Coordination Operators for Overlapping Large-Scale Global Optimization.

LOCO-LSGO studies a deliberately narrow problem in overlapping LSGO:

```text
shared-variable conflict -> coordination operator -> more stable cooperative coevolution
```

The project does **not** use LLMs to generate a new optimizer. It does not generate DE, CMA-ES, PSO, SHADE, schedulers, controllers, optimizer selectors, or benchmark objectives. The intended Stage 3 role of LLM + evolution is only to discover reusable **coordination operator ASTs** that act on shared variables in overlapping subcomponents.

## Current Status

Current repository state: `Stage 5.0 PASS` — Stage 5.0 has selected one candidate from the Stage 4.1 tie-hardened validation-ready set using validation-only conflict diagnostics. The selected candidate is `stage3_5_batch_1_weighted_consensus_projection`, with status `SELECTED_FOR_SEALED_TEST_NOT_FINAL`.

Stage 5.0 is not a performance claim. It uses validation feedback only after train search for selection, and it does not use sealed-test feedback, benchmark objective evaluation, LLM calls, new candidate generation, prompt revision, train-search revision, promotion-rule revision, BaseOpt modification, or optimizer/controller/scheduler generation.

Current stage map:

```text
Stage 0      research contract and boundary lock                 PASS
Stage 1      benchmark/data layer and CEC2013 LSGO semantics      PASS
Stage 2      conflict-state, metrics, FE accounting, readiness    PASS
Stage 3      LLM candidate supply, audit, freeze, family lock      PASS
Stage 4.0    deterministic train-only search over frozen pool      PASS
Stage 4.1    train-search audit and tie-hardened promotion rule    PASS
Stage 5.0    validation-only selection                            PASS
Stage 5.1    selected operator freeze                             NEXT
```

The project is now past candidate generation, train-search promotion, and validation-only selection. The next executable frontier is selected-operator freeze before sealed-test final reporting.

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

The current frontier is no longer candidate generation, train search, or
validation selection. LOCO-LSGO has completed the candidate-supply chain,
frozen train-only candidate pool, train-only search trace, promotion-rule
hardening, and validation-only selection. The active research frontier is now
freezing the selected operator before sealed-test reporting.

Next recommended step:

```text
Stage 5.1: selected operator freeze
```

Stage 5.1 should read only the Stage 5.0 selection decision:

```text
artifacts/validation/stage5_0/selection_decision.json
```

It should freeze `stage3_5_batch_1_weighted_consensus_projection` as the only
candidate eligible for sealed-test reporting. Stage 5.1 should not revise the
Stage 5.0 validation rule, rerun train search, add new candidates, or use sealed
test feedback.

Stage 5.0 produced:

```text
artifacts/validation/stage5_0/validation_trace.jsonl
artifacts/validation/stage5_0/validation_metrics.json
artifacts/validation/stage5_0/selection_decision.json
artifacts/validation/stage5_0/fe_ledger.json
artifacts/validation/stage5_0/validation_report.json
```

Stage 5.1 must still preserve:

```text
no LLM call
no new candidate generation
no prompt revision
no train-search revision
no promotion-rule revision
no validation-rule revision
no test feedback
no sealed-test access
no BaseOpt modification
no optimizer/controller/scheduler generation
not a performance claim
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
Engineering prototype:                  75%
Candidate generation and audit chain:   90%
Train-only search and promotion audit:  80%
Validation evidence:                    55%
Sealed-test evidence:                   10%
Paper-ready empirical case:             55-65%
```

In plain terms:

```text
Distance to a completed innovation prototype: about 75-80% done
Distance to a credible short paper: about 55-65% done
Distance to a strong final performance claim: about 25-35% done
```

The main remaining gap is not more LLM generation. The main remaining gap is
evidence:

```text
Stage 5.1 selected operator freeze
-> Stage 6.0 sealed test final reporting
-> Stage 6.1 baseline comparison, ablation, and failure analysis
-> paper claim polishing
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
docs/stage0/          Research boundary and mathematical contracts
docs/stage1/          Benchmark/data-layer reports and CEC2013 LSGO semantics
docs/stage2/          Stage 2 reports, result JSON, CSV summaries, and audits
docs/stage3/          Stage 3 protocol lock, search-space, selection, and firewall docs
docs/stage4/          Stage 4 family-space grounding, train-only search, and audit docs
docs/stage5/          Stage 5 validation-only selection docs
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
tests/                Stage 0/1/2/3/4/5 tests
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

Expected latest local result after Stage 5.0:

```text
171 passed
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

Stage 2 evaluates each baseline or frozen artifact-backed operator as a separate method run. Cross-baseline comparison evaluations are not shared across methods.

## Next Recommended Stage

Recommended next step:

```text
Stage 5.1: selected operator freeze
```

This next stage must freeze only the Stage 5.0 selected candidate, `stage3_5_batch_1_weighted_consensus_projection`, for sealed-test reporting. It must not feed validation results back into prompt generation, candidate generation, frozen pool contents, train-search scores, or promotion-rule design.
