# Stage 2.3 DSL Interpreter Runtime Shell

创建日期：2026-06-20
执行者：Codex
阶段边界：只解释 frozen typed AST 到 shared-variable coordination behavior；不实现 LLM search、evolution、optimizer、controller/scheduler、benchmark objective evaluation 或 operator discovery。

## 1. 阶段目标

Stage 2.3 的目标是把 Stage 2.2 已冻结的 typed coordination operator AST，解释为一个局部 coordination runtime shell：

```text
validated frozen typed AST + SharedVariableConflictState -> CoordinationResult
```

这里的 runtime shell 只处理单个 shared variable 的 conflict state。它不访问 benchmark objective，不生成 group proposals，不修改 BaseOpt，不控制 optimizer，也不选择 optimizer。

## 2. 输入输出契约

输入：

- 一个通过 Stage 2.2 preflight 的 frozen typed AST；
- 一个 `SharedVariableConflictState`；
- 当前 shared variables 集合。

输出：

- `CoordinationResult`；
- `variable_id` 必须等于输入 conflict state 的 shared variable；
- `coordinated_value` 必须经过 bounds clipping；
- `extra_fe = 0`；
- diagnostics 中包含 deterministic trace。

## 3. 支持的 node kinds

Stage 2.3 runtime shell 支持 Stage 2.2 已允许的 coordination-only primitives：

```text
consensus
weighted_consensus
best_reward_select
projection
dampening
reweighting
clip
repair
```

这些 primitives 只解释 shared-variable proposals、rewards、current value 和 bounds。它们不是 optimizer，也不创建新的 objective evaluations。

## 4. 明确禁止项

Stage 2.3 明确保持：

- no LLM；
- no evolution；
- no optimizer；
- no controller/scheduler；
- no optimizer selection；
- no BaseOpt modification；
- no benchmark objective mutation；
- no MetaBox source mutation；
- no arbitrary executable code；
- no objective evaluation。

## 5. FE Accounting

Stage 2.3 runtime validation 和 coordination interpretation 都不调用 `f(x)`：

```text
runtime_extra_fe = 0
```

如果未来某个 AST primitive 需要 objective evaluation，该 primitive 不属于当前 Stage 2.3 runtime shell，必须在后续阶段单独设计并计入：

```text
FE_coordination_extra
```

## 6. 与 Stage 3 的关系

Stage 2.3 仍不是 Stage 3。它只证明：

```text
frozen typed AST can be interpreted into bounded shared-variable coordination behavior
```

未来 Stage 3 若进入 LLM/evolution search，只能产生 Stage 2.2 可接受、Stage 2.3 可解释的 typed AST。测试阶段仍必须 frozen：no LLM / no evolution / no tuning。

## 7. 当前结论

Stage 2.3 的完成标准不是找到更好的 coordination operator，而是提供一个可测试、可审计、无 objective evaluation 的 runtime shell。

它让 LOCO-LSGO 的下一步从“有 AST schema”推进到“frozen AST 可以被安全解释”，但仍不构成 learned operator、optimizer improvement 或 SOTA claim。
