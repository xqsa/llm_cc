# LOCO-LSGO

LLM-Evolved Coordination Operators for Overlapping Large-Scale Global Optimization.

LOCO-LSGO studies a deliberately narrow problem in overlapping LSGO:

```text
shared-variable conflict -> coordination operator -> more stable cooperative coevolution
```

The project does **not** use LLMs to generate a new optimizer. It does not generate DE, CMA-ES, PSO, SHADE, schedulers, controllers, optimizer selectors, or benchmark objectives. The intended Stage 3 role of LLM + evolution is only to discover reusable **coordination operator ASTs** that act on shared variables in overlapping subcomponents.

## Current Status

Current repository state: pre-Stage-3 readiness gate passed at the Stage 2 boundary.

- Stage 0 locked the research problem, mathematical contract, allowed/forbidden behavior, and acceptance boundary.
- Stage 1 built the benchmark/data layer, including the `LSGOProblem` interface, MetaBox lazy adapter, synthetic overlap generator, split manifests, and CEC2013 LSGO semantics correction.
- Stage 2 built the conflict-coordination infrastructure and readiness gates needed before any LLM/evolution search is allowed.

The Stage 2 readiness artifact currently records:

```text
decision = READY_FOR_STAGE3_BOUNDARY_ONLY
stage3_allowed = true
not_performance_claim = true
```

This means Stage 3 may begin only as boundary-constrained typed coordination-operator AST search. It is **not** a claim that LOCO has learned final operators, beaten baselines, or achieved SOTA optimizer performance.

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
loco/benchmarks/      LSGOProblem interface, MetaBox adapter, synthetic overlap generator
loco/conflict/        Shared-variable conflict state and metrics
loco/coordination/    Baseline coordination rules, typed AST boundary, artifact helpers
loco/evaluation/      FE accounting
loco/experiments/     Stage 2 diagnostic runners
scripts/stage1/       Real MetaBox CEC2013 LSGO smoke script
tests/                Stage 0/1/2 tests
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

Expected latest local Stage 2 boundary result:

```text
126 passed
```

Run the Stage 2 readiness gate directly:

```powershell
python -m pytest tests\stage2\test_stage2_10_readiness_gate.py -q
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
Stage 3.0: protocol lock for boundary-constrained typed-AST LLM/evolution search
```
