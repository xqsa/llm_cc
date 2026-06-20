# Stage 2.9 Promotion Replay and Registry Audit

创建日期：2026-06-20
执行者：Codex
阶段边界：只做 promoted artifact / promotion receipt / promotion registry 的 cold-start replay audit；不调用 LLM、不运行 evolution、不生成 candidate、不重新 promotion、不执行 AST、不调用 objective function、不实现 optimizer/controller/scheduler。

## 1. 阶段目标

Stage 2.8 已经把一个 Stage 2.6 accepted candidate 在 Stage 2.7 sealed split replay audit `PASS` 的前提下晋升为 frozen operator artifact。Stage 2.9 的目标是验证这个 promotion 不是一次性脚本输出，而是可冷启动重放审计的 artifact chain：

```text
Stage 2.8 promoted registry
-> load promoted artifact
-> load promotion receipt
-> recompute artifact fingerprint
-> recompute receipt fingerprint
-> recompute promotion fingerprint
-> verify Stage 2.6 / Stage 2.7 provenance
```

这一步不是 LLM/evolution search，也不是 operator discovery。它只证明 promoted artifact、receipt 和 registry 在新进程中仍能互相绑定，并且可以检测 artifact tamper 与 receipt tamper。

## 2. 输入

Stage 2.9 的输入是：

```text
artifacts/operators/stage2_8_registry.jsonl
```

registry 每一行必须至少绑定：

- promoted artifact path；
- promotion receipt path；
- artifact fingerprint；
- promotion receipt fingerprint；
- promotion fingerprint；
- source candidate id；
- source AST fingerprint；
- split；
- target scope；
- frozen/no-test-feedback/no-LLM/no-evolution flags。

## 3. Audit Report

新增 audit report：

```text
artifacts/operators/stage2_9/promotion_replay_audit_report.json
```

schema：

```text
schema_version = loco.promotion_replay_audit.v1
stage = 2.9
status = PASS
```

当前 committed report：

```text
registry_entry_count = 1
audited_artifact_count = 1
artifact_fingerprint_mismatch_count = 0
receipt_fingerprint_mismatch_count = 0
promotion_fingerprint_mismatch_count = 0
source_candidate_fingerprint_mismatch_count = 0
sealed_manifest_fingerprint_mismatch_count = 0
audit_report_fingerprint_mismatch_count = 0
schema_violation_count = 0
boundary_violation_count = 0
```

## 4. Tamper Detection

Stage 2.9 tests 覆盖两类篡改：

- 修改 promoted artifact，例如把 `split_policy.no_test_feedback` 改成 `false`，audit 必须报告 `FAIL`；
- 修改 promotion receipt，例如改写 `source_ast_fingerprint_sha256`，audit 必须报告 `FAIL`。

这里 registry 中的 `promotion_receipt_fingerprint_sha256` 是独立事实源。没有这个字段，receipt 被篡改后 audit 只能相信被篡改的 receipt 自己，无法完成 cold-start tamper detection。

## 5. Claim Boundary

Stage 2.9 可以声明：

```text
LOCO can cold-start replay and audit promoted operator artifacts against their promotion receipts and registry fingerprints.
```

Stage 2.9 不能声明：

```text
LLM-generated operator success
evolution search success
learned reusable coordination operators
optimizer performance improvement
SOTA optimization result
```

## 6. 下一步

建议下一步是 Stage 2.10：pre-Stage-3 readiness gate。

Stage 2.10 应继续不调用 LLM/evolution，只做进入 Stage 3 前的 readiness checklist：artifact chain 是否 sealed、registry audit 是否 PASS、candidate/promotion provenance 是否完整、forbidden actions 是否仍被测试覆盖。
