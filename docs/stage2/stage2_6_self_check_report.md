# Stage 2.6 Self Check Report

创建日期：2026-06-20
执行者：Codex
阶段：Candidate Artifact Logging Schema and Rejection Corpus

## 1. Scope

本阶段只定义 candidate artifact logging schema、rejection corpus 和 replay verifier。它不是 LLM search，不是 evolution，不是 optimizer runtime，也不是 operator discovery。

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

- `loco/coordination/candidate_logging.py`：candidate logging、reject reason taxonomy、replay verifier。
- `artifacts/candidates/stage2_6/rejection_corpus.jsonl`：replayable rejection corpus。
- `artifacts/candidates/stage2_6/accepted_candidates.jsonl`：accepted candidate log artifact。
- `artifacts/candidates/stage2_6/rejected_candidates.jsonl`：rejected candidate log artifact。
- `artifacts/candidates/stage2_6/replay_report.json`：replay verifier report。
- `configs/stage2_6_candidate_logging.yaml`：Stage 2.6 配置草案。
- `docs/stage2/stage2_6_candidate_logging.md`：中文边界说明。
- `tests/stage2/test_stage2_6_candidate_logging.py`：candidate logging 与 replay tests。

## 3. Boundary Checks

| 检查项 | 状态 | 说明 |
| --- | --- | --- |
| accepted log schema | PASS | accepted rows 使用 `loco.candidate_log.v1`。 |
| rejected log schema | PASS | rejected rows 使用 `loco.candidate_log.v1`。 |
| deterministic accepted fingerprint | PASS | accepted rows 记录 `ast_fingerprint_sha256`。 |
| reject taxonomy | PASS | rejected rows 记录 `reject_reason_category`。 |
| rejection corpus coverage | PASS | 覆盖 non-shared target、optimizer/controller、executable code、forbidden metadata、invalid schema。 |
| replay verifier | PASS | committed replay report `status = PASS`。 |
| tamper detection | PASS | 修改 accepted AST payload 会导致 fingerprint mismatch。 |
| no LLM/evolution imports | PASS | tests 覆盖 no LLM / no evolution imports。 |
| no test feedback | PASS | log schema 与 replay report 均记录 no-test-feedback boundary。 |

## 4. Replay Report

当前 committed replay report：

```text
status = PASS
total_count = 6
accepted_count = 1
rejected_count = 5
fingerprint_mismatch_count = 0
decision_mismatch_count = 0
category_mismatch_count = 0
```

## 5. Claim Boundary

Stage 2.6 可以声明：

```text
LOCO can record and replay candidate AST preflight decisions through an auditable logging schema and rejection corpus.
```

Stage 2.6 不能声明：

```text
LLM-generated operator success
evolution search success
learned reusable coordination operators
optimizer performance improvement
SOTA optimization result
```

## 6. Next Stage

建议下一步是 Stage 2.7：sealed split replay audit for candidate logs。

Stage 2.7 的重点应是 split id、frozen candidate promotion、candidate log replay 和 no-test-feedback audit，而不是进入 LLM/evolution search。
