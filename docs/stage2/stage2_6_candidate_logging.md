# Stage 2.6 Candidate Artifact Logging Schema

创建日期：2026-06-20
执行者：Codex
阶段边界：只定义 candidate artifact logging schema、rejection corpus 和 replay verifier；不调用 LLM、不运行 evolution、不生成候选、不实现 optimizer、controller/scheduler 或 operator discovery。

## 1. 阶段目标

Stage 2.6 的目标是在真正进入 Stage 3 之前，先固定候选 AST 的审计表面：

```text
typed AST candidate payload -> Stage 3 preflight -> accepted/rejected JSONL logs -> replay verifier
```

这一步不是 candidate generation。它只说明：未来如果 LLM/evolution 产生 AST candidate，LOCO 将如何记录 accepted/rejected decision、fingerprint、reject reason taxonomy、split boundary 和 no-test-feedback flags。

## 2. Candidate Artifact Logging Schema

Stage 2.6 新增：

```text
loco/coordination/candidate_logging.py
```

该模块只做 data-only preflight logging：

- 调用既有 `stage3_preflight_check`；
- 写出 accepted/rejected JSONL；
- 记录 deterministic fingerprint；
- 记录 reject reason category；
- replay 时重新运行 preflight；
- 不解释 AST；
- 不调用 objective function；
- 不调用 LLM；
- 不运行 evolution。

通用字段：

```text
log_schema_version = loco.candidate_log.v1
stage = 2.6
source_stage
candidate_id
decision
split = pre_stage3_schema_only
ast_payload
candidate_payload_sha256
no_llm = true
no_evolution = true
no_optimizer = true
no_test_feedback = true
no_objective_evaluation = true
```

accepted-only 字段：

```text
serialized_ast
ast_fingerprint_sha256
```

rejected-only 字段：

```text
reject_reason
reject_reason_category
```

## 3. Rejection Corpus

Stage 2.6 固化一个 replayable rejection corpus：

```text
artifacts/candidates/stage2_6/rejection_corpus.jsonl
```

覆盖：

- `non_shared_target`；
- `forbidden_optimizer_or_controller`；
- `executable_code`；
- `forbidden_metadata`；
- `invalid_schema`。

同时包含一个 accepted control candidate，用于验证 accepted path 的 fingerprint replay。

## 4. Replay Verifier

Replay verifier 读取：

```text
artifacts/candidates/stage2_6/accepted_candidates.jsonl
artifacts/candidates/stage2_6/rejected_candidates.jsonl
```

然后重新运行 `stage3_preflight_check`。它检查：

- accepted decision 是否仍 accepted；
- accepted AST fingerprint 是否一致；
- rejected decision 是否仍 rejected；
- reject reason category 是否一致；
- 是否存在 decision mismatch；
- 是否存在 fingerprint mismatch；
- 是否存在 category mismatch。

当前 committed replay report：

```text
artifacts/candidates/stage2_6/replay_report.json
```

状态为：

```text
status = PASS
accepted_count = 1
rejected_count = 5
fingerprint_mismatch_count = 0
decision_mismatch_count = 0
category_mismatch_count = 0
```

## 5. Claim Boundary

Stage 2.6 可以声明：

```text
LOCO has a replayable candidate artifact logging schema and rejection corpus for future Stage 3 candidate ASTs.
```

Stage 2.6 不能声明：

```text
LLM-generated operator success
evolution search success
learned reusable coordination operators
optimizer performance improvement
SOTA optimization result
```

## 6. 下一步

建议下一步是 Stage 2.7：sealed split replay audit for candidate logs。

Stage 2.7 应继续不调用 LLM/evolution，只把 train/validation/test split id、candidate log replay、artifact freezing 和 no-test-feedback audit 串起来。Stage 3 的 LLM candidate generation 应等待 sealed split replay audit 稳定后再启动。
