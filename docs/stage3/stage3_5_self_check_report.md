# Stage 3.5 Self-Check Report

创建日期：2026-06-20
执行者：Codex
阶段：Stage 3.5 Prompt-space Hardening for Broader Coordination Operator Family Coverage

## Status

Stage 3.5 当前状态：PASS。

本阶段完成的是 hardened prompt 下的 train-only multi-batch LLM candidate generation，并通过 coverage gate 验证更广的 coordination family 覆盖。它不是 evolution run，不是 objective evaluation，不是 performance claim。

## Artifacts

新增 artifacts：

- `configs/stage3_5_prompt_space_hardening.yaml`；
- `loco/llm/prompt_space_hardening.py`；
- `scripts/stage3/run_stage3_5_prompt_space_hardening.py`；
- `tests/stage3/test_stage3_5_prompt_space_hardening.py`；
- `artifacts/candidates/stage3_5/raw_batches/raw_response_000.json`；
- `artifacts/candidates/stage3_5/raw_batches/raw_response_001.json`；
- `artifacts/candidates/stage3_5/raw_batches/raw_response_002.json`；
- `artifacts/candidates/stage3_5/raw_batches/raw_llm_output_000.json`；
- `artifacts/candidates/stage3_5/raw_batches/raw_llm_output_001.json`；
- `artifacts/candidates/stage3_5/raw_batches/raw_llm_output_002.json`；
- `artifacts/candidates/stage3_5/merged_raw_llm_output.json`；
- `artifacts/candidates/stage3_5/accepted_candidates.jsonl`；
- `artifacts/candidates/stage3_5/rejected_candidates.jsonl`；
- `artifacts/candidates/stage3_5/replay_report.json`；
- `artifacts/candidates/stage3_5/quality_filter_report.json`；
- `artifacts/candidates/stage3_5/static_diversity_audit.json`；
- `artifacts/candidates/stage3_5/coverage_gate_report.json`；
- `artifacts/candidates/stage3_5/stage3_5_summary.json`；
- `docs/stage3/stage3_5_prompt_space_hardening.md`；
- `docs/stage3/stage3_5_self_check_report.md`。

## Coverage Gate Result

当前 `coverage_gate_report.json`：

```text
status = PASS
api_call_count = 3
raw_candidate_count = 12
accepted_count = 12
quality_pass_count = 12
unique_kind_sequence_count = 8
operator_family_count = 8
dominant_kind_sequence = projection->dampening
dominant_kind_sequence_count = 3
dominant_ratio = 0.25
```

required node kind coverage：

```text
projection = true
dampening = true
reweighting = true
repair = true
best_reward_select = true
```

## Boundary Flags

Stage 3.5 保持：

- train-only；
- no evolution run；
- no objective evaluation；
- no optimizer generation；
- no scheduler/controller generation；
- no validation feedback；
- no test feedback；
- not a performance claim。

## Secret Check

检查目标：

```text
artifacts/candidates/stage3_5/
```

禁止出现：

```text
sk-
Authorization
Bearer
LLM_API_KEY
```

当前检查结果：未发现上述 secret/header 字符串。

## Verification

本阶段验证命令：

```powershell
python -m black --check loco tests scripts
python -m pytest tests\stage3\test_stage3_5_prompt_space_hardening.py -q
python -m pytest -p no:cacheprovider tests -q -rs
```

当前验证结果将在最终提交前刷新记录。
当前验证结果：

```text
black --check: PASS
Stage 3.5 targeted tests: 3 passed
Full test suite: 158 passed
Secret scan over Stage 3.5 artifacts: no matches for sk-, Authorization, Bearer, or LLM_API_KEY
```
