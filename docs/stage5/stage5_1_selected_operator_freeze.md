# Stage 5.1 Selected Operator Freeze

创建日期：2026-06-21
执行者：Codex
阶段边界：Stage 5.1 只冻结 Stage 5.0 选出的单一 coordination operator，作为 sealed-test final reporting 的唯一候选。它不调用 LLM、不生成新候选、不修改 prompt / train search / promotion rule / validation rule、不访问 sealed test、不做 objective evaluation、不修改 BaseOpt，也不是 not a performance claim。

## 1. Goal

Stage 5.0 选出的候选是：

```text
stage3_5_batch_1_weighted_consensus_projection
```

Stage 5.1 的目标是将这个候选冻结为：

```text
FROZEN_FOR_SEALED_TEST_NOT_FINAL
```

这个状态表示它可以进入 Stage 6 sealed-test final reporting，但仍然不是 final operator、不是 objective performance claim。

## 2. Inputs

Stage 5.1 只读取：

```text
artifacts/validation/stage5_0/selection_decision.json
artifacts/validation/stage5_0/validation_report.json
artifacts/candidates/stage3_6/frozen_candidate_pool.jsonl
```

Stage 5.1 不重新选择、不重新计算 validation score、不改 Stage 5.0 selection rule。

## 3. Outputs

Stage 5.1 产物：

```text
artifacts/selected/stage5_1/selected_operator.json
artifacts/selected/stage5_1/selected_operator_ast.json
artifacts/selected/stage5_1/selected_operator_manifest.json
artifacts/selected/stage5_1/sealed_test_readiness_protocol.json
artifacts/selected/stage5_1/freeze_report.json
```

## 4. Boundary Flags

Stage 5.1 preserves:

```text
validation_feedback_used = false
test_feedback_used = false
sealed_test_access_used = false
objective_evaluation_used = false
llm_call_used = false
new_candidate_generation_used = false
prompt_revision_used = false
train_search_revision_used = false
promotion_rule_revision_used = false
validation_rule_revision_used = false
baseopt_modified = false
optimizer_generation_used = false
controller_scheduler_generation_used = false
not_performance_claim = true
```

## 5. Next Step

The next stage can be:

```text
Stage 6.0: sealed test final reporting
```

Stage 6.0 must use only the Stage 5.1 frozen selected operator and must preserve complete FE accounting, fixed BaseOpt, separated oracle/detected grouping reports, and sealed-test isolation.
