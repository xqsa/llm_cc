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
53 passed, 1 skipped
```

The skipped test is allowed only when a real MetaBox smoke test is unavailable or not a complete PASS, and it must print a clear reason.

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

F14 real conflicting-overlap smoke can be checked through:

```powershell
python -c "from loco.experiments.stage2_minimal_runner import run_optional_f14_smoke; import json; print(json.dumps(run_optional_f14_smoke(seed=3), indent=2, sort_keys=True))"
```

F13 remains a known compatibility blocker in the current environment because the official formula dimension is `D_formula=905`, while the MetaBox numpy implementation may internally read an `Ovector(1000)`.

Do not pad F13/F14 to fake a pass unless a future wrapper compatibility adapter is explicitly labeled as `implementation_api_adapter` and justified separately.
