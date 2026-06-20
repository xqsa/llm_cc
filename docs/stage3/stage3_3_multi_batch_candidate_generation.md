# Stage 3.3 Train-only Multi-batch LLM Candidate Generation

创建日期：2026-06-20
执行者：Codex
阶段边界：Stage 3.3 只做 train-only multi-batch LLM candidate generation and rejection-corpus hardening。它真实调用 DeepSeek-compatible chat API 多次，保存 sanitized per-batch response，合并 train-only raw candidate batch，并复用 Stage 3.1 replay。no evolution run、no objective evaluation、no optimizer generation、no scheduler/controller generation、no test feedback、not a performance claim。

## 1. 阶段目标

Stage 3.3 的目标不是证明 operator 性能，而是证明 LOCO-LSGO 的 LLM candidate supply chain 可以从一次 smoke 扩展为多批次候选生成：

```text
.env -> provider client -> repeated chat API calls
     -> sanitized raw_batches/
     -> merged_raw_llm_output.json
     -> Stage 3.1 replay
     -> accepted/rejected logs
     -> dedup_report.json
     -> rejection_taxonomy.json
```

所有候选仍然必须是 typed coordination operator AST wrapper，且只能作用于 shared variables。

## 2. Allowed Scope

Stage 3.3 允许：

```text
real LLM API multi-batch call
train split only
typed coordination operator AST candidate
sanitized response artifact
accepted/rejected candidate log
AST fingerprint dedup
rejection reason taxonomy
```

Stage 3.3 不允许：

```text
evolution run
objective evaluation
optimizer generation
BaseOpt modification
scheduler/controller generation
optimizer selection
benchmark objective rewrite
validation feedback
test feedback
performance claim
```

## 3. Artifacts

Stage 3.3 输出：

```text
artifacts/candidates/stage3_3/raw_batches/raw_response_000.json
artifacts/candidates/stage3_3/raw_batches/raw_response_001.json
artifacts/candidates/stage3_3/raw_batches/raw_response_002.json
artifacts/candidates/stage3_3/raw_batches/raw_llm_output_000.json
artifacts/candidates/stage3_3/raw_batches/raw_llm_output_001.json
artifacts/candidates/stage3_3/raw_batches/raw_llm_output_002.json
artifacts/candidates/stage3_3/merged_raw_llm_output.json
artifacts/candidates/stage3_3/accepted_candidates.jsonl
artifacts/candidates/stage3_3/rejected_candidates.jsonl
artifacts/candidates/stage3_3/replay_report.json
artifacts/candidates/stage3_3/dedup_report.json
artifacts/candidates/stage3_3/rejection_taxonomy.json
artifacts/candidates/stage3_3/multi_batch_report.json
```

`raw_response_*.json` 是 sanitized response：保留 provenance，但省略 assistant message content，不包含 Authorization header 或 API key。

## 4. Current Multi-batch Result

当前真实 DeepSeek multi-batch run：

```text
status = PASS
provider = deepseek
base_url_host = api.deepseek.com
model = deepseek-v4-pro
wire_api = chat
reasoning_effort = high
split = train
api_call_count = 3
raw_candidate_count = 9
accepted_count = 9
unique_accepted_count = 9
duplicate_accepted_count = 0
rejected_count = 0
```

当前 run 没有产生 rejected candidates。这不是问题，也不能被包装为模型完美；它只说明这次真实 API 输出全部通过现有 schema/boundary validator。rejection taxonomy 管线仍然输出空分类，并由单元测试覆盖 non-shared target、optimizer/controller 等拒绝路径。

## 5. Dedup Boundary

Stage 3.3 使用 `ast_fingerprint_sha256` 作为 dedup key。dedup 只用于 candidate corpus hygiene：

```text
accepted_count = 9
unique_accepted_count = 9
duplicate_accepted_count = 0
```

这不是 diversity claim，也不是 performance claim。Stage 3.4 才应进入 candidate quality filter and static diversity audit。

## 6. Rejection Corpus Boundary

Stage 3.3 的 `rejection_taxonomy.json` 记录 rejection categories。当前真实 run：

```text
rejected_count = 0
categories = {}
```

测试覆盖的 rejection categories 包括：

```text
non_shared_target
forbidden_optimizer_or_controller
```

如果后续真实 multi-batch 产生 rejected candidates，应保留原始拒绝原因和 category，不应放宽 validator 来追求更高 accepted count。

## 7. Claim Boundary

Stage 3.3 可以声明：

```text
LOCO can repeatedly call a real chat-compatible LLM API, save sanitized train-only candidate batches, merge them, replay them through the Stage 3.1 audit chain, and harden the candidate corpus with AST fingerprint dedup and rejection taxonomy.
```

Stage 3.3 不能声明：

```text
learned reusable coordination operators
evolution search success
operator performance improvement
generalization
SOTA optimization result
```
