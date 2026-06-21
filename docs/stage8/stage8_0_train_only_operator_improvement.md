# Stage 8.0 Train-only Operator Improvement

创建日期：2026-06-21  
执行者：Codex  
阶段边界：Stage 8.0 只在 Stage 3.6 frozen candidate pool 上做 train-only operator improvement，并遵守 Stage 7.6 comparator contract。它不调用 LLM，不生成新候选，不执行 AST，不做 objective evaluation，不跑 benchmark，不使用 validation/test feedback，也不把 reported results 变成 runtime feedback 或 performance claim。

## 1. Goal

Stage 8.0 的目标不是发明新的 optimizer，而是对冻结的协调候选做 deterministic train-only improvement record。它把 Stage 3.6 的 12 个 frozen candidates 接入一个可复现、可审计的改进链：

```text
frozen_candidate_pool.jsonl
-> train-only improvement trace
-> improvement candidates
-> FE ledger
-> improvement report
-> next route decision
```

这个阶段只证明训练期改进记录和边界成立。它不证明真实 objective 性能，也不构成 validation 或 sealed test 结论。

## 2. Inputs

Stage 8.0 只读取：

```text
artifacts/candidates/stage3_6/frozen_candidate_pool.jsonl
configs/stage4_coordination_family_space.yaml
configs/stage7_6_reported_results_comparator_audit.yaml
artifacts/objective_eval/stage7_6/reported_results_comparator_audit_report.json
```

输入要求：

```text
candidate_pool_frozen = true
split = train
target_scope = shared_variables_only
comparator_contract_stage = 7.6
```

## 3. Outputs

当前 Stage 8.0 产物：

```text
artifacts/improvement/stage8_0/improvement_trace.jsonl
artifacts/improvement/stage8_0/improvement_candidates.json
artifacts/improvement/stage8_0/fe_ledger.json
artifacts/improvement/stage8_0/improvement_report.json
artifacts/improvement/stage8_0/next_route_decision.json
```

`improvement_trace.jsonl` 为 12 个 frozen candidates 生成 deterministic train-only improvement score 和 rank。

`improvement_candidates.json` 只标记 top-k candidates 为：

```text
TRAIN_ONLY_RECORDED
```

这表示它们可以进入后续 Stage 8.1 selection / audit gate，但不是 final selected operator。

## 4. Current Result

当前结果：

```text
status = PASS
source_stage = 7.6
candidate_pool_source_stage = 3.6
candidate_count = 12
improvement_candidate_count = 4
allowed_split = train
train_only_improvement_executed = true
comparator_contract_used = true
next_status = READY_FOR_STAGE8_1_TRAIN_ONLY_SELECTION_AUDIT
FE_total = 12
llm_call_used = false
new_candidate_generation_used = false
validation_feedback_used = false
test_feedback_used = false
ast_execution_used = false
objective_evaluation_used = false
benchmark_execution_used = false
reported_results_used_as_runtime_feedback = false
baseopt_modified = false
not_performance_claim = true
```

## 5. FE Ledger

Stage 8.0 records the full FE accounting identity:

```text
FE_total = FE_grouping + FE_proposal + FE_coordination_extra + FE_repair
```

Current ledger:

```text
FE_grouping = 0
FE_proposal = 12
FE_coordination_extra = 0
FE_repair = 0
FE_total = 12
budget_scope = train_only_operator_improvement
cross_candidate_evaluations_shared = false
```

这里的 `FE_proposal = 12` 是 train-only improvement ledger，不是 objective benchmark evaluation。

## 6. Claim Boundary

Stage 8.0 可以声明：

```text
The frozen Stage 3.6 candidate pool has been ranked by a deterministic train-only improvement protocol under the Stage 7.6 comparator contract, with trace, improvement candidates, FE ledger, and route decision artifacts.
```

Stage 8.0 不能声明：

```text
operator performance improvement
validation success
sealed test success
SOTA result
learned final reusable coordination operators
```

## 7. Next Step

Stage 8.0 next status:

```text
READY_FOR_STAGE8_1_TRAIN_ONLY_SELECTION_AUDIT
```

下一步是 Stage 8.1: 对 train-only improvement trace 做 selection audit、threshold review 和 boundary hardening，再决定是否进入任何更后续的选择流程。
