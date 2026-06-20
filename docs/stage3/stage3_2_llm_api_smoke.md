# Stage 3.2 Real LLM API Adapter Smoke

创建日期：2026-06-20
执行者：Codex
阶段边界：Stage 3.2 只做 real LLM API adapter smoke；调用一次 DeepSeek-compatible chat API，保存 sanitized response，解析 train-only raw candidate batch，并复用 Stage 3.1 replay。no evolution run、no objective evaluation、no optimizer generation、no scheduler/controller generation、no test feedback、not a performance claim。

## 1. 阶段目标

Stage 3.2 的目标是把真实 LLM API 接入已经锁定的 LOCO-LSGO audit chain：

```text
.env -> provider client -> chat API -> sanitized raw response
     -> raw_llm_output.json -> Stage 3.1 candidate replay
```

本阶段只证明 API adapter 和 audit chain 可以闭环，不证明 operator 有效，也不证明优化性能提升。

API 返回的 candidate 必须继续是 typed coordination operator AST wrapper，且 AST 只作用于 shared variables。

## 2. 环境变量

本阶段使用本地 `.env`，但 `.env` 被 `.gitignore` 忽略，不能提交。

可提交模板为 `.env.example`：

```text
LLM_API_KEY=
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-pro
LLM_REASONING_EFFORT=high
LLM_WIRE_API=chat
```

`LLM_API_KEY` 不能写入日志、artifact、文档或测试输出。

## 3. API Boundary

当前 adapter 支持：

```text
LLM_WIRE_API = chat
POST {LLM_BASE_URL}/chat/completions
```

请求只用于生成 `loco.stage3_1_raw_llm_batch.v1`。adapter 不执行 AST、不调用 objective function、不运行 evolution、不访问 validation/test feedback。

## 4. Artifacts

Stage 3.2 输出：

```text
artifacts/candidates/stage3_2/raw_response.json
artifacts/candidates/stage3_2/raw_llm_output.json
artifacts/candidates/stage3_2/accepted_candidates.jsonl
artifacts/candidates/stage3_2/rejected_candidates.jsonl
artifacts/candidates/stage3_2/replay_report.json
artifacts/candidates/stage3_2/smoke_report.json
```

`raw_response.json` 是 sanitized response，保留 provenance 和 token usage 等非 secret 信息，但省略 message content 并不包含 Authorization header 或 API key。

## 5. Current Smoke Result

当前真实 DeepSeek smoke：

```text
status = PASS
provider = deepseek
base_url_host = api.deepseek.com
model = deepseek-v4-pro
wire_api = chat
reasoning_effort = high
split = train
accepted_count = 1
rejected_count = 0
```

Stage 3.1 replay：

```text
status = PASS
split_violation_count = 0
test_feedback_violation_count = 0
execution_violation_count = 0
fingerprint_mismatch_count = 0
```

## 6. First Failed Attempt

第一次真实 API 调用成功返回了内容，但模型没有遵守 `loco.stage3_1_raw_llm_batch.v1` 与 `loco.llm_candidate.v1` 的完整 wrapper schema。Stage 3.1 replay 正确拒绝了该输出。

修复方式不是放宽 validator，而是强化 prompt：要求 JSON-only、固定 field names、固定 `stage = 3.1`、`split = train`、`ast.schema_version = loco.dsl.v1`，并在 chat request 中使用 JSON object response format。第二次 smoke 通过。

## 7. Claim Boundary

Stage 3.2 可以声明：

```text
LOCO can call a real chat-compatible LLM API once, save sanitized artifacts, and replay the returned train-only candidate batch through the existing Stage 3.1 audit chain.
```

Stage 3.2 不能声明：

```text
learned reusable coordination operators
evolution search success
operator performance improvement
SOTA optimization result
```
