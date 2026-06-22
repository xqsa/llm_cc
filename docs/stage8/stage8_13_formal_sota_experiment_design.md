# Stage 8.13 Formal CEC2013 SOTA Experiment Design And Budget Lock

创建日期：2026-06-22
执行者：Codex
阶段边界：Stage 8.13 只锁定正式 CEC2013 same-budget SOTA-facing experiment design。它不运行 CEC2013，不执行 objective loop，不调用 LLM，不生成新 candidate，不修改 selected operator，不使用 validation/test feedback，不修改 BaseOpt，也不声称 final objective-value performance improvement 或 SOTA。

## 1. Goal

Stage 8.13 回答：

```text
Stage 8.12 已确认 regime_safe_adaptive_shrinkage_v1 值得进入正式 SOTA-facing 实验。

那么正式 CEC2013 实验到底怎么跑、跑哪些函数、预算是多少、
怎么比较、怎么统计、什么条件下才允许 claim？
```

## 2. Formal CEC2013 Contract

Stage 8.13 locks:

```text
benchmark_suite = CEC2013_LSGO
dimension = 1000
function_ids = F1..F15
overlap_focus_function_ids = F13, F14
run_count = 25
MaxFEs = 3000000
checkpoints = 120000, 600000, 3000000
statistics = best, median, worst, mean, std
primary_ranking_statistic = median_at_3000000_fe
total_planned_official_runs = 375
total_planned_max_fe = 1125000000
```

F13/F14 are important because they are the overlap-focused functions, but F13/F14-only evidence is not a full CEC2013 SOTA claim.

## 3. Comparator Contract

Stage 8.13 preserves the Stage 7.5/7.6 comparator boundary:

```text
direct_comparator_sources = HCC
background_only_sources = OEDG
same_setting_required_for_direct_comparison = true
reported_results_use_policy = audit_only_not_runtime_feedback
```

Reported paper values may be used for audit/comparison tables only. They cannot be used to tune the policy, revise the selected operator, design prompts, select candidates, or make runtime decisions.

## 4. Statistical Plan

The formal run should report:

```text
per-function best / median / worst / mean / std
checkpoint tables at 120000, 600000, 3000000 FE
primary ranking by median_at_3000000_fe
win/tie/loss versus each admissible comparator
median relative gap
Wilcoxon signed-rank test on per-function final values
Holm-Bonferroni correction for multiple comparisons
failure-honest reporting if the policy loses or only wins narrow subsets
```

## 5. Claim Gate

Stage 8.13 locks the claim ladder:

```text
T1 = overlap-focused F13/F14 evidence after F13/F14 runs
T2 = named same-budget subset claim after subset runs
T3 = full CEC2013 LSGO SOTA-facing claim only after F1..F15 same-budget runs
```

Current claim state:

```text
full_sota_claim_allowed_now = false
official_benchmark_claim_ready = false
blocked_claim_reason = formal official CEC2013 same-budget panel not executed yet
```

## 6. Outputs

Stage 8.13 writes:

```text
artifacts/objective_eval/stage8_13/formal_sota_experiment_design.json
artifacts/objective_eval/stage8_13/budget_lock.json
artifacts/objective_eval/stage8_13/function_scope_lock.json
artifacts/objective_eval/stage8_13/comparator_admissibility_lock.json
artifacts/objective_eval/stage8_13/statistical_reporting_plan.json
artifacts/objective_eval/stage8_13/claim_gate.json
artifacts/objective_eval/stage8_13/fe_ledger.json
artifacts/objective_eval/stage8_13/runtime_boundary.json
artifacts/objective_eval/stage8_13/next_route_decision.json
```

## 7. Boundary

Stage 8.13 preserves:

```text
FE_total = 0
objective_loop_executed = false
new_objective_evaluation_used = false
official_cec2013_panel_run = false
llm_call_used = false
new_candidate_generation_used = false
selected_operator_revision_used = false
validation_feedback_used = false
test_feedback_used = false
reported_results_used_as_runtime_feedback = false
baseopt_modified = false
not a final objective-value performance claim
not a SOTA claim
```

## 8. Next Step

Recommended next stage:

```text
Stage 8.14 execute formal CEC2013 same-budget panel
```

大白话：Stage 8.13 是“开跑前把实验合同写死”。它不是结果，不是 SOTA，也不是 official benchmark success。真正的压力测试从 Stage 8.14 才开始。
