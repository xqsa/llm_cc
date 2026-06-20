# Stage 2.5 Frozen AST Artifact Registry

创建日期：2026-06-20
执行者：Codex
阶段边界：只固化 frozen typed AST artifact、registry provenance 和 train/validation/test split boundary；不实现 LLM search、evolution、optimizer、controller/scheduler 或 operator discovery。

## 1. 阶段目标

Stage 2.4 已经证明 handwritten frozen AST 可以进入 synthetic conflict runner。Stage 2.5 进一步把这个 smoke operator 从 Python 内部模板升级为可审计 artifact：

```text
frozen operator artifact -> registry -> preflight -> FrozenASTRuntime -> synthetic conflict runner
```

这一步的研究意义不是性能提升，而是把未来 Stage 3 的 operator candidate 管理对象提前定义清楚：operator 必须是 data-only artifact，必须有 provenance，必须可 fingerprint，必须能被 split boundary 约束。

## 2. Artifact Registry

新增 registry：

```text
artifacts/operators/stage2_5_registry.jsonl
```

当前注册的 frozen artifact：

```text
artifacts/operators/stage2_5/frozen_ast_smoke_weighted_dampened_clip.json
```

artifact 记录：

- `artifact_schema_version = loco.operator_artifact.v1`；
- `artifact_id = stage2_5.frozen_ast_smoke.weighted_dampened_clip`；
- `operator_name = FrozenASTSmoke`；
- `source = handwritten_frozen_ast_template`；
- `target_scope = shared_variables_only`；
- `frozen = true`；
- `no_llm = true`；
- `no_evolution = true`；
- `no_test_feedback = true`；
- `test_mode_allowed = true`。

artifact fingerprint 使用 canonical JSON：

```text
json.dumps(payload, sort_keys=True, separators=(",", ":"))
sha256(encoded_utf8)
```

因此 artifact 内容变化会改变 fingerprint。

## 3. Split Boundary

Stage 2.5 明确区分：

```text
train / validation feedback: not used by this handwritten frozen artifact
test mode: allowed only because the artifact is already frozen
test feedback: forbidden
tuning on test: forbidden
```

这不是未来 Stage 3 的搜索协议本身，但它提前建立了 test-mode frozen-only 约束。未来 LLM/evolution search 产生的 candidate 只有在冻结并登记为 artifact 后，才允许进入 test-mode evaluation。

## 4. Runner Integration

`FrozenASTSmoke` 现在不再以 Python 内部模板作为事实源，而是：

```text
load frozen artifact
instantiate AST for current shared variable
run Stage 3 preflight
interpret with FrozenASTRuntime
emit artifact provenance in diagnostics
```

runner 输出新增：

```text
artifact_registry.enabled = true
artifact_registry.registry_path = artifacts/operators/stage2_5_registry.jsonl
FrozenASTSmoke.frozen_ast_runtime.artifact_id
FrozenASTSmoke.frozen_ast_runtime.artifact_fingerprint_sha256
FrozenASTSmoke.frozen_ast_runtime.no_test_feedback
```

## 5. FE Accounting

artifact loading、preflight、runtime interpretation 不调用 objective function：

```text
FE_coordination_extra = 0
```

每个 method 仍作为独立 run 汇报：

```text
budget_scope = per_method_run
cross_baseline_evaluations_shared = false
FE_commit_evaluation = 1
```

## 6. Claim Boundary

Stage 2.5 可以声明：

```text
LOCO can load a frozen typed AST from an auditable operator artifact registry and run it through the existing synthetic conflict runner with split-boundary provenance.
```

Stage 2.5 不能声明：

```text
learned reusable coordination operators
LLM-generated operator success
evolution search success
optimizer performance improvement
SOTA optimization result
```

## 7. 下一步

建议下一步是 Stage 2.6：candidate artifact logging schema and rejection corpus。

Stage 2.6 仍可不调用 LLM，只定义未来 LLM/evolution candidate 的 accepted/rejected artifact log schema、reject reasons、split fields 和 replay verifier。Stage 3 LLM candidate generation 应等待 artifact logging 和 no-test-feedback replay verifier 稳定后再启动。
