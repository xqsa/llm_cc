# Reproducibility Notes

生成日期：2026-06-19
执行者：Codex

## Environment

Recommended:

```text
Python >= 3.10
numpy >= 1.24
pytest >= 8.0
black >= 24.0
```

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
45 passed, 1 skipped
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
