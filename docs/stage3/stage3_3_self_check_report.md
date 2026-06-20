# Stage 3.3 Self-Check Report

创建日期：2026-06-20
执行者：Codex
阶段：Stage 3.3 Train-only Multi-batch LLM Candidate Generation and Rejection-corpus Hardening

## Status

Stage 3.3 当前状态：PASS。

本阶段完成的是真实 DeepSeek-compatible chat API 的 train-only multi-batch candidate generation，并将多批模型返回合并后接入 Stage 3.1 replay、dedup report 和 rejection taxonomy。它不是 evolution run，不是 objective evaluation，不是 performance claim。

Stage 3.3 仍然只允许 typed coordination operator AST candidate，不允许 optimizer、scheduler、controller、optimizer selection 或 arbitrary executable code。

## Artifacts

新增 artifacts：

- `configs/stage3_3_multi_batch_candidate_generation.yaml`；
- `loco/llm/multibatch_candidate_generator.py`；
- `scripts/stage3/run_stage3_3_multi_batch.py`；
- `tests/stage3/test_stage3_3_multi_batch_candidate_generation.py`；
- `artifacts/candidates/stage3_3/raw_batches/raw_response_000.json`；
- `artifacts/candidates/stage3_3/raw_batches/raw_response_001.json`；
- `artifacts/candidates/stage3_3/raw_batches/raw_response_002.json`；
- `artifacts/candidates/stage3_3/raw_batches/raw_llm_output_000.json`；
- `artifacts/candidates/stage3_3/raw_batches/raw_llm_output_001.json`；
- `artifacts/candidates/stage3_3/raw_batches/raw_llm_output_002.json`；
- `artifacts/candidates/stage3_3/merged_raw_llm_output.json`；
- `artifacts/candidates/stage3_3/accepted_candidates.jsonl`；
- `artifacts/candidates/stage3_3/rejected_candidates.jsonl`；
- `artifacts/candidates/stage3_3/replay_report.json`；
- `artifacts/candidates/stage3_3/dedup_report.json`；
- `artifacts/candidates/stage3_3/rejection_taxonomy.json`；
- `artifacts/candidates/stage3_3/multi_batch_report.json`；
- `docs/stage3/stage3_3_multi_batch_candidate_generation.md`；
- `docs/stage3/stage3_3_self_check_report.md`。

## Multi-batch Result

当前 `multi_batch_report.json`：

```text
schema_version = loco.stage3_3_multi_batch_report.v1
stage = 3.3
status = PASS
api_called = true
api_call_count = 3
provider = deepseek
base_url_host = api.deepseek.com
model = deepseek-v4-pro
wire_api = chat
reasoning_effort = high
split = train
raw_candidate_count = 9
accepted_count = 9
unique_accepted_count = 9
duplicate_accepted_count = 0
rejected_count = 0
secret_redacted = true
```

当前 `replay_report.json`：

```text
schema_version = loco.stage3_1_candidate_replay.v1
status = PASS
split = train
accepted_count = 9
rejected_count = 0
split_violation_count = 0
test_feedback_violation_count = 0
execution_violation_count = 0
fingerprint_mismatch_count = 0
```

当前 `dedup_report.json`：

```text
status = PASS
accepted_count = 9
unique_accepted_count = 9
duplicate_accepted_count = 0
dedup_key = ast_fingerprint_sha256
```

当前 `rejection_taxonomy.json`：

```text
status = PASS
rejected_count = 0
categories = {}
```

真实 run 没有产生 rejected candidates；这不能解释为 LLM 输出“完美”，只能说明本次 9 个 candidates 都通过当前 Stage 3.1 validator。拒绝路径由 `tests/stage3/test_stage3_3_multi_batch_candidate_generation.py` 使用 fake chat server 覆盖。

## Secret Check

检查目标：

```text
artifacts/candidates/stage3_3/
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

Stage 3.3 保持：

- train-only；
- no evolution run；
- no objective evaluation；
- no optimizer generation；
- no scheduler/controller generation；
- no validation feedback；
- no test feedback；
- not a performance claim。

## PASS Criteria

Stage 3.3 PASS 要求：

- 真实 LLM API 被调用多次；
- 每批 raw output 都是 train-only；
- raw response 被 sanitized；
- merged raw output 可通过 Stage 3.1 replay；
- accepted/rejected logs 可复现；
- dedup report 记录 unique/duplicate accepted AST fingerprints；
- rejection taxonomy 记录拒绝类别，即使当前真实 run 为 zero-rejection；
- committed artifacts 不含 API key 或 Authorization header；
- no evolution run、no objective evaluation、no test feedback。

## Verification

本阶段验证命令：

```powershell
python -m black --check loco tests scripts
python -m pytest tests\stage3\test_stage3_3_multi_batch_candidate_generation.py -q
python -m pytest -p no:cacheprovider tests -q -rs
```

当前验证结果将在最终提交前刷新记录。
当前验证结果：

```text
black --check: PASS
Stage 3.3 targeted tests: 3 passed
Full test suite: 152 passed
Secret scan over Stage 3.3 committed artifacts: no matches for sk-, Authorization, Bearer, or LLM_API_KEY
```
