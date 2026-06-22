# Stage 8.14 CEC2013 Single-Run Smoke And Route Decision

创建日期：2026-06-22
执行者：Codex

## 1. Boundary

阶段边界：Stage 8.14 只做 CEC2013 overlap-focused single-run smoke。它不是 full 25-run panel，不是 full F1..F15 panel，不是 final objective-value performance claim，也不是 SOTA claim。

本阶段的目的很直接：

```text
先跑一次，看方法在真实 CEC2013 F13/F14 路线上是否值得继续烧 25-run 成本。
```

如果 single-run promising，再进入 full 25-run formal panel。如果 single-run 不 promising，先做 failure-honest diagnosis，不直接跑 25 次。

## 2. Smoke Contract

```text
benchmark_suite = CEC2013_LSGO
function_ids = F13, F14
run_count = 1
seed = 0
smoke_max_fe_per_method_per_function = 1200
method_count = 5
methods =
  identity_no_coord
  simple_consensus
  weighted_consensus
  best_reward_select
  stage8_11_generalized_policy
policy_name = regime_safe_adaptive_shrinkage_v1
```

Stage 8.13 的 full formal contract 仍然保留：

```text
full_formal_run_count = 25
full_formal_function_count = 15
full_formal_MaxFEs = 3000000
```

但 Stage 8.14 明确记录：

```text
not_full_25_run_panel = true
not_full_f1_f15_panel = true
full_official_budget_deferred = true
```

## 3. Result

Stage 8.14 已执行真实 MetaBox-backed CEC2013 F13/F14 smoke。

```text
status = PASS
single_run_smoke_executed = true
official_cec2013_problem_loaded = true
objective_loop_executed = true
new_objective_evaluation_used = true
trace_row_count = 12000
FE_global_objective = 12010
FE_total = 24010
```

Win/loss against the best baseline:

```text
policy_vs_best_baseline = 0 win / 0 tie / 2 loss
single_run_promising = false
```

Per-function smoke result:

```text
F13:
  best_baseline_method = best_reward_select
  best_baseline_final_best = 8.714428967708853e+16
  policy_final_best = 8.716559195496776e+16
  policy_vs_best_baseline_delta = 21302277879232.0
  result = loss

F14:
  best_baseline_method = best_reward_select
  best_baseline_final_best = 5.074322565106659e+18
  policy_final_best = 5.074322808381155e+18
  policy_vs_best_baseline_delta = 243274496000.0
  result = loss
```

## 4. Route Decision

Stage 8.14 route:

```text
decision = NOT_PROMISING_SINGLE_RUN_DIAGNOSE_BEFORE_25_RUN_PANEL
recommended_next_stage = Stage 8.15
recommended_next_work = failure_honest_cec2013_smoke_diagnosis
run_full_25_run_panel_next = false
run_failure_diagnosis_next = true
```

大白话：这次单次 smoke 没有给出“值得马上跑 25 次”的信号。当前最合理动作不是硬跑 full panel，而是先查为什么 generalized policy 在 F13/F14 上输给 `best_reward_select`。

## 5. Artifacts

```text
configs/stage8_14_cec2013_single_run_smoke_decision.yaml
docs/stage8/stage8_14_cec2013_single_run_smoke_decision.md
docs/stage8/stage8_14_self_check_report.md
loco/coordination/cec2013_single_run_smoke_decision.py
scripts/stage8/run_stage8_14_cec2013_single_run_smoke_decision.py
tests/stage8/test_stage8_14_cec2013_single_run_smoke_decision.py
artifacts/objective_eval/stage8_14/objective_trace.jsonl
artifacts/objective_eval/stage8_14/method_summary.json
artifacts/objective_eval/stage8_14/win_loss_report.json
artifacts/objective_eval/stage8_14/fe_ledger.json
artifacts/objective_eval/stage8_14/runtime_boundary.json
artifacts/objective_eval/stage8_14/next_route_decision.json
artifacts/objective_eval/stage8_14/single_run_smoke_report.json
```

## 6. Forbidden Scope

```text
llm_call_used = false
new_candidate_generation_used = false
selected_operator_revision_used = false
evolution_search_used = false
validation_feedback_used = false
test_feedback_used = false
reported_results_used_as_runtime_feedback = false
baseopt_modified = false
optimizer_generation_used = false
controller_scheduler_generation_used = false
not_sota_claim = true
not_final_performance_claim = true
```

Stage 8.14 does not support:

```text
SOTA improvement
official full CEC2013 benchmark success
final objective-value performance improvement
full 25-run statistical claim
full F1..F15 claim
```
