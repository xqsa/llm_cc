# Stage 2.7 Sealed Split Replay Audit

创建日期：2026-06-20
执行者：Codex
阶段边界：只把 Stage 2.6 candidate logs 绑定到 sealed split manifest 并审计 replay/no-test-feedback invariants；不调用 LLM、不运行 evolution、不生成候选、不执行 AST、不实现 optimizer 或 controller/scheduler。

## 1. 阶段目标

Stage 2.6 已经定义 candidate artifact logging schema 和 rejection corpus。Stage 2.7 继续加固进入 Stage 3 前的审稿风险边界：

```text
Stage 2.6 accepted/rejected logs
-> sealed split manifest
-> file fingerprint audit
-> replay status audit
-> no-test-feedback audit
```

这一步不是 benchmark split generation，也不是 LLM/evolution search。它只证明当前 candidate logs 被一个 sealed manifest 锁定，且 replay/audit 可以检测篡改、test split 泄漏和 test feedback 污染。

## 2. Sealed Manifest

新增 manifest：

```text
artifacts/candidates/stage2_7/sealed_split_manifest.json
```

关键字段：

```text
schema_version = loco.sealed_split_manifest.v1
stage = 2.7
sealed = true
allowed_candidate_log_splits = [pre_stage3_schema_only]
test_split_locked = true
no_llm = true
no_evolution = true
no_optimizer = true
no_candidate_generation = true
no_test_feedback = true
```

manifest 绑定 Stage 2.6 artifacts 的 sha256：

```text
artifacts/candidates/stage2_6/accepted_candidates.jsonl
artifacts/candidates/stage2_6/rejected_candidates.jsonl
artifacts/candidates/stage2_6/replay_report.json
```

## 3. Replay Audit

新增 audit module：

```text
loco/coordination/split_replay_audit.py
```

它检查：

- manifest 是否 sealed；
- Stage 2.6 accepted/rejected/replay report 文件 sha256 是否匹配；
- Stage 2.6 replay report 是否仍为 `PASS`；
- candidate log row 的 `split` 是否只使用 `pre_stage3_schema_only`；
- candidate log row 是否没有使用 `test` split；
- candidate log row 是否保持 `no_test_feedback = true`；
- candidate log row 是否没有 `test_feedback_used` 或 `tuned_on_test`；
- candidate log row 是否保持 no LLM / no evolution flags。

当前 audit report：

```text
artifacts/candidates/stage2_7/split_replay_audit_report.json
```

状态为：

```text
status = PASS
accepted_count = 1
rejected_count = 5
file_fingerprint_mismatch_count = 0
split_violation_count = 0
test_feedback_violation_count = 0
```

## 4. Tamper Detection

Stage 2.7 tests 会复制 Stage 2.6 logs 到临时目录，然后修改 accepted row：

```text
split = test
no_test_feedback = false
```

audit 必须报告：

```text
status = FAIL
file_fingerprint_mismatch_count = 1
split_violation_count = 1
test_feedback_violation_count = 1
```

## 5. Claim Boundary

Stage 2.7 可以声明：

```text
LOCO can audit candidate logs against a sealed split manifest and detect replay/test-feedback violations.
```

Stage 2.7 不能声明：

```text
LLM-generated operator success
evolution search success
learned reusable coordination operators
optimizer performance improvement
SOTA optimization result
```

## 6. 下一步

建议下一步是 Stage 2.8：frozen candidate promotion contract。

Stage 2.8 仍应不调用 LLM/evolution，只定义 accepted candidate 如何从 preflight log 晋升为 frozen operator artifact，以及晋升时必须携带的 split id、fingerprint、provenance 和 no-test-feedback audit。
