# Stage 2.7 Self Check Report

创建日期：2026-06-20
执行者：Codex
阶段：Sealed Split Replay Audit for Candidate Logs

## 1. Scope

本阶段只做 sealed split replay audit。它不是 LLM search，不是 evolution，不是 candidate generation，不是 optimizer runtime，也不是 operator discovery。

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

- `loco/coordination/split_replay_audit.py`：sealed split manifest loading、file fingerprint audit、split/no-test-feedback audit。
- `artifacts/candidates/stage2_7/sealed_split_manifest.json`：sealed split manifest。
- `artifacts/candidates/stage2_7/split_replay_audit_report.json`：audit report。
- `configs/stage2_7_sealed_split_replay_audit.yaml`：Stage 2.7 配置草案。
- `docs/stage2/stage2_7_sealed_split_replay_audit.md`：中文边界说明。
- `tests/stage2/test_stage2_7_sealed_split_replay_audit.py`：sealed split replay audit tests。

## 3. Boundary Checks

| 检查项 | 状态 | 说明 |
| --- | --- | --- |
| sealed manifest | PASS | manifest `sealed = true`。 |
| Stage 2.6 file fingerprints | PASS | accepted/rejected/replay report sha256 均匹配。 |
| replay report status | PASS | Stage 2.6 replay report `status = PASS`。 |
| split boundary | PASS | 只允许 `pre_stage3_schema_only`。 |
| test split forbidden | PASS | candidate log rows 不使用 test split。 |
| no test feedback | PASS | candidate log rows 均保持 `no_test_feedback = true`。 |
| tamper detection | PASS | 修改 split/test-feedback flag 会触发 FAIL。 |
| no LLM/evolution imports | PASS | tests 覆盖 no LLM / no evolution imports。 |

## 4. Audit Report

当前 committed audit report：

```text
status = PASS
accepted_count = 1
rejected_count = 5
file_fingerprint_mismatch_count = 0
split_violation_count = 0
test_feedback_violation_count = 0
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

## 6. Next Stage

建议下一步是 Stage 2.8：frozen candidate promotion contract。

Stage 2.8 的重点应是 accepted candidate 如何晋升为 frozen operator artifact，以及晋升时的 provenance / split id / fingerprint / no-test-feedback audit。
