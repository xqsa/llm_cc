# Stage 3.1 Self-Check Report

创建日期：2026-06-20
执行者：Codex
阶段：Stage 3.1 small-batch LLM candidate generation

## Status

Stage 3.1 当前状态：PASS。

本阶段完成的是 train-only small-batch LLM candidate generation capture 和 audit，不是 evolution search，不是 objective evaluation，不是 performance claim。

## Artifacts

新增 artifacts：

- `configs/stage3_1_llm_candidate_batch.yaml`；
- `artifacts/candidates/stage3_1/raw_llm_output.json`；
- `artifacts/candidates/stage3_1/accepted_candidates.jsonl`；
- `artifacts/candidates/stage3_1/rejected_candidates.jsonl`；
- `artifacts/candidates/stage3_1/replay_report.json`；
- `docs/stage3/stage3_1_llm_candidate_batch.md`；
- `docs/stage3/stage3_1_self_check_report.md`；
- `loco/llm/candidate_batch.py`；
- `tests/stage3/test_stage3_1_llm_candidate_batch.py`。

## Replay Result

当前 replay report：

```text
schema_version = loco.stage3_1_candidate_replay.v1
stage = 3.1
status = PASS
split = train
accepted_count = 1
rejected_count = 2
split_violation_count = 0
test_feedback_violation_count = 0
execution_violation_count = 0
fingerprint_mismatch_count = 0
```

## Boundary Flags

Stage 3.1 保持：

- no evolution run；
- no objective evaluation；
- no optimizer generation；
- no scheduler/controller generation；
- no test feedback；
- no validation feedback；
- train-only；
- not a performance claim。

## PASS Criteria

Stage 3.1 PASS 要求：

- Stage 3.0 protocol lock report 为 PASS；
- raw LLM candidate batch 被记录；
- raw batch split 为 train；
- accepted/rejected logs 可 replay；
- accepted candidates 通过 typed coordination operator AST wrapper validation；
- accepted candidates 只作用于 shared variables；
- rejected candidates 保留明确 reject reasons；
- replay report status 为 PASS；
- Stage 3.1 tests pass；
- no evolution run、no objective evaluation、no test feedback。

## FAIL Criteria

任一情况出现即 Stage 3.1 FAIL：

- Stage 3.0 protocol lock 不是 PASS；
- raw batch 使用 validation/test split；
- candidate 绕过 typed AST wrapper；
- accepted candidate 作用于 non-shared variables；
- optimizer/controller/scheduler candidate 被 accepted；
- replay report 发现 split/test-feedback/execution/fingerprint violation；
- 文档把 Stage 3.1 误写成 performance success。

## Verification

本阶段验证命令：

```powershell
python -m black --check loco tests scripts
python -m pytest tests\stage3\test_stage3_0_protocol_lock.py tests\stage3\test_stage3_1_llm_candidate_batch.py -q
python -m pytest -p no:cacheprovider tests -q -rs
```

当前验证结果将在最终提交前刷新记录。
当前验证结果：

```text
black --check: PASS
Stage 3.0 + Stage 3.1 targeted tests: 18 passed
Full test suite: 144 passed
```
