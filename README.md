# LOCO-LSGO

LLM-Evolved Coordination Operators for Overlapping Large-Scale Global Optimization.

LOCO-LSGO studies a narrow problem in overlapping LSGO:

```text
shared-variable conflict -> coordination operator -> more stable cooperative coevolution
```

The project does **not** use LLMs to generate a new optimizer. It does not generate DE, CMA-ES, PSO, SHADE, schedulers, controllers, or optimizer selectors. The intended Stage 3 role of LLM + evolution is only to discover reusable coordination operators that act on shared variables in overlapping subcomponents.

## Current Status

Current repository stage: `Stage 2.0 PASS`.

Implemented:

- Stage 0: research problem lock and system boundary definition.
- Stage 1: benchmark/data layer with MetaBox lazy adapter, synthetic overlap generator, manifest support, and CEC2013 LSGO semantics correction.
- Stage 2.0: conflict state, conflict metrics, baseline coordination operators, FE accounting, and a minimal synthetic conflict-coordination runner.

Known blocker:

- MetaBox F13 real evaluate remains a documented `D_formula=905` vs implementation/API `Ovector(1000)` compatibility blocker.
- F14 real conflicting-overlap smoke currently passes in the local environment, but remains optional in CI-style tests.

## Repository Layout

```text
configs/              Stage boundary and benchmark configuration drafts
docs/stage0/          Research boundary and mathematical contracts
docs/stage1/          Benchmark/data-layer reports and CEC2013 LSGO semantics
docs/stage2/          Stage 2.0 result JSON and self-check report
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
45 passed, 1 skipped
```

The skip is the optional Stage 1 real MetaBox smoke when F12/F13/F14 are not all complete PASS. It must give a clear reason and must not fake a real benchmark success.

## Run Stage 2.0 Minimal Runner

```powershell
python loco\experiments\stage2_minimal_runner.py
```

This writes:

```text
docs/stage2/stage2_0_synthetic_result.json
```

The runner uses a deterministic one-shot perturbation proposal generator. It is not an optimizer and should not be interpreted as performance evidence. Its purpose is to verify that shared-variable conflict states, baseline coordination operators, metrics, and FE accounting work end to end.

## Benchmark And License Boundary

LOCO-LSGO reuses external benchmark implementations through dependencies/adapters.

- MetaBox / `metaevobox`: used as an optional dependency for CEC2013 LSGO access.
- CEC2013 LSGO objective implementations: not copied into this repository and not rewritten here.
- Synthetic overlap benchmarks: LOCO-controlled supplements for topology, overlap ratio, and dimension generalization.

See [LICENSE_NOTICE.md](LICENSE_NOTICE.md) and [docs/reproducibility.md](docs/reproducibility.md) for license and reproduction notes.

## Metric Honesty Note

Stage 2.0 reports `proposal_consensus_collapse_ratio`, not a true longitudinal conflict reduction claim.

This value measures how much the current set of proposals collapses after applying a coordination rule. It does **not** prove that future regenerated conflicts are reduced. Stage 2.1 should add `post_coordination_regenerated_conflict` by generating proposals again after coordination or by running a next-step loop.

## FE Accounting

The project keeps this accounting identity:

```text
FE_total = FE_grouping + FE_proposal + FE_coordination_extra + FE_repair
```

Stage 2.0 evaluates each baseline as a separate method run. Cross-baseline comparison evaluations are not shared across methods.

## Next Recommended Stage

Do not jump directly to Stage 3. Recommended next step:

```text
Stage 2.1: multi-setting synthetic runner + stronger conflict metrics + logging schema + typed coordination operator DSL boundary
```
