# LOCO-LSGO

LLM-Evolved Coordination Operators for Overlapping Large-Scale Global Optimization.

LOCO-LSGO studies a deliberately narrow problem in overlapping LSGO:

```text
shared-variable conflict -> coordination operator -> more stable cooperative coevolution
```

The project does **not** use LLMs to generate a new optimizer. It does not generate DE, CMA-ES, PSO, SHADE, schedulers, controllers, optimizer selectors, or benchmark objectives. The intended Stage 3 role of LLM + evolution is only to discover reusable **coordination operator ASTs** that act on shared variables in overlapping subcomponents.

## Current Status

Current repository state: `Stage 4.1 PASS` — Stage 4 has audited the Stage 4.0 train-only search trace and hardened the promotion rule. The original top-3 cutoff split a six-candidate tie at score 1.0, so Stage 4.1 now promotes the full tied validation-ready set while preserving the no-validation-feedback, no-test-feedback, no-objective-evaluation, and not-performance-claim boundaries.

Stage 4.1 is not a performance claim.

- Stage 0 locked the research problem, mathematical contract, allowed/forbidden behavior, and acceptance boundary.
- Stage 1 built the benchmark/data layer, including the `LSGOProblem` interface, MetaBox lazy adapter, synthetic overlap generator, split manifests, and CEC2013 LSGO semantics correction.
- Stage 2 built the conflict-coordination infrastructure and readiness gates needed before any LLM/evolution search is allowed.
- Stage 3 completed the LLM candidate-supply chain and the pre-Stage-4 search boundary. It locked the typed-AST protocol, captured real train-only LLM candidate batches, audited candidate quality and diversity, hardened family coverage, froze the quality-pass pool, and locked the literature-grounded Stage 4 family vocabulary.
- Stage 4.0 ran deterministic train-only search over the frozen coordination-candidate pool, produced a ranked search trace and promotion candidates, and recorded an FE ledger while preserving the no-validation-feedback, no-test-feedback, no-objective-evaluation, and not-performance-claim boundaries.
- Stage 4.1 audited the Stage 4.0 search trace, detected that the top-k cutoff split a six-candidate score tie, and hardened the promotion rule to `include_all_candidates_tied_at_cutoff`.

The Stage 2 readiness artifact currently records:

```text
decision = READY_FOR_STAGE3_BOUNDARY_ONLY
stage3_allowed = true
not_performance_claim = true
```

This means Stage 3 may begin only as boundary-constrained typed coordination-operator AST search. It is **not** a claim that LOCO has learned final operators, beaten baselines, or achieved SOTA optimizer performance.

## What Stage 3 Established

Stage 3 should be read as a candidate-generation, audit, and pre-search locking phase. It did not run evolution, execute candidate ASTs in an optimization loop, evaluate objectives for performance, or use validation/test feedback.

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

Do not run Stage 4 evolution/search before the Stage 3.7 family lock is preserved. The next executable phase is Stage 4 train-only evolution/search, still under the frozen-pool, family-lock, and split-firewall boundaries.

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
docs/stage0/          Research boundary and mathematical contracts
docs/stage1/          Benchmark/data-layer reports and CEC2013 LSGO semantics
docs/stage2/          Stage 2 reports, result JSON, CSV summaries, and audits
docs/stage3/          Stage 3 protocol lock, search-space, selection, and firewall docs
docs/stage4/          Stage 4 family-space grounding, train-only search, and audit docs
loco/benchmarks/      LSGOProblem interface, MetaBox adapter, synthetic overlap generator
loco/conflict/        Shared-variable conflict state and metrics
loco/coordination/    Baseline coordination rules, typed AST boundary, artifact helpers
loco/evaluation/      FE accounting
loco/experiments/     Stage 2 diagnostic runners
loco/llm/             Stage 3 prompt contract, provider client, candidate wrappers, and batch audit helpers
scripts/stage1/       Real MetaBox CEC2013 LSGO smoke script
tests/                Stage 0/1/2/3/4 tests
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

Expected latest local result after Stage 4.0:

```text
168 passed
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
Stage 5.0: validation-only selection over tie-hardened validation-ready candidates
```

This next stage must use validation only for selection after train search; validation results must not feed back into prompt generation, candidate generation, frozen pool contents, or promotion-rule design.
