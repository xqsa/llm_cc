# Stage 4.0 Train-only Search over Frozen Coordination-candidate Pool

创建日期：2026-06-20
执行者：Codex
阶段边界：Stage 4.0 只在 Stage 3.6 frozen coordination-candidate pool 上运行 train-only search，并遵守 Stage 3.7 family lock。它不调用 LLM、不生成新候选、不使用 validation/test feedback、不执行 AST、不做 objective evaluation、不修改 BaseOpt，也不是 not a performance claim。

## 1. Goal

Stage 4.0 的目标是把 Stage 3.6 的冻结候选池接入一个可复现、可审计的 train-only search artifact 链：

```text
frozen_candidate_pool.jsonl
-> train-only search trace
-> promotion candidates
-> FE ledger
-> search report
```

本阶段只证明搜索链路、边界和证据账本成立。它不证明 selected operators 有真实优化性能，也不构成 validation 或 sealed test 结论。

## 2. Inputs

Stage 4.0 只读取：

```text
artifacts/candidates/stage3_6/frozen_candidate_pool.jsonl
configs/stage4_coordination_family_space.yaml
```

输入要求：

```text
candidate_pool_frozen = true
split = train
target_scope = shared_variables_only
family_lock_stage = 3.7
```

## 3. Outputs

当前 Stage 4.0 产物：

```text
artifacts/search/stage4_0/search_trace.jsonl
artifacts/search/stage4_0/promotion_candidates.json
artifacts/search/stage4_0/fe_ledger.json
artifacts/search/stage4_0/search_report.json
```

`search_trace.jsonl` 为 12 个 frozen candidates 生成 deterministic train proxy score 和 rank。

`promotion_candidates.json` 只标记 top-k candidates 为：

```text
VALIDATION_READY_NOT_SELECTED_FINAL
```

这表示它们可以进入后续 validation selection gate，但不是 final selected operator。

## 4. Current Result

当前结果：

```text
status = PASS
candidate_count = 12
promotion_candidate_count = 3
allowed_split = train
family_lock_stage = 3.7
train_only_search_executed = true
next_status = READY_FOR_STAGE4_1_TRAIN_SEARCH_AUDIT
```

边界 flags：

```text
llm_call_used = false
new_candidate_generation_used = false
validation_feedback_used = false
test_feedback_used = false
ast_execution_used = false
objective_evaluation_used = false
optimizer_generation_used = false
baseopt_modified = false
not_performance_claim = true
```

## 5. FE Ledger

Stage 4.0 记录完整 FE accounting identity：

```text
FE_total = FE_grouping + FE_proposal + FE_coordination_extra + FE_repair
```

当前 ledger：

```text
FE_grouping = 0
FE_proposal = 12
FE_coordination_extra = 0
FE_repair = 0
FE_total = 12
budget_scope = train_only_candidate_search
cross_candidate_evaluations_shared = false
```

这里的 `FE_proposal = 12` 是 train-only candidate search 的 proxy evaluation ledger，不是 objective benchmark evaluation。

## 6. Claim Boundary

Stage 4.0 可以声明：

```text
The frozen Stage 3.6 candidate pool has been ranked by a deterministic train-only search protocol under the Stage 3.7 family lock, with trace, promotion candidates, and FE ledger artifacts.
```

Stage 4.0 不能声明：

```text
operator performance improvement
validation success
sealed test success
SOTA result
learned final reusable coordination operators
```

## 7. Next Step

下一步是：

```text
Stage 4.1: train search audit and promotion-rule hardening
```

Stage 4.1 应审计 search trace、tie handling、promotion rule、family coverage 和 FE ledger，再决定是否进入 validation-only selection。

