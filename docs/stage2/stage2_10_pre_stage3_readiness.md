# Stage 2.10 Pre-Stage-3 Readiness Gate

创建日期：2026-06-20
执行者：Codex
阶段边界：只做 pre-Stage-3 readiness gate；不调用 LLM、不运行 evolution、不生成 candidate、不重新 promotion、不执行 AST、不调用 objective function、不实现 optimizer/controller/scheduler。

## 1. 阶段目标

Stage 2.0-2.9 已经建立了 conflict state、typed AST boundary、candidate logging、sealed split replay audit、frozen candidate promotion contract、promotion replay and registry audit。Stage 2.10 的目标是把这些证据汇总成一个进入 Stage 3 前的 readiness decision：

```text
Stage 2.7 sealed split replay audit PASS
Stage 2.8 frozen candidate promotion registry ready
Stage 2.9 promotion replay and registry audit PASS
-> Stage 2.10 readiness decision
```

该 decision 只回答一个问题：

```text
是否允许进入 Stage 3 的 LLM/evolution search over typed coordination operator ASTs？
```

它不是性能结论，不是 learned operator 成功，不是 SOTA claim。

## 2. Decision Artifact

新增 decision artifact：

```text
artifacts/readiness/stage2_10_readiness_decision.json
```

当前 committed decision：

```text
schema_version = loco.pre_stage3_readiness.v1
stage = 2.10
decision = READY_FOR_STAGE3_BOUNDARY_ONLY
stage3_allowed = true
```

`READY_FOR_STAGE3_BOUNDARY_ONLY` 的含义很窄：只允许 Stage 3 在 typed coordination operator AST 空间内做 LLM/evolution search，仍然必须维持 no test feedback、no optimizer generation、no BaseOpt modification 等边界。

## 3. Required Gates

Stage 2.10 要求以下 gate 为 PASS / ready：

- `stage2_7_sealed_split_replay_audit`；
- `stage2_8_frozen_candidate_promotion_contract`；
- `stage2_9_promotion_replay_and_registry_audit`。

如果任一 gate 失败，decision 必须变成：

```text
decision = BLOCK_STAGE3
stage3_allowed = false
```

## 4. Allowed Stage 3 Scope

Stage 3 允许范围：

```text
LLM/evolution search over typed coordination operator ASTs only
```

这意味着 LLM/evolution 只能在受限 typed AST 空间内提出 coordination operator 结构，并且 operator 仍然只作用于 shared variables。

## 5. Forbidden Stage 3 Scope

Stage 3 仍然禁止：

- optimizer generation；
- BaseOpt modification；
- scheduler/controller generation；
- optimizer selection；
- benchmark objective rewrite；
- test feedback access；
- test-set tuning；
- untyped executable code generation。

## 6. Known Risks

Stage 2.10 记录但不阻塞的风险：

- real MetaBox benchmark-only smoke 当前为 PASS；
- MetaBox top-level import 仍不是 Stage 3 readiness 的必要条件；
- Stage 3 仍需要单独定义 sealed train/validation/test protocol；
- 当前 readiness 不是 optimizer performance claim。

## 7. Claim Boundary

Stage 2.10 可以声明：

```text
LOCO has a pre-Stage-3 readiness decision that permits only boundary-constrained typed-AST LLM/evolution search.
```

Stage 2.10 不能声明：

```text
LLM-generated operator success
evolution search success
learned reusable coordination operators
optimizer performance improvement
SOTA optimization result
```

## 8. 下一步

下一步可以进入 Stage 3，但必须先写 Stage 3 protocol：

- sealed train/validation/test split；
- no test feedback enforcement；
- LLM prompt/output schema；
- evolution search budget；
- operator acceptance/rejection logs；
- FE accounting；
- frozen-final-operator rule。
