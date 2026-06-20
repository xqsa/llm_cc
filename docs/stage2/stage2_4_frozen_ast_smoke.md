# Stage 2.4 Frozen AST Smoke Integration

创建日期：2026-06-20
执行者：Codex
阶段边界：只把 handwritten frozen typed AST smoke operator 接入现有 synthetic conflict runner；不实现 LLM search、evolution、optimizer、controller/scheduler 或 operator discovery。

## 1. 阶段目标

Stage 2.4 的目标是验证 Stage 2.2/2.3 形成的 typed AST boundary 和 runtime shell 能进入现有 Stage 2 synthetic conflict runner：

```text
existing synthetic conflict runner + handwritten frozen AST -> audited smoke result
```

这一步不是性能实验，也不是 learned operator 证据。它只证明 frozen AST runtime 可以在已有 proposal / conflict-state / FE accounting loop 中运行。

## 2. Frozen AST Smoke Operator

新增 smoke operator：

```text
FrozenASTSmoke
```

它使用 handwritten frozen AST template：

```text
weighted_consensus -> dampening -> clip
```

对每个 shared variable，template 被确定性实例化为目标变量对应的 typed AST，然后由 `FrozenASTRuntime` 解释。该过程：

- 不调用 LLM；
- 不运行 evolution；
- 不生成新 AST search candidate；
- 不调用 objective function；
- 不修改 BaseOpt；
- 不访问 benchmark metadata；
- 不修改 benchmark objective 或 MetaBox source。

## 3. Runner Integration

`loco.experiments.stage2_minimal_runner` 现在在原有 5 个 baseline method runs 后加入：

```text
FrozenASTSmoke
```

当前 runner method list：

```text
NoCoordination
AverageConsensus
BestRewardSelection
WeightedConsensus
ConflictDampening
FrozenASTSmoke
```

每个 method 仍作为独立 run 计费：

```text
budget_scope = per_method_run
cross_baseline_evaluations_shared = false
FE_commit_evaluation = 1
```

`FrozenASTSmoke` 的 runtime 本身不产生额外 objective evaluation：

```text
FE_coordination_extra = 0
```

## 4. 输出 Artifact

默认脚本：

```powershell
python loco\experiments\stage2_minimal_runner.py
```

输出：

```text
docs/stage2/stage2_4_frozen_ast_smoke_result.json
```

result JSON 中记录：

- `frozen_ast_smoke.enabled = true`；
- handwritten template source；
- no LLM / no evolution / no optimizer flags；
- `FrozenASTSmoke` 的 `frozen_ast_runtime` metadata；
- 每个 shared variable 的 DSLRuntime diagnostics trace。

## 5. Claim Boundary

Stage 2.4 可以声明：

```text
A handwritten frozen typed AST can run through the existing synthetic conflict runner with audited FE accounting.
```

Stage 2.4 不能声明：

```text
learned reusable coordination operators
LLM-generated operator success
evolution search success
optimizer performance improvement
SOTA optimization result
```

## 6. 下一步

建议下一步是 Stage 2.5：frozen AST artifact registry and train/validation/test boundary hardening。

Stage 2.5 仍应使用 handwritten / frozen AST，不进入 LLM search 或 evolution。Stage 3 前必须先固定 AST artifact provenance、split policy、logging schema 和 no-test-feedback boundary。
