# Stage 2.2 Typed Coordination Operator DSL Boundary

创建日期：2026-06-20
执行者：Codex
阶段边界：只定义 typed coordination operator AST 的 schema、验证规则和安全边界；不实现 LLM search、evolution、optimizer、controller/scheduler、benchmark 或 coordination operator discovery。

## 1. 阶段目标

Stage 2.2 的目标是把 LOCO-LSGO 后续 LLM 输出边界从文字约束变成可测试接口：

```text
LLM allowed output = typed coordination operator AST
```

这里的 typed coordination operator AST 是数据结构，不是 Python source code，也不是可执行函数。它只描述 coordination operator 的受限组合结构，供后续阶段在独立 runtime 中解释或筛选。

Stage 2.2 不发现新 operator，不执行 operator，不调用 LLM，不运行 evolution，也不实现 optimizer。

## 2. 与 LOCO-LSGO 核心问题的关系

LOCO-LSGO 的核心问题仍然是：

```text
shared-variable conflict -> coordination operator -> more stable cooperative coevolution
```

Stage 2.2 只锁定 coordination operator 的表达边界。该边界确保未来 LLM + evolution 只能探索作用于 shared variables 的 conflict coordination mechanism，而不能转向生成全局优化器、scheduler/controller 或 optimizer selector。

## 3. AST 输入输出契约

AST 的输入范围：

- 只允许接收 shared-variable conflict state；
- 只允许引用 shared variables；
- target variable 必须属于当前 `shared_variables` 集合；
- validation 不允许产生额外 function evaluations，`validation_extra_fe = 0`。

AST 的输出范围：

- 输出 typed coordination operator AST；
- AST 使用固定 `schema_version = loco.dsl.v1`；
- AST 的 serialization 必须 deterministic，便于 hash、review 和 frozen artifact 记录；
- AST validation 只返回 schema/report，不提交优化步骤。

## 4. 允许的 node kinds

Stage 2.2 允许的 node kinds 是 coordination-only primitives：

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

这些名字只表达 shared-variable proposal coordination 的局部机制，不表示完整 optimizer，也不表示 BaseOpt 的替换。

## 5. 明确禁止项

Stage 2.2 明确禁止：

- no LLM；
- no evolution；
- no optimizer；
- no controller/scheduler；
- no optimizer selection；
- no arbitrary executable code；
- no Python source code generation；
- no BaseOpt modification；
- no benchmark objective mutation；
- no MetaBox source mutation；
- no test-set tuning。

AST 不能包含 optimizer/controller/scheduler 相关 node kinds，例如：

```text
optimizer
de_optimizer
cma_es_optimizer
pso_optimizer
shade_optimizer
lshade_optimizer
controller
scheduler
optimizer_selection
base_optimizer_replacement
```

## 6. 禁止访问的信息

AST 不能访问或请求：

- `function_id`；
- `benchmark_name`；
- `true_optimum_location`；
- `test_set_metadata`；
- `future_evaluations`；
- `hidden_test_information`。

这些字段会被 loader/validator 视为 forbidden metadata access。它们不能出现在 node inputs、target 或任何嵌套字段中。

## 7. 代码执行边界

Stage 2.2 的 AST 是 data-only schema。AST 中禁止出现 arbitrary executable code，包括：

- `lambda`；
- `def ...`；
- `class ...`；
- `import ...`；
- `eval(...)`；
- `exec(...)`；
- `__import__(...)`；
- `subprocess`；
- `.system(...)`。

包含 `code` 或 `callable` 的字段名也会被拒绝。这样做是为了确保未来 LLM 不能绕过 typed AST，直接生成任意 Python 逻辑。

## 8. 规模限制

Stage 2.2 默认安全限制：

- `max_nodes = 32`；
- `max_depth = 8`；
- node id 必须唯一；
- output source 必须指向已存在 node；
- source graph 不允许 cycle；
- target variables 必须是 shared variables 子集。

这些限制不是性能优化，而是 reviewability 和 boundary control 的一部分。

## 9. 与 Stage 3 的关系

Stage 2.2 是 Stage 3 前的 hard gate。未来 Stage 3 若进入 LLM candidate generation，LLM 只能生成符合本 DSL 的 typed coordination operator AST。

Stage 3 仍应继续保持：

- LLM 不生成 optimizer；
- LLM 不生成 scheduler/controller；
- LLM 不选择 optimizer；
- 测试阶段 frozen：no LLM / no evolution / no tuning；
- 所有额外 function evaluations 必须纳入 FE accounting。

## 10. 当前结论

Stage 2.2 的完成标准不是发现更好 coordination operator，而是证明项目已经有一个可测试、可审计、可冻结的 typed AST boundary。

该边界直接服务于论文防护：LOCO-LSGO 的创新是学习 shared-variable conflict coordination operator，不是让 LLM 编写优化器。
