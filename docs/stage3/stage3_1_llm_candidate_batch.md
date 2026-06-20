# Stage 3.1 Small-Batch LLM Candidate Generation

创建日期：2026-06-20
执行者：Codex
阶段边界：Stage 3.1 只做 small-batch LLM candidate generation 的 train-only capture、schema validation、accepted/rejected logging 和 replay audit；no evolution run、no objective evaluation、no optimizer generation、no scheduler/controller generation、no test feedback、not a performance claim。

## 1. 阶段目标

Stage 3.1 是 Stage 3.0 protocol lock 之后的第一步真实 candidate generation surface。它只回答：

```text
能否把一小批 LLM candidate 输出捕获为 typed coordination operator AST wrapper，并在 train-only 边界内完成 accepted/rejected 审计？
```

Stage 3.1 不回答：

```text
operator 是否有效
operator 是否提升优化性能
evolution selection 是否成功
是否形成 reusable operator library
```

## 2. 依赖边界

Stage 3.1 必须依赖：

```text
artifacts/readiness/stage3_0_protocol_lock_report.json
status = PASS
```

若 Stage 3.0 protocol lock 不是 PASS，则 Stage 3.1 candidate batch 不能处理。

## 3. 输入契约

Stage 3.1 的 raw LLM output 固定为：

```text
artifacts/candidates/stage3_1/raw_llm_output.json
schema_version = loco.stage3_1_raw_llm_batch.v1
split = train
```

每个 candidate 必须是：

```text
schema_version = loco.llm_candidate.v1
ast.schema_version = loco.dsl.v1
declared_scope.target = shared_variables_only
```

## 4. 输出契约

Stage 3.1 输出：

```text
artifacts/candidates/stage3_1/accepted_candidates.jsonl
artifacts/candidates/stage3_1/rejected_candidates.jsonl
artifacts/candidates/stage3_1/replay_report.json
```

当前 batch：

```text
accepted_count = 1
rejected_count = 2
status = PASS
split = train
```

Accepted candidate 只表示通过 schema 和 boundary validation，不表示性能有效。

Rejected candidates 必须保留 reject_reason 和 reject_reason_category，当前覆盖：

- non_shared_target；
- forbidden_optimizer_or_controller。

## 5. Train-Only Firewall

Stage 3.1 只允许 train split：

- no validation selection；
- no test feedback；
- no test-set tuning；
- no prompt update from validation/test；
- no operator library update from test。

任何 raw batch 若 `split != train` 必须 rejected。

## 6. 禁止动作

Stage 3.1 禁止：

- no evolution run；
- no objective evaluation；
- no optimizer generation；
- no BaseOpt modification；
- no scheduler/controller generation；
- no optimizer selection；
- no benchmark objective rewrite；
- no test feedback；
- no performance claim。

## 7. Claim Boundary

Stage 3.1 可以声明：

```text
LOCO can capture a first small-batch LLM candidate output as typed coordination operator AST wrappers and audit accepted/rejected train-only logs.
```

Stage 3.1 不能声明：

```text
learned reusable coordination operators
evolution search success
operator performance improvement
SOTA optimization result
```
