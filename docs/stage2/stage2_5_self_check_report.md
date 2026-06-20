# Stage 2.5 Self Check Report

创建日期：2026-06-20
执行者：Codex
阶段：Frozen AST Artifact Registry and Split Boundary Hardening

## 1. Scope

本阶段只把 Stage 2.4 的 handwritten frozen typed AST smoke operator 固化为 registry-managed artifact。它不是 LLM search，不是 evolution，不是 optimizer runtime，也不是 operator discovery。

明确边界：

- no LLM；
- no evolution；
- no optimizer；
- no controller/scheduler；
- no objective evaluation inside DSL runtime；
- no arbitrary executable code；
- no test feedback；
- no tuning on test；
- no benchmark objective mutation；
- no BaseOpt modification；
- no MetaBox source mutation。

## 2. Artifacts

新增 / 更新核心文件：

- `artifacts/operators/stage2_5_registry.jsonl`：frozen operator artifact registry。
- `artifacts/operators/stage2_5/frozen_ast_smoke_weighted_dampened_clip.json`：handwritten frozen AST artifact。
- `loco/coordination/operator_artifacts.py`：artifact loading、fingerprint、provenance validation、template instantiation。
- `loco/coordination/frozen_ast_smoke.py`：从 artifact registry 加载 `FrozenASTSmoke`。
- `loco/experiments/stage2_minimal_runner.py`：输出 Stage 2.5 artifact registry provenance。
- `configs/stage2_5_artifact_registry.yaml`：Stage 2.5 配置草案。
- `docs/stage2/stage2_5_artifact_registry.md`：中文边界说明。
- `docs/stage2/stage2_5_artifact_registry_result.json`：smoke result artifact。
- `tests/stage2/test_stage2_5_artifact_registry.py`：artifact registry 与 split boundary tests。

## 3. Boundary Checks

| 检查项 | 状态 | 说明 |
| --- | --- | --- |
| frozen artifact exists and is registered | PASS | registry 指向 `stage2_5.frozen_ast_smoke.weighted_dampened_clip`。 |
| deterministic artifact fingerprint | PASS | artifact canonical JSON sha256 长度为 64。 |
| artifact mutation changes fingerprint | PASS | 修改 AST 内容会改变 fingerprint。 |
| unfrozen artifact rejected | PASS | `provenance.frozen=false` 会被拒绝。 |
| test feedback rejected | PASS | `split_policy.no_test_feedback=false` 会被拒绝。 |
| shared-variable-only scope | PASS | artifact `target_scope=shared_variables_only`。 |
| runner provenance | PASS | result JSON 记录 registry path、artifact id、fingerprint 和 no-test-feedback flags。 |
| FE accounting unchanged by runtime | PASS | `FrozenASTSmoke.FE_coordination_extra = 0`。 |
| no LLM/evolution imports | PASS | tests 覆盖 no LLM / no evolution imports。 |
| Stage 2.1 not polluted | PASS | `_run_problem()` 默认 baseline-only，Stage 2.1 panel 仍为 5 operators。 |

## 4. Claim Boundary

Stage 2.5 可以声明：

```text
LOCO can load and run a frozen typed AST from an auditable artifact registry with explicit split-boundary provenance.
```

Stage 2.5 不能声明：

```text
learned reusable coordination operators
LLM-generated operator success
evolution search success
optimizer performance improvement
SOTA optimization result
```

## 5. Next Stage

建议下一步是 Stage 2.6：candidate artifact logging schema and rejection corpus。

Stage 2.6 的重点应是 accepted/rejected candidate artifact logs、reject reason taxonomy、replay verifier 和 no-test-feedback audit，而不是进入 LLM/evolution search。
