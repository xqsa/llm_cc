# Stage 6.1 Baseline Comparison, Ablation, and Failure Analysis

创建日期：2026-06-21
执行者：Codex
阶段边界：Stage 6.1 只读取 Stage 6.0 sealed-test reporting artifacts，生成 baseline comparison、ablation summary、failure analysis 和 claim boundary。它不调用 LLM、不生成新候选、不修改 prompt / train search / promotion rule / validation rule、不做 no test-feedback tuning、不做 objective evaluation、不修改 BaseOpt，也不是 not a SOTA claim 或 objective-value performance claim。

## 1. Goal

Stage 6.1 的目标是把 Stage 6.0 的最小 sealed-test diagnostics panel 整理成更接近论文结果分析的证据层：

```text
identity_no_coord
simple_consensus
weighted_consensus
selected_loco_operator
```

本阶段比较的是 shared-variable coordination diagnostics。主要指标是：

```text
normalized_distance_to_best_reward_proposal
```

它表示 coordination result 与当前 proposal set 中 best-reward proposal 的归一化距离。该指标是 sealed-test coordination diagnostic，不是 benchmark objective value。

## 2. Legal Inputs

Stage 6.1 只允许读取：

```text
artifacts/sealed_test/stage6_0/sealed_test_trace.jsonl
artifacts/sealed_test/stage6_0/sealed_test_metrics.json
artifacts/sealed_test/stage6_0/fe_ledger.json
artifacts/sealed_test/stage6_0/final_reporting_boundary.json
artifacts/sealed_test/stage6_0/sealed_test_report.json
```

它不得读取 Stage 3/4/5 candidate pool 来重新选择候选，也不得根据 sealed-test 结果回改 prompt、candidate generation、train search、promotion rule 或 validation rule。

## 3. Analysis Surface

Stage 6.1 产出四类分析：

```text
baseline_comparison_table
ablation_summary
failure_analysis
claim_boundary
```

`baseline_comparison_table` 汇总每个 method 的 mean distance、mean update size、FE_total 和按 distance 排序的 rank。

`ablation_summary` 记录 selected LOCO operator 相对三个 baseline 的 pairwise deltas。

`failure_analysis` 逐 case 标出 winner method、selected method 的 distance/update size，以及 cautionary failure modes。

`claim_boundary` 固化允许说什么、禁止说什么，以及后续允许路线。

## 4. Current Diagnostic Reading

在当前 Stage 6.0 sealed-test panel 上，selected LOCO operator 对三个 sealed conflict cases 的 `normalized_distance_to_best_reward_proposal` 均低于固定 baselines。与此同时，它的 `normalized_update_size` 也更大。

这支持一个很窄的 coordination-level 观察：

```text
selected_loco_operator moved closer to the current best-reward proposal
on this sealed diagnostic panel.
```

但它不支持以下 claim：

```text
objective-value improvement
SOTA improvement
optimizer superiority
general benchmark performance gain
```

## 5. Outputs

Stage 6.1 产物：

```text
artifacts/sealed_test/stage6_1/baseline_comparison_table.json
artifacts/sealed_test/stage6_1/ablation_summary.json
artifacts/sealed_test/stage6_1/failure_analysis.json
artifacts/sealed_test/stage6_1/claim_boundary.json
artifacts/sealed_test/stage6_1/analysis_report.json
```

## 6. Boundary Flags

Stage 6.1 preserves:

```text
llm_call_used = false
new_candidate_generation_used = false
prompt_revision_used = false
train_search_revision_used = false
promotion_rule_revision_used = false
validation_rule_revision_used = false
test_feedback_tuning_used = false
objective_evaluation_used = false
baseopt_modified = false
optimizer_generation_used = false
controller_scheduler_generation_used = false
not_sota_claim = true
not_performance_claim = true
```

## 7. Next Step

Stage 6.1 之后有两条合理路线：

```text
paper_claim_polish_from_diagnostics
stage7_objective_value_eval_with_new_protocol_and_fe_accounting
```

如果继续写小论文，可以先把 Stage 6.1 的 evidence 转成 method/result/threats-to-validity。若要做更强 claim，则 Stage 7 必须重新锁定 objective-value evaluation protocol，并完整计数 FE。
