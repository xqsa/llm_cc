# Stage 4.1 Train Search Audit and Promotion-rule Hardening

创建日期：2026-06-21
执行者：Codex
阶段边界：Stage 4.1 只审计 Stage 4.0 train-only search artifacts，并加固 promotion rule。它不使用 validation feedback、不使用 test feedback、不执行 AST、不做 objective evaluation、不调用 LLM、不生成新候选，也不是 not a performance claim。

## 1. Goal

Stage 4.0 已经对 Stage 3.6 frozen candidate pool 产生 train-only ranking 和 top-k promotion candidates。Stage 4.1 的目标是做 train search audit 和 promotion-rule hardening，尤其是：

```text
search trace ordering
tie handling
promotion cutoff behavior
family coverage
FE ledger identity
claim boundary
```

本阶段不进入 validation selection。它只决定哪些 candidates 可以作为 validation-ready set 进入下一阶段。

## 2. Inputs

Stage 4.1 只读取 Stage 4.0 产物：

```text
artifacts/search/stage4_0/search_trace.jsonl
artifacts/search/stage4_0/promotion_candidates.json
artifacts/search/stage4_0/fe_ledger.json
artifacts/search/stage4_0/search_report.json
```

## 3. Audit Finding

Stage 4.0 原始 promotion rule 是：

```text
promotion_top_k = 3
selection_metric = deterministic_train_proxy_score
```

审计发现：

```text
cutoff_rank = 3
cutoff_score = 1.0
tie_group_size_at_cutoff = 6
boundary_tie_detected = true
```

也就是说，原始 top-k 在第 3 名处截断了一个 6 个候选的同分组。若直接保留 top-3，会把 3 个同分候选静默丢弃：

```text
stage3_5_batch_1_weighted_consensus_projection
stage3_5_batch_2_projection_dampening
stage3_5_batch_2_reweighting_repair
```

这不是性能问题，而是 promotion-rule determinism / fairness / auditability 问题。

## 4. Hardened Rule

Stage 4.1 固化的 promotion rule 是：

```text
include_all_candidates_tied_at_cutoff
```

规则含义：

```text
If top-k cuts through an equal-score group, include every candidate tied at the cutoff score in the validation-ready set.
```

当前结果：

```text
original_top_k = 3
cutoff_score = 1.0
hardened_candidate_count = 6
```

这些 candidates 的状态是：

```text
VALIDATION_READY_TIE_HARDENED_NOT_FINAL
```

它们不是 final selected operators，也不是性能成功声明。

## 5. Outputs

Stage 4.1 产物：

```text
artifacts/search/stage4_1/train_search_audit_report.json
artifacts/search/stage4_1/tie_audit.json
artifacts/search/stage4_1/hardened_promotion_rule.json
artifacts/search/stage4_1/promotion_decision.json
```

## 6. Current Result

```text
status = PASS
source_stage = 4.0
candidate_count = 12
original_promotion_top_k = 3
top_score_tie_count = 6
boundary_tie_detected = true
promotion_rule_hardened = true
hardened_promotion_candidate_count = 6
next_status = READY_FOR_STAGE5_VALIDATION_SELECTION
```

Boundary flags:

```text
validation_feedback_used = false
test_feedback_used = false
objective_evaluation_used = false
ast_execution_used = false
not_performance_claim = true
```

## 7. FE Ledger Audit

Stage 4.1 preserved the Stage 4.0 FE ledger identity:

```text
FE_total = FE_grouping + FE_proposal + FE_coordination_extra + FE_repair
12 = 0 + 12 + 0 + 0
```

No cross-candidate evaluations were shared.

## 8. Next Step

The next stage can be:

```text
Stage 5.0: validation-only selection over tie-hardened validation-ready candidates
```

Stage 5.0 must not feed validation results back into Stage 4.0/4.1 search, prompt generation, frozen pool contents, or promotion-rule design.
