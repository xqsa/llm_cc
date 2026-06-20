# Stage 2.8 Self Check Report

创建日期：2026-06-20
执行者：Codex
阶段：Frozen Candidate Promotion Contract

## 1. Scope

本阶段只做 frozen candidate promotion contract。它不是 LLM search，不是 evolution，不是 candidate generation，不是 optimizer runtime，也不是 operator discovery。

明确边界：

- no LLM；
- no evolution；
- no optimizer；
- no controller/scheduler；
- no candidate generation；
- no objective evaluation；
- no runtime AST execution；
- no test feedback；
- no tuning on test；
- no benchmark objective mutation；
- no BaseOpt modification。

## 2. Artifacts

新增 / 更新核心文件：

- `loco/coordination/candidate_promotion.py`：accepted candidate 到 frozen operator artifact 的 promotion contract。
- `artifacts/operators/stage2_8/stage2_6_corpus_valid_weighted_clip_shared_5.json`：promoted frozen operator artifact。
- `artifacts/operators/stage2_8/stage2_6_corpus_valid_weighted_clip_shared_5_promotion_receipt.json`：promotion receipt。
- `artifacts/operators/stage2_8_registry.jsonl`：promotion registry。
- `configs/stage2_8_candidate_promotion.yaml`：Stage 2.8 配置草案。
- `docs/stage2/stage2_8_candidate_promotion.md`：中文边界说明。
- `tests/stage2/test_stage2_8_candidate_promotion.py`：promotion contract tests。

## 3. Boundary Checks

| 检查项 | 状态 | 说明 |
| --- | --- | --- |
| accepted-only promotion | PASS | 只有 `decision = accepted` 的 candidate 可晋升。 |
| sealed split replay audit | PASS | 必须基于 Stage 2.7 `status = PASS` audit report。 |
| rejected candidate blocked | PASS | rejected candidate log 不能晋升。 |
| failed audit blocked | PASS | failed/tampered audit report 不能晋升。 |
| artifact schema | PASS | 输出 artifact 使用 `loco.operator_artifact.v1`。 |
| target scope | PASS | artifact 保持 `shared_variables_only`。 |
| receipt fingerprint | PASS | registry 记录 `promotion_receipt_fingerprint_sha256`，用于 Stage 2.9 receipt tamper detection。 |
| no test feedback | PASS | artifact、receipt、registry 均保留 no-test-feedback flag。 |
| no LLM/evolution imports | PASS | tests 覆盖 no LLM / no evolution imports。 |

## 4. Promotion Result

当前 committed promotion result：

```text
status = PROMOTED
candidate_id = stage2_6_corpus_valid_weighted_clip_shared_5
artifact_id = stage2_8.promoted.stage2_6_corpus_valid_weighted_clip_shared_5
source_ast_fingerprint_sha256 = ad6866257797a6373679ec30f1fac4a8c7313c6ec21361d972a622a025deb71c
```

## 5. Claim Boundary

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

## 6. Next Stage

建议下一步是 Stage 2.9：promotion replay and registry audit。

Stage 2.9 的重点应是冷启动重放 promoted artifact / receipt / registry，验证 fingerprints、source candidate provenance 和 sealed split audit provenance 是否可复现。
