# Stage 8.1 Train-only Selection Audit

创建日期：2026-06-21  
执行者：Codex  
阶段边界：Stage 8.1 只审计 Stage 8.0 的 improvement trace，并在 train-only 条件下加固 selection cutoff。它不调用 LLM，不生成新候选，不执行 AST，不做 objective evaluation，不跑 benchmark，不使用 validation/test feedback，也不把 reported results 变成 runtime feedback 或 performance claim。

## 1. Goal

Stage 8.0 已经给出 12 个 frozen candidates 的 deterministic improvement trace。Stage 8.1 的目标是做 train-only selection audit，重点检查：

本阶段直接读取的是 frozen Stage 8.0 improvement trace。

```text
trace ordering
tie handling
selection cutoff behavior
FE ledger identity
claim boundary
```

本阶段不进入 validation selection。它只决定哪些 improvement candidates 可以作为 selection-ready set 进入下一阶段。

## 2. Inputs

Stage 8.1 只读取 Stage 8.0 产物：

```text
artifacts/improvement/stage8_0/improvement_trace.jsonl
artifacts/improvement/stage8_0/improvement_candidates.json
```

## 3. Audit Finding

Stage 8.0 原始 selection rule 是：

```text
selection_top_k = 4
selection_metric = deterministic_train_only_improvement_score
```

审计发现：

```text
cutoff_rank = 4
cutoff_score = 0.775
tie_group_size_at_cutoff = 6
boundary_tie_detected = true
```

也就是说，原始 top-k 在第 4 名处截断了一个 6 个候选的同分组。若直接保留 top-4，会把 2 个同分候选静默丢弃。

这不是性能问题，而是 selection determinism / fairness / auditability 问题。

## 4. Hardened Rule

Stage 8.1 固化的 selection rule 是：

```text
include_all_candidates_tied_at_selection_cutoff
```

规则含义：

```text
If top-k cuts through an equal-score group, include every candidate tied at the cutoff score in the selection-ready set.
```

当前结果：

```text
original_top_k = 4
cutoff_score = 0.775
hardened_candidate_count = 6
```

这些 candidates 的状态是：

```text
TRAIN_ONLY_SELECTION_READY_NOT_FINAL
```

它们不是 final selected operators，也不是性能成功声明。

## 5. Outputs

Stage 8.1 产物：

```text
artifacts/selection_audit/stage8_1/selection_audit_report.json
artifacts/selection_audit/stage8_1/tie_audit.json
artifacts/selection_audit/stage8_1/hardened_selection_rule.json
artifacts/selection_audit/stage8_1/selection_decision.json
artifacts/selection_audit/stage8_1/fe_ledger.json
artifacts/selection_audit/stage8_1/next_route_decision.json
```

## 6. Current Result

```text
status = PASS
source_stage = 8.0
candidate_count = 12
original_selection_top_k = 4
top_score_tie_count = 6
boundary_tie_detected = true
selection_rule_hardened = true
hardened_selection_candidate_count = 6
next_status = READY_FOR_STAGE8_2_TRAIN_ONLY_BOUNDARY_LOCK
```

Boundary flags:

```text
validation_feedback_used = false
test_feedback_used = false
objective_evaluation_used = false
benchmark_execution_used = false
reported_results_used_as_runtime_feedback = false
not_performance_claim = true
```

## 7. FE Ledger Audit

Stage 8.1 preserved the Stage 8.0 FE ledger identity:

```text
FE_total = FE_grouping + FE_proposal + FE_coordination_extra + FE_repair
12 = 0 + 12 + 0 + 0
```

No cross-candidate evaluations were shared.

## 8. Next Step

The next stage can be:

```text
Stage 8.2: train-only boundary lock or audit
```

Stage 8.2 must not feed selection results back into Stage 8.0 trace generation, improvement scoring, comparator reuse, or future candidate generation.
