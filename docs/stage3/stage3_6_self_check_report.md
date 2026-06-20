# Stage 3.6 Self-Check Report

创建日期：2026-06-20
执行者：Codex
阶段：Stage 3.6 Freeze Quality-pass Candidate Pool and Prepare Train-only Evolution/Search Protocol

## Status

Stage 3.6 当前状态：PASS。

本阶段完成的是 Stage 3.5 quality-pass candidate pool 的冻结，以及 Stage 4 train-only evolution/search protocol 的准备。它不是 evolution run，不是 objective evaluation，不是 performance claim。

## Artifacts

新增 artifacts：

- `configs/stage3_6_freeze_candidate_pool.yaml`；
- `loco/llm/freeze_candidate_pool.py`；
- `scripts/stage3/run_stage3_6_freeze_candidate_pool.py`；
- `tests/stage3/test_stage3_6_freeze_candidate_pool.py`；
- `artifacts/candidates/stage3_6/frozen_candidate_pool.jsonl`；
- `artifacts/candidates/stage3_6/frozen_pool_manifest.json`；
- `artifacts/candidates/stage3_6/candidate_family_descriptors.json`；
- `artifacts/candidates/stage3_6/train_only_search_protocol.json`；
- `artifacts/candidates/stage3_6/freeze_report.json`；
- `docs/stage3/stage3_6_freeze_candidate_pool.md`；
- `docs/stage3/stage3_6_self_check_report.md`。

## Freeze Result

当前 `freeze_report.json`：

```text
schema_version = loco.stage3_6_freeze_report.v1
stage = 3.6
status = PASS
source_stage = 3.5
frozen_candidate_count = 12
quality_pass_only = true
family_count = 8
candidate_pool_frozen = true
train_only_search_protocol_prepared = true
```

当前 `train_only_search_protocol.json`：

```text
status = READY_FOR_STAGE4_TRAIN_ONLY_SEARCH
allowed_split = train
validation_usage = selection only after train search
test_usage = sealed final reporting only
candidate_pool_frozen = true
frozen_candidate_count = 12
```

## Boundary Flags

Stage 3.6 保持：

- no LLM call；
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
artifacts/candidates/stage3_6/
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
python -m pytest tests\stage3\test_stage3_6_freeze_candidate_pool.py -q
python -m pytest -p no:cacheprovider tests -q -rs
```

当前验证结果：

```text
python -m black --check loco tests scripts
=> PASS, 83 files would be left unchanged

python -m pytest tests\stage3\test_stage3_6_freeze_candidate_pool.py -q
=> PASS, 3 passed in 0.10s

python -m pytest -p no:cacheprovider tests -q -rs
=> PASS, 161 passed in 7.66s
```

Secret scan：

```powershell
Get-ChildItem artifacts\candidates\stage3_6 -Recurse -File | Select-String -Pattern "sk-|Authorization|Bearer|LLM_API_KEY"
```

当前结果：无输出，未发现 `sk-`、`Authorization`、`Bearer` 或 `LLM_API_KEY`。
