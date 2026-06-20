# Stage 5.0 Validation-only Selection

创建日期：2026-06-21
执行者：Codex
阶段边界：Stage 5.0 只在 Stage 4.1 的 tie-hardened validation-ready set 上做 validation-only selection。它可以执行已经冻结的 typed AST 做 shared-variable conflict diagnostics，但不调用 LLM、不生成新候选、不修改 prompt / train search / promotion rule、不访问 sealed test、不做 objective evaluation、不修改 BaseOpt，也不是 not a performance claim。

## 1. Goal

Stage 4.1 产生了 6 个 tie-hardened validation-ready candidates：

```text
VALIDATION_READY_TIE_HARDENED_NOT_FINAL
```

Stage 5.0 的目标是使用预声明的 validation-only 规则，从这 6 个候选中选出一个进入 Stage 5.1 selected operator freeze。

输出状态是：

```text
SELECTED_FOR_SEALED_TEST_NOT_FINAL
```

这不是 final operator，也不是 benchmark performance claim。

## 2. Inputs

Stage 5.0 只读取：

```text
artifacts/search/stage4_1/promotion_decision.json
artifacts/candidates/stage3_6/frozen_candidate_pool.jsonl
```

Validation 结果不得回流到：

```text
prompt generation
candidate generation
Stage 3.6 frozen pool
Stage 4.0 train search score
Stage 4.1 promotion rule
```

## 3. Validation Selection Rule

Stage 5.0 在 deterministic validation conflict states 上执行 frozen typed AST，并计算：

```text
normalized_distance_to_best_reward_proposal
normalized_update_size
oscillation_score
```

选择分数：

```text
selection_score =
mean(0.50 * normalized_distance_to_best_reward_proposal
   + 0.35 * normalized_update_size
   + 0.15 * oscillation_score)
```

排序规则：

```text
minimize selection_score
tie-break 1: lower FE_total
tie-break 2: lower node_count
tie-break 3: lexicographic candidate_id
```

这些指标只描述 shared-variable proposal coordination behavior，不是 objective-value improvement。

## 4. Outputs

Stage 5.0 产物：

```text
artifacts/validation/stage5_0/validation_trace.jsonl
artifacts/validation/stage5_0/validation_metrics.json
artifacts/validation/stage5_0/selection_decision.json
artifacts/validation/stage5_0/fe_ledger.json
artifacts/validation/stage5_0/validation_report.json
```

## 5. Boundary Flags

Stage 5.0 preserves:

```text
validation_feedback_used = true
test_feedback_used = false
sealed_test_access_used = false
objective_evaluation_used = false
llm_call_used = false
new_candidate_generation_used = false
prompt_revision_used = false
train_search_revision_used = false
promotion_rule_revision_used = false
baseopt_modified = false
optimizer_generation_used = false
controller_scheduler_generation_used = false
not_performance_claim = true
```

## 6. Next Step

The next stage can be:

```text
Stage 5.1: selected operator freeze
```

Stage 5.1 should freeze the selected operator and prepare sealed-test execution without adding LLM calls, candidate generation, or validation-driven prompt/search revisions.
