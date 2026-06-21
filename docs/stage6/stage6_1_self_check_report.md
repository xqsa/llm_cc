# Stage 6.1 Self-check Report

创建日期：2026-06-21
执行者：Codex

## Result

```text
status = PASS
stage = 6.1
source_stage = 6.0
selected_candidate_id = stage3_5_batch_1_weighted_consensus_projection
analysis_scope = sealed-test baseline diagnostics only
method_count = 4
baseline_method_count = 3
selected_method_name = selected_loco_operator
sealed_state_count = 3
trace_row_count = 12
next_status = READY_FOR_PAPER_CLAIM_POLISH_OR_STAGE7_OBJECTIVE_EVAL
```

## Artifact Check

```text
configs/stage6_1_baseline_ablation_analysis.yaml
docs/stage6/stage6_1_baseline_ablation_analysis.md
docs/stage6/stage6_1_self_check_report.md
artifacts/sealed_test/stage6_1/baseline_comparison_table.json
artifacts/sealed_test/stage6_1/ablation_summary.json
artifacts/sealed_test/stage6_1/failure_analysis.json
artifacts/sealed_test/stage6_1/claim_boundary.json
artifacts/sealed_test/stage6_1/analysis_report.json
loco/coordination/baseline_ablation_analysis.py
scripts/stage6/run_stage6_1_baseline_ablation_analysis.py
tests/stage6/test_stage6_1_baseline_ablation_analysis.py
```

## Method Set

```text
identity_no_coord
simple_consensus
weighted_consensus
selected_loco_operator
```

## Diagnostic Summary

Stage 6.1 compares selected LOCO operator against three fixed baselines using Stage 6.0 sealed-test records only.

The primary coordination diagnostic is:

```text
normalized_distance_to_best_reward_proposal
```

Lower values mean the coordinated value is closer to the current best-reward proposal in the same sealed conflict case. This is a coordination diagnostic, not an objective-value performance metric.

The cautionary diagnostic is:

```text
normalized_update_size
```

Selected LOCO currently uses larger updates than the fixed baselines on the sealed diagnostic panel. This is recorded as a failure-analysis caution, not as an optimizer failure claim.

## Boundary Check

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
full FE accounting inherited from Stage 6.0
not a SOTA claim
not an objective-value performance claim
```

## Validation Commands

Fresh validation should include:

```powershell
python -m pytest tests\stage6\test_stage6_1_baseline_ablation_analysis.py -q
python -m pytest tests\stage4\test_coordination_family_space.py tests\stage5 tests\stage6 -q
python -m black --check loco tests scripts
python -m pytest -p no:cacheprovider tests -q -rs
```
