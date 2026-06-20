# Stage 3.2 Self-Check Report

创建日期：2026-06-20
执行者：Codex
阶段：Stage 3.2 Real LLM API Adapter Smoke

## Status

Stage 3.2 当前状态：PASS。

本阶段完成的是真实 DeepSeek-compatible chat API 的 adapter smoke，并将模型返回的 train-only candidate batch 接入 Stage 3.1 replay。它不是 evolution run，不是 objective evaluation，不是 performance claim。

Stage 3.2 仍然只允许 typed coordination operator AST candidate，不允许 optimizer、scheduler、controller 或 arbitrary executable code。

## Artifacts

新增 artifacts：

- `.env.example`；
- `configs/stage3_2_llm_api_smoke.yaml`；
- `loco/llm/provider_client.py`；
- `loco/llm/api_candidate_generator.py`；
- `tests/stage3/test_stage3_2_llm_api_smoke.py`；
- `artifacts/candidates/stage3_2/raw_response.json`；
- `artifacts/candidates/stage3_2/raw_llm_output.json`；
- `artifacts/candidates/stage3_2/accepted_candidates.jsonl`；
- `artifacts/candidates/stage3_2/rejected_candidates.jsonl`；
- `artifacts/candidates/stage3_2/replay_report.json`；
- `artifacts/candidates/stage3_2/smoke_report.json`；
- `docs/stage3/stage3_2_llm_api_smoke.md`；
- `docs/stage3/stage3_2_self_check_report.md`。

## Smoke Result

当前 `smoke_report.json`：

```text
schema_version = loco.stage3_2_api_smoke_report.v1
stage = 3.2
status = PASS
api_called = true
provider = deepseek
base_url_host = api.deepseek.com
model = deepseek-v4-pro
wire_api = chat
reasoning_effort = high
split = train
accepted_count = 1
rejected_count = 0
secret_redacted = true
```

当前 `replay_report.json`：

```text
schema_version = loco.stage3_1_candidate_replay.v1
status = PASS
split = train
accepted_count = 1
rejected_count = 0
split_violation_count = 0
test_feedback_violation_count = 0
execution_violation_count = 0
fingerprint_mismatch_count = 0
```

## Secret Check

检查目标：

```text
artifacts/candidates/stage3_2/raw_response.json
artifacts/candidates/stage3_2/raw_llm_output.json
artifacts/candidates/stage3_2/accepted_candidates.jsonl
```

禁止出现：

```text
sk-
Authorization
Bearer
LLM_API_KEY
```

当前检查结果：未发现上述 secret/header 字符串。

## Boundary Flags

Stage 3.2 保持：

- train-only；
- no evolution run；
- no objective evaluation；
- no optimizer generation；
- no scheduler/controller generation；
- no validation feedback；
- no test feedback；
- not a performance claim。

## PASS Criteria

Stage 3.2 PASS 要求：

- `.env` 被 git ignore；
- `.env.example` 可提交且不含 secret；
- 真实 LLM API 被调用一次；
- raw response 被 sanitized；
- raw LLM output 是 `loco.stage3_1_raw_llm_batch.v1`；
- Stage 3.1 replay report 为 PASS；
- accepted candidate 只作用于 shared variables；
- committed artifacts 不含 API key 或 Authorization header；
- no evolution run、no objective evaluation、no test feedback。

## Verification

本阶段验证命令：

```powershell
python -m black --check loco tests scripts
python -m pytest tests\stage3\test_stage3_2_llm_api_smoke.py -q
python -m pytest -p no:cacheprovider tests -q -rs
```

当前验证结果将在最终提交前刷新记录。
当前验证结果：

```text
black --check: PASS
Stage 3.2 targeted tests: 5 passed
Full test suite: 149 passed
Secret scan over Stage 3.2 committed artifacts: no matches for sk-, Authorization, Bearer, or LLM_API_KEY
```
