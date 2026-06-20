# LOCO-LSGO

LLM-Evolved Coordination Operators for Overlapping Large-Scale Global Optimization.

LOCO-LSGO studies a narrow problem in overlapping LSGO:

```text
shared-variable conflict -> coordination operator -> more stable cooperative coevolution
```

The project does **not** use LLMs to generate a new optimizer. It does not generate DE, CMA-ES, PSO, SHADE, schedulers, controllers, or optimizer selectors. The intended Stage 3 role of LLM + evolution is only to discover reusable coordination operators that act on shared variables in overlapping subcomponents.

## Current Status

Current repository stage: `Stage 2.9 PASS` locally; latest GitHub Actions should be checked for the current commit before publication claims.

Implemented:

- Stage 0: research problem lock and system boundary definition.
- Stage 1: benchmark/data layer with MetaBox lazy adapter, synthetic overlap generator, manifest support, and CEC2013 LSGO semantics correction.
- Stage 2.0: conflict state, conflict metrics, baseline coordination operators, FE accounting, and a minimal synthetic conflict-coordination runner.
- Stage 2.1: multi-setting synthetic conflict evidence panel across topology, dimension, overlap ratio, and seed settings.
- Stage 2.1B: multi-round post-coordination regenerated-conflict evidence gate.
- Stage 2.2: typed coordination operator DSL boundary and Stage 3 candidate-AST preflight.
- Stage 2.3: DSL interpreter/runtime shell for frozen typed ASTs.
- Stage 2.4: handwritten frozen AST smoke integration with the existing synthetic conflict runner.
- Stage 2.5: frozen AST artifact registry and train/validation/test split boundary hardening.
- Stage 2.6: candidate artifact logging schema, rejection corpus, and replay verifier.
- Stage 2.7: sealed split replay audit for candidate logs.
- Stage 2.8: frozen candidate promotion contract.
- Stage 2.9: promotion replay and registry audit.

Known benchmark boundary:

- MetaBox F13 is evaluated through an explicit `implementation_api_adapter`: LOCO preserves `D_formula=905` for official overlap semantics and uses `runtime_dimension=1000` because the MetaBox F13 implementation/API exposes 1000-length internal data (`Ovector`, `Pvector`, and `s` sum).
- F14 real conflicting-overlap smoke currently passes in the local environment with direct `D_formula=905` evaluation, but remains optional in CI-style tests.

## Repository Layout

```text
configs/              Stage boundary and benchmark configuration drafts
artifacts/operators/  Frozen coordination-operator artifacts and registries
artifacts/candidates/ Candidate AST accepted/rejected logs and replay reports
docs/stage0/          Research boundary and mathematical contracts
docs/stage1/          Benchmark/data-layer reports and CEC2013 LSGO semantics
docs/stage2/          Stage 2.0/2.1 result JSON, CSV summaries, and self-check reports
loco/benchmarks/      LSGOProblem interface, MetaBox adapter, synthetic overlap generator
loco/conflict/        Shared-variable conflict state and metrics
loco/coordination/    Baseline coordination operators
loco/evaluation/      FE accounting
loco/experiments/     Minimal Stage 2.0 runner
scripts/stage1/       Real MetaBox CEC2013 LSGO smoke script
tests/                Stage 0/1/2 tests
```

## Installation

Create an environment with Python 3.10+.

```powershell
python -m pip install -r requirements.txt
```

MetaBox is optional for the core test suite. The project uses MetaBox as a dependency/adapter for CEC2013 LSGO and does not copy or rewrite CEC2013 objective code.

For real MetaBox CEC2013 LSGO smoke tests, install `metaevobox` in an isolated environment following MetaBox's own requirements. Missing trainer/agent dependencies should not affect the synthetic Stage 2.0 runner.

## Run Tests

```powershell
python -m pytest -p no:cacheprovider tests -q -rs
```

Expected current local result:

```text
121 passed
```

Optional real MetaBox tests are allowed to skip only when F12/F13/F14 are not all complete PASS. They must give a clear reason and must not fake a real benchmark success.

## Run Current Minimal Runner

```powershell
python loco\experiments\stage2_minimal_runner.py
```

This writes:

```text
docs/stage2/stage2_5_artifact_registry_result.json
```

The runner uses a deterministic one-shot perturbation proposal generator. It is not an optimizer and should not be interpreted as performance evidence. Its current Stage 2.5 surface verifies that shared-variable conflict states, baseline coordination operators, a frozen AST artifact registry, DSL runtime interpretation, provenance logging, and FE accounting work end to end.

## Run Stage 2.6 Candidate Logging Replay

```powershell
python -m pytest tests\stage2\test_stage2_6_candidate_logging.py -q
```

This verifies:

```text
artifacts/candidates/stage2_6/accepted_candidates.jsonl
artifacts/candidates/stage2_6/rejected_candidates.jsonl
artifacts/candidates/stage2_6/rejection_corpus.jsonl
artifacts/candidates/stage2_6/replay_report.json
```

Stage 2.6 is a logging and replay gate for future candidate ASTs. It does not call an LLM, run evolution, generate candidates, execute operators, or evaluate objective functions.

## Run Stage 2.7 Sealed Split Replay Audit

```powershell
python -m pytest tests\stage2\test_stage2_7_sealed_split_replay_audit.py -q
```

This verifies:

```text
artifacts/candidates/stage2_7/sealed_split_manifest.json
artifacts/candidates/stage2_7/split_replay_audit_report.json
```

Stage 2.7 binds the Stage 2.6 accepted/rejected candidate logs and replay report to a sealed split manifest, checks their file fingerprints, and audits no-test-feedback boundaries. It does not call an LLM, run evolution, generate candidates, execute AST runtime, evaluate objectives, or implement an optimizer.

## Run Stage 2.8 Frozen Candidate Promotion

```powershell
python -m pytest tests\stage2\test_stage2_8_candidate_promotion.py -q
```

This verifies:

```text
artifacts/operators/stage2_8/stage2_6_corpus_valid_weighted_clip_shared_5.json
artifacts/operators/stage2_8/stage2_6_corpus_valid_weighted_clip_shared_5_promotion_receipt.json
artifacts/operators/stage2_8_registry.jsonl
```

Stage 2.8 promotes an already accepted Stage 2.6 candidate into a frozen operator artifact only after the Stage 2.7 sealed split replay audit passes. It does not call an LLM, run evolution, generate candidates, execute AST runtime, evaluate objectives, or implement an optimizer.

## Run Stage 2.9 Promotion Replay Audit

```powershell
python -m pytest tests\stage2\test_stage2_9_promotion_replay_audit.py -q
```

This verifies:

```text
artifacts/operators/stage2_8_registry.jsonl
artifacts/operators/stage2_9/promotion_replay_audit_report.json
```

Stage 2.9 cold-start replays the Stage 2.8 promoted artifact registry, loads the promoted artifact and promotion receipt, recomputes fingerprints, and audits Stage 2.6 / Stage 2.7 provenance. It does not call an LLM, run evolution, generate candidates, re-promote candidates, execute AST runtime, evaluate objectives, or implement an optimizer.

## Run Stage 2.1 Multi-setting Panel

```powershell
python loco\experiments\stage2_panel_runner.py
```

This writes:

```text
docs/stage2/stage2_1_synthetic_panel_result.json
docs/stage2/stage2_1_synthetic_panel_summary.csv
docs/stage2/stage2_1_self_check_report.md
```

The default panel covers `line / ring / random_graph`, dimensions `100 / 500 / 1000`, overlap ratios `0.0 / 0.05 / 0.10 / 0.20 / 0.30`, and seeds `0 / 1 / 2`. It is an evidence gate for conflict-state behavior and metric sanity. It does not implement an optimizer, LLM search, evolution, or new coordination operators.

## Run Stage 2.1B Multi-round Evidence

```powershell
python loco\experiments\stage2_multiround_runner.py
```

This writes:

```text
docs/stage2/stage2_1b_multiround_result.json
docs/stage2/stage2_1b_multiround_summary.csv
docs/stage2/stage2_1b_self_check_report.md
```

Stage 2.1B runs five deterministic rounds per baseline-method run. At each round it generates group proposals, measures conflict, applies one baseline coordination rule, commits the coordinated shared-variable values, regenerates next-round proposals from that committed solution, and measures regenerated conflict. The CSV is the main reading surface; the JSON is an audit artifact with per-round FE and shared-variable change logs.

## Benchmark And License Boundary

LOCO-LSGO reuses external benchmark implementations through dependencies/adapters.

- MetaBox / `metaevobox`: used as an optional dependency for CEC2013 LSGO access.
- CEC2013 LSGO objective implementations: not copied into this repository and not rewritten here.
- Synthetic overlap benchmarks: LOCO-controlled supplements for topology, overlap ratio, and dimension generalization.

See [LICENSE_NOTICE.md](LICENSE_NOTICE.md) and [docs/reproducibility.md](docs/reproducibility.md) for license and reproduction notes.

## Metric Honesty Note

Stage 2.0/2.1 report `proposal_consensus_collapse_ratio`, not a true longitudinal conflict reduction claim.

This value measures how much the current set of proposals collapses after applying a coordination rule. It does **not** prove that future regenerated conflicts are reduced. Stage 2.1 reports `post_coordination_regenerated_conflict` as a deterministic regenerated-conflict proxy. Stage 2.1B reports `longitudinal_conflict_reduction_ratio` using next-round regenerated conflict, not same-round collapse. These are evidence-gate diagnostics, not SOTA optimizer-loop performance claims.

## FE Accounting

The project keeps this accounting identity:

```text
FE_total = FE_grouping + FE_proposal + FE_coordination_extra + FE_repair
```

Stage 2.x evaluates each baseline or frozen artifact-backed operator as a separate method run. Cross-baseline comparison evaluations are not shared across methods.

## Next Recommended Stage

Do not jump directly to Stage 3. Recommended next step:

```text
Stage 2.10: pre-Stage-3 readiness gate
```
