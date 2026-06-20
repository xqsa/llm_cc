# Stage 3.6 Freeze Candidate Pool and Train-only Protocol

创建日期：2026-06-20
执行者：Codex
阶段边界：Stage 3.6 只 freeze Stage 3.5 的 quality-pass candidate pool，并准备 Stage 4 train-only evolution/search protocol。它不调用 LLM、不运行 evolution、不执行 AST、不评价 objective、不使用 validation/test feedback、不做 performance claim。

## 1. 阶段目标

Stage 3.5 已经生成并通过 coverage gate 的候选池：

```text
raw_candidate_count = 12
accepted_count = 12
quality_pass_count = 12
operator_family_count = 8
coverage_gate_status = PASS
```

Stage 3.6 的目标是把这批候选冻结成后续 Stage 4 的输入：

```text
Stage 3.5 quality-pass candidates
-> frozen_candidate_pool.jsonl
-> frozen_pool_manifest.json
-> candidate_family_descriptors.json
-> train_only_search_protocol.json
```

## 2. Frozen Pool

当前冻结结果：

```text
frozen_candidate_count = 12
quality_pass_only = true
family_count = 8
candidate_pool_frozen = true
```

每条 frozen candidate row 包含：

```text
candidate_id
ast_fingerprint_sha256
candidate_payload_sha256
freeze_fingerprint_sha256
operator_family
kind_sequence
target_scope = shared_variables_only
split = train
frozen = true
no_evolution_run = true
no_objective_evaluation = true
no_test_feedback = true
not_performance_claim = true
```

## 3. Family Descriptors

当前 frozen pool 覆盖 8 个 operator families：

```text
best_reward_select+dampening+clip
projection+dampening
projection+projection+best_reward_select+dampening+clip
projection+projection+weighted_consensus+projection
projection+reweighting+repair
reweighting+repair
reweighting+weighted_consensus+clip
weighted_consensus+projection
```

这些 family descriptors 是 Stage 4 train-only evolution/search 的候选池描述，不是性能结论。

## 4. Train-only Search Protocol

`train_only_search_protocol.json` 当前状态：

```text
status = READY_FOR_STAGE4_TRAIN_ONLY_SEARCH
allowed_split = train
validation_usage = selection only after train search
test_usage = sealed final reporting only
candidate_pool_frozen = true
frozen_candidate_count = 12
```

Stage 4 仍必须保持：

```text
BaseOpt must remain fixed across LOCO and baselines
all extra function evaluations must be counted
oracle grouping and detected grouping must be reported separately
no test feedback during search
```

## 5. Claim Boundary

Stage 3.6 可以声明：

```text
The Stage 3.5 quality-pass candidate pool is frozen and ready as an input to a future train-only evolution/search protocol.
```

Stage 3.6 不能声明：

```text
evolution search success
operator performance improvement
learned final reusable coordination operators
generalization
SOTA optimization result
```

## 6. Next Step

下一步可以进入 Stage 4，但 Stage 4 只能是：

```text
train-only evolution/search over frozen candidates
fixed BaseOpt
full FE accounting
no validation/test feedback during train search
no optimizer generation
```
