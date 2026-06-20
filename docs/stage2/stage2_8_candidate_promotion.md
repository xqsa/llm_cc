# Stage 2.8 Frozen Candidate Promotion Contract

创建日期：2026-06-20
执行者：Codex
阶段边界：只定义并验证 accepted candidate 到 frozen operator artifact 的晋升契约；不调用 LLM、不运行 evolution、不生成新 candidate、不执行 AST、不调用 objective function、不实现 optimizer/controller/scheduler。

## 1. 阶段目标

Stage 2.6 记录 candidate preflight decisions，Stage 2.7 用 sealed split replay audit 锁定这些 candidate logs。Stage 2.8 的目标是继续把边界前移一步：

```text
Stage 2.6 accepted candidate
-> Stage 2.7 sealed split replay audit PASS
-> Stage 2.8 frozen candidate promotion contract
-> frozen operator artifact + promotion receipt + promotion registry
```

这一步不是 LLM/evolution search，也不是 operator discovery。它只说明：一个已经通过 schema/preflight 的 accepted candidate，如何在没有 test feedback 的前提下，被冻结成可审计 artifact。

## 2. 输入契约

Stage 2.8 的输入必须同时满足：

- candidate row 来自 `artifacts/candidates/stage2_6/accepted_candidates.jsonl`；
- `decision = accepted`；
- `split = pre_stage3_schema_only`；
- `no_llm = true`；
- `no_evolution = true`；
- `no_optimizer = true`；
- `no_test_feedback = true`；
- `no_objective_evaluation = true`；
- Stage 2.7 sealed manifest 绑定 accepted/rejected/replay report 文件 sha256；
- Stage 2.7 audit report `status = PASS`；
- Stage 2.7 audit report 的 fingerprint/split/test-feedback/LLM/evolution violation count 均为 0。

rejected candidate、test split candidate、failed audit report、tampered candidate log 都不能晋升。

## 3. 输出 artifact

新增 frozen operator artifact：

```text
artifacts/operators/stage2_8/stage2_6_corpus_valid_weighted_clip_shared_5.json
```

它使用现有 artifact schema：

```text
artifact_schema_version = loco.operator_artifact.v1
source = stage2_6_accepted_candidate_promotion
stage_created = 2.8
target_scope = shared_variables_only
dsl_schema_version = loco.dsl.v1
```

provenance 必须保留：

```text
frozen = true
no_llm = true
no_evolution = true
no_optimizer = true
no_candidate_generation = true
no_objective_evaluation = true
no_arbitrary_executable_code = true
source_candidate_id
source_ast_fingerprint_sha256
```

split policy 必须保留：

```text
source_split = pre_stage3_schema_only
test_mode_allowed = true
no_test_feedback = true
no_tuning_on_test = true
```

## 4. Promotion Receipt

新增 promotion receipt：

```text
artifacts/operators/stage2_8/stage2_6_corpus_valid_weighted_clip_shared_5_promotion_receipt.json
```

receipt schema：

```text
schema_version = loco.candidate_promotion_receipt.v1
stage = 2.8
status = PROMOTED
```

receipt 必须记录：

- source candidate id；
- source accepted log path 和 sha256；
- source AST fingerprint；
- sealed manifest path 和 fingerprint；
- Stage 2.7 audit report path 和 fingerprint；
- promoted artifact path 和 fingerprint；
- promotion fingerprint；
- no LLM / no evolution / no optimizer / no candidate generation / no test feedback / no objective evaluation flags。

## 5. Promotion Registry

新增 registry：

```text
artifacts/operators/stage2_8_registry.jsonl
```

每一行绑定：

- promoted artifact path；
- promotion receipt path；
- source candidate id；
- source AST fingerprint；
- artifact fingerprint；
- promotion fingerprint；
- split；
- target scope；
- frozen/no-test-feedback flags。

## 6. Claim Boundary

Stage 2.8 可以声明：

```text
LOCO can promote an accepted candidate into a frozen operator artifact under a sealed split replay audit contract.
```

Stage 2.8 不能声明：

```text
LLM-generated operator success
evolution search success
learned reusable coordination operators
optimizer performance improvement
SOTA optimization result
```

## 7. 下一步

建议下一步是 Stage 2.9：promotion replay and registry audit。

Stage 2.9 应继续不调用 LLM/evolution，只做 promoted artifact / receipt / registry 的 replay audit，验证 promotion fingerprint、artifact loadability、source candidate fingerprint 和 sealed split provenance 在冷启动环境中可复现。
