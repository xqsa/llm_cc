# Stage 8.35 Self-Check Report

Date: 2026-06-23
Executor: Codex

## Checks

```text
failure_honest_bounded_guarded_checkpoint_diagnosis = true
stage8_34_less_loss_case_count = 1
stage8_34_comparison_case_count = 6
stage8_34_less_loss_rate = 0.16666666666666666
less_loss_case_explained = true
remaining_loss_cases_explained = true
limited_guard_applicability = true
formal_25_run_recommended_now = false
```

## FE Boundary

```text
FE_total = 0
objective_loop_executed = false
new_objective_evaluation_used = false
cec_checkpoint_executed = false
formal_25_run_panel_executed = false
```

## Claim Boundary

Stage 8.35 is not a final objective-value performance claim and not a SOTA
claim. It is a diagnosis explaining why Stage 8.34 is not strong enough for a
formal 25-run panel.

## Files

```text
configs/stage8_35_bounded_guarded_checkpoint_diagnosis.yaml
loco/coordination/bounded_guarded_checkpoint_diagnosis.py
scripts/stage8/run_stage8_35_bounded_guarded_checkpoint_diagnosis.py
artifacts/analysis/stage8_35/bounded_guarded_checkpoint_diagnosis_report.json
artifacts/analysis/stage8_35/one_of_six_less_loss_cause_report.json
artifacts/analysis/stage8_35/case_diagnosis_table.jsonl
artifacts/analysis/stage8_35/guard_branch_diagnosis.json
artifacts/analysis/stage8_35/fe_ledger.json
artifacts/analysis/stage8_35/runtime_boundary.json
artifacts/analysis/stage8_35/next_route_decision.json
```
