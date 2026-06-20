# Reproducibility Notes

生成日期：2026-06-19
执行者：Codex

## Environment

Recommended:

```text
Python >= 3.10
numpy >= 1.24
pytest >= 8.0
black == 24.8.0
```

`black` is pinned because formatter output can drift across releases. Local checks and GitHub Actions must use the same formatter version before the repository can claim CI-level reproducibility.

Install:

```powershell
python -m pip install -r requirements.txt
```

## Tests

Run:

```powershell
python -m pytest -p no:cacheprovider tests -q -rs
```

Current expected local result:

```text
tests pass; optional real MetaBox tests pass only when metaevobox is installed
```

The optional real MetaBox tests are allowed to skip only when a real MetaBox smoke test is unavailable or not a complete PASS, and they must print a clear reason.

## Stage 2.0 Runner

Run:

```powershell
python loco\experiments\stage2_minimal_runner.py
```

Output:

```text
docs/stage2/stage2_0_synthetic_result.json
```

The result is deterministic for the same seed.

## Stage 2.1 Multi-setting Panel

Run:

```powershell
python loco\experiments\stage2_panel_runner.py
```

Outputs:

```text
docs/stage2/stage2_1_synthetic_panel_result.json
docs/stage2/stage2_1_synthetic_panel_summary.csv
docs/stage2/stage2_1_self_check_report.md
```

The default panel runs 45 synthetic settings and 135 seeded runs:

```text
topology in {line, ring, random_graph}
dimension in {100, 500, 1000}
overlap_ratio in {0.0, 0.05, 0.10, 0.20, 0.30}
seed in {0, 1, 2}
```

Stage 2.1 remains benchmark/evidence infrastructure. It does not call an LLM, run evolution, implement an optimizer, or generate new coordination operators.

## Stage 2.1B Multi-round Evidence

Run:

```powershell
python loco\experiments\stage2_multiround_runner.py
```

Outputs:

```text
docs/stage2/stage2_1b_multiround_result.json
docs/stage2/stage2_1b_multiround_summary.csv
docs/stage2/stage2_1b_self_check_report.md
```

The default Stage 2.1B panel runs 36 synthetic settings, 540 independent baseline-method runs, and 5 rounds per run:

```text
topology in {line, ring, random_graph}
dimension in {100, 500, 1000}
overlap_ratio in {0.05, 0.10, 0.20, 0.30}
seed in {0, 1, 2}
baseline in {NoCoordination, AverageConsensus, BestRewardSelection, WeightedConsensus, ConflictDampening}
```

`longitudinal_conflict_reduction_ratio` uses next-round regenerated conflict. It must not be substituted with same-round `proposal_consensus_collapse_ratio_mean`, and it is not a SOTA optimizer-loop performance claim.

## Stage 2.2 DSL Boundary And Stage 3 Preflight

Stage 2.2 is verified through the DSL boundary tests:

```powershell
python -m pytest tests\stage2\test_stage2_2_dsl_boundary.py -q
```

The tested surface includes:

- typed coordination operator AST loading;
- shared-variable-only target validation;
- forbidden optimizer/controller/scheduler node rejection;
- forbidden metadata rejection;
- arbitrary executable code rejection;
- deterministic AST serialization;
- Stage 3 preflight accepted/rejected candidate reports;
- deterministic accepted-candidate `fingerprint_sha256`;
- zero additional function evaluations during validation.

Stage 2.2 does not execute ASTs, call an LLM, run evolution, implement an optimizer, or claim learned operators.

## Stage 2.3 DSL Runtime Shell

Stage 2.3 is verified through the frozen-AST runtime tests:

```powershell
python -m pytest tests\stage2\test_stage2_3_dsl_runtime.py -q
```

The tested surface includes:

- `FrozenASTRuntime`;
- interpretation of a frozen typed AST into `CoordinationResult`;
- shared-variable target matching against `SharedVariableConflictState`;
- deterministic runtime trace diagnostics;
- zero additional function evaluations during runtime interpretation;
- no LLM/evolution module imports.

Stage 2.3 does not call objective functions, generate ASTs, call an LLM, run evolution, implement an optimizer, or claim learned operators.

## Stage 2.4 Frozen AST Smoke Integration

Stage 2.4 can be verified with:

```powershell
python -m pytest tests\stage2\test_stage2_4_frozen_ast_runner.py -q
python loco\experiments\stage2_minimal_runner.py
```

The runner writes:

```text
docs/stage2/stage2_4_frozen_ast_smoke_result.json
```

The tested and logged surface includes:

- existing synthetic conflict runner integration;
- handwritten `FrozenASTSmoke` method run;
- deterministic frozen AST template fingerprint;
- per-shared-variable DSLRuntime trace diagnostics;
- `FE_coordination_extra = 0`;
- per-method budget accounting;
- no LLM / no evolution imports.

Stage 2.4 is a smoke integration gate. It does not claim learned operators, LLM-generated operator success, evolution search success, optimizer improvement, or SOTA results.

## Stage 2.5 Frozen AST Artifact Registry

Stage 2.5 can be verified with:

```powershell
python -m pytest tests\stage2\test_stage2_5_artifact_registry.py -q
python loco\experiments\stage2_minimal_runner.py
```

The runner writes:

```text
docs/stage2/stage2_5_artifact_registry_result.json
```

The tested and logged surface includes:

- `artifacts/operators/stage2_5_registry.jsonl`;
- frozen operator artifact loading;
- deterministic artifact fingerprinting;
- artifact mutation changing the fingerprint;
- rejection of unfrozen artifacts;
- rejection of artifacts with test feedback enabled;
- shared-variable-only target scope;
- `FrozenASTSmoke` provenance emitted through `frozen_ast_runtime`;
- `FE_coordination_extra = 0`;
- no LLM / no evolution imports.

Stage 2.5 is an artifact provenance and split-boundary hardening gate. It does not claim learned operators, LLM-generated operator success, evolution search success, optimizer improvement, or SOTA results.

## Stage 2.6 Candidate Artifact Logging

Stage 2.6 can be verified with:

```powershell
python -m pytest tests\stage2\test_stage2_6_candidate_logging.py -q
```

The committed artifacts are:

```text
artifacts/candidates/stage2_6/rejection_corpus.jsonl
artifacts/candidates/stage2_6/accepted_candidates.jsonl
artifacts/candidates/stage2_6/rejected_candidates.jsonl
artifacts/candidates/stage2_6/replay_report.json
```

The tested and logged surface includes:

- candidate artifact logging schema `loco.candidate_log.v1`;
- accepted candidate deterministic `ast_fingerprint_sha256`;
- rejected candidate `reject_reason_category`;
- replay verifier for accepted/rejected decisions;
- tamper detection through fingerprint mismatch;
- rejection corpus coverage for non-shared target, optimizer/controller node, executable code, forbidden metadata, and invalid schema;
- no LLM / no evolution imports;
- no test feedback boundary.

Stage 2.6 is a candidate artifact logging schema and replay verifier gate. It does not call an LLM, run evolution, generate candidates, execute AST runtime, implement an optimizer, or claim learned operators.

## Stage 2.7 Sealed Split Replay Audit

Stage 2.7 can be verified with:

```powershell
python -m pytest tests\stage2\test_stage2_7_sealed_split_replay_audit.py -q
```

The committed artifacts are:

```text
artifacts/candidates/stage2_7/sealed_split_manifest.json
artifacts/candidates/stage2_7/split_replay_audit_report.json
```

The tested and logged surface includes:

- sealed split manifest schema `loco.sealed_split_manifest.v1`;
- sha256 binding for Stage 2.6 accepted/rejected candidate logs and replay report;
- replay report status audit;
- candidate log split restriction to `pre_stage3_schema_only`;
- explicit rejection of `test` split rows;
- no-test-feedback audit for candidate log rows;
- no LLM / no evolution boundary flags;
- tamper detection for file fingerprint, split, and test-feedback violations.

Stage 2.7 is a sealed split replay audit gate. It does not call an LLM, run evolution, generate candidates, execute AST runtime, call objective functions, implement an optimizer, or claim learned operators.

## Stage 2.8 Frozen Candidate Promotion Contract

Stage 2.8 can be verified with:

```powershell
python -m pytest tests\stage2\test_stage2_8_candidate_promotion.py -q
```

The committed artifacts are:

```text
artifacts/operators/stage2_8/stage2_6_corpus_valid_weighted_clip_shared_5.json
artifacts/operators/stage2_8/stage2_6_corpus_valid_weighted_clip_shared_5_promotion_receipt.json
artifacts/operators/stage2_8_registry.jsonl
```

The tested and logged surface includes:

- accepted-only promotion from Stage 2.6 candidate logs;
- required Stage 2.7 sealed split replay audit `PASS`;
- frozen operator artifact schema `loco.operator_artifact.v1`;
- promotion receipt schema `loco.candidate_promotion_receipt.v1`;
- promoted operator registry schema `loco.promoted_operator_registry.v1`;
- source candidate log fingerprint binding;
- sealed manifest and audit report fingerprint binding;
- artifact and promotion fingerprint generation;
- rejection of rejected candidates;
- rejection of failed/tampered audit reports;
- no LLM / no evolution imports;
- no candidate generation, no runtime AST execution, no objective evaluation, and no test feedback boundary.

Stage 2.8 is a frozen candidate promotion contract gate. It does not call an LLM, run evolution, generate candidates, execute AST runtime, call objective functions, implement an optimizer, or claim learned operators.

## Stage 2.9 Promotion Replay and Registry Audit

Stage 2.9 can be verified with:

```powershell
python -m pytest tests\stage2\test_stage2_9_promotion_replay_audit.py -q
```

The committed artifacts are:

```text
artifacts/operators/stage2_8_registry.jsonl
artifacts/operators/stage2_9/promotion_replay_audit_report.json
```

The tested and logged surface includes:

- cold-start replay of Stage 2.8 promoted registry rows;
- promoted artifact loading through `loco.operator_artifact.v1`;
- promotion receipt loading through `loco.candidate_promotion_receipt.v1`;
- artifact fingerprint recomputation;
- promotion receipt fingerprint recomputation against the registry;
- promotion fingerprint recomputation from artifact and receipt provenance;
- Stage 2.6 accepted candidate log fingerprint audit;
- Stage 2.7 sealed manifest and audit report fingerprint audit;
- artifact tamper detection;
- receipt tamper detection;
- no LLM / no evolution imports;
- no candidate generation, no candidate promotion, no runtime AST execution, no objective evaluation, and no test feedback boundary.

Stage 2.9 is a promotion replay and registry audit gate. It does not call an LLM, run evolution, generate candidates, re-promote candidates, execute AST runtime, call objective functions, implement an optimizer, or claim learned operators.

## FE Accounting

All function evaluations must be assigned to:

```text
FE_total = FE_grouping + FE_proposal + FE_coordination_extra + FE_repair
```

Stage 2.0 evaluates each baseline as a separate method run. Cross-baseline comparison evaluations are not shared across methods.

Current Stage 2.0 synthetic runner uses:

```text
FE_grouping = 0
FE_proposal = 10
FE_coordination_extra = 0
FE_repair = 0
FE_total = 10
```

where `FE_proposal=10` means:

```text
1 initial solution evaluation
8 group proposal evaluations
1 coordinated solution evaluation
```

## Real MetaBox Smoke

F12/F13/F14 real MetaBox smoke can be checked through:

```powershell
python scripts\stage1\check_metabox_cec2013lsgo_real.py --json-output docs\stage1\metabox_real_smoke_latest.json --seed 11
```

Current local benchmark-only environment uses `metaevobox==2.0.2` and the LOCO lazy import adapter. In that environment:

- F13 preserves official overlap semantics as `D_formula=905`, but evaluates through `runtime_dimension=1000` with `adapter_mode=implementation_api_adapter` because MetaBox F13 internally exposes 1000-length `Ovector`, `Pvector`, and `s` construction data.
- F13 grouping, shared-variable count, and overlap ratio remain reported against `D_formula=905`: 20 groups, overlap size 5, 95 shared variables, and `95/905`.
- F14 remains the direct `D_formula=905` real conflicting-overlap smoke case.
- The top-level `metaevobox` import may still fail if trainer/agent dependencies such as `pettingzoo` are absent; LOCO uses a benchmark-only lazy import path for CEC2013LSGO.

Do not silently pad F13/F14 to fake a pass. Any wrapper compatibility must be explicitly labeled as `implementation_api_adapter`, must preserve `D_formula`, and must not rewrite or copy the CEC objective.
