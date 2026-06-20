# Stage 3.4 Self-Check Report

创建日期：2026-06-20
执行者：Codex
阶段：Stage 3.4 Candidate Quality Filter and Static Diversity Audit

## Status

Stage 3.4 当前状态：PASS。

本阶段完成的是 Stage 3.3 accepted candidate corpus 的静态质量过滤和多样性审计。它不是 LLM generation，不是 evolution run，不是 objective evaluation，不是 performance claim。

## Artifacts

新增 artifacts：

- `configs/stage3_4_static_candidate_audit.yaml`；
- `loco/llm/static_candidate_audit.py`；
- `scripts/stage3/run_stage3_4_static_candidate_audit.py`；
- `tests/stage3/test_stage3_4_static_candidate_audit.py`；
- `artifacts/candidates/stage3_4/quality_filter_report.json`；
- `artifacts/candidates/stage3_4/static_diversity_audit.json`；
- `artifacts/candidates/stage3_4/stage3_4_summary.json`；
- `docs/stage3/stage3_4_static_candidate_audit.md`；
- `docs/stage3/stage3_4_self_check_report.md`。

## Quality Filter Result

当前 `quality_filter_report.json`：

```text
schema_version = loco.stage3_4_quality_filter_report.v1
stage = 3.4
status = PASS
candidate_count = 9
quality_pass_count = 7
quality_reject_count = 2
issue_counts = {"single_consensus_only": 2}
```

解释：2 个 accepted candidates 虽然通过 Stage 3.1 boundary validator，但在 Stage 3.4 被标记为 single consensus-only，原因是它们只有 `weighted_consensus` 单节点，没有后续 transform/repair structure。

## Static Diversity Result

当前 `static_diversity_audit.json`：

```text
schema_version = loco.stage3_4_static_diversity_audit.v1
stage = 3.4
status = PASS
candidate_count = 9
unique_ast_fingerprint_count = 9
unique_kind_sequence_count = 2
dominant_kind_sequence = weighted_consensus->clip
dominant_kind_sequence_count = 7
low_diversity_warning = true
```

kind sequence distribution：

```text
weighted_consensus->clip = 7
weighted_consensus = 2
```

operator family distribution：

```text
weighted_consensus+clip = 7
weighted_consensus = 2
```

## Main Finding

Stage 3.4 的主要发现：

```text
Stage 3.3 的 9 个候选都通过了边界审计，但结构多样性偏低。
7/9 是 weighted_consensus->clip 变体。
2/9 是 single weighted_consensus，被 quality filter 标记为 single_consensus_only。
```

这说明当前 LLM candidate supply chain 可用，但 prompt/output guidance 还没有有效覆盖 projection、dampening、reweighting、repair 等更丰富的 coordination families。

## Boundary Flags

Stage 3.4 保持：

- no LLM call；
- no evolution run；
- no objective evaluation；
- no optimizer generation；
- no scheduler/controller generation；
- no validation feedback；
- no test feedback；
- not a performance claim。

## PASS Criteria

Stage 3.4 PASS 要求：

- 能读取 Stage 3.3 accepted candidate log；
- 能生成 quality filter report；
- 能生成 static diversity audit；
- 能诚实标记 low diversity；
- 能识别 weighted_consensus->clip dominant pattern；
- 不调用 LLM；
- 不运行 evolution；
- 不执行 AST；
- 不调用 objective；
- 不做 performance claim。

## Verification

本阶段验证命令：

```powershell
python -m black --check loco tests scripts
python -m pytest tests\stage3\test_stage3_4_static_candidate_audit.py -q
python -m pytest -p no:cacheprovider tests -q -rs
```

当前验证结果将在最终提交前刷新记录。
当前验证结果：

```text
black --check: PASS
Stage 3.4 targeted tests: 3 passed
Full test suite: 155 passed
Secret scan over Stage 3.4 artifacts: no matches for sk-, Authorization, Bearer, or LLM_API_KEY
```
