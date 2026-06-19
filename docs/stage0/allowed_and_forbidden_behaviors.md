# Stage 0: Allowed and Forbidden Behaviors

生成日期：2026-06-19  
执行者：Codex

## 1. Stage 0 允许项

Stage 0 允许创建：

- research problem 文档；
- system boundary 文档；
- mathematical contract 文档；
- allowed/forbidden behavior 清单；
- acceptance checklist；
- reviewer risk analysis；
- implementation roadmap；
- boundary YAML 配置草案；
- typed contract 草案；
- boundary contract tests。

Stage 0 允许验证：

- 文件是否存在；
- contract 默认值是否禁止越界行为；
- LLM 输出是否被限定为 coordination operator AST；
- LOCO target 是否限定在 shared variables；
- LOCO 是否禁止访问 function id、benchmark name、true optimum location、test-set metadata、future evaluations 和 hidden test information；
- function evaluation ledger policy 是否声明所有额外 `f(x)` 调用计入预算；
- oracle grouping 和 detected grouping 是否在接口上分开。

## 2. Stage 0 禁止项

Stage 0 禁止：

- 实现完整优化算法；
- 实现 DE/CMA-ES/SHADE/CC/DECC 或其替代品；
- 实现 optimizer selection；
- 实现 scheduler/controller；
- 实现 LLM search/evolution loop；
- 调用 LLM API；
- 生成 benchmark；
- 运行真实 benchmark；
- 实现 coordination operators 的具体逻辑；
- 调参；
- 使用测试阶段结果宣称 performance improvement；
- 写入隐藏 fallback 来绕过边界；
- 将多指标 evaluation 描述成原始 multi-objective optimization；
- 将 oracle grouping 结果混入 detected grouping 报告；
- 不计入 LOCO 带来的额外 function evaluations。

## 3. LLM 行为边界

后续阶段中，LLM 只能生成 coordination operator AST。

合法 LLM 输出：

```text
CoordinationOperatorAST
```

非法 LLM 输出：

```text
Optimizer
Controller
Scheduler
Benchmark
ProblemGenerator
BaseOptReplacement
BudgetPolicy
GroupingOracle
ArbitraryExecutableCode
```

如果任一输出对象试图控制完整 optimization loop，必须判定为越界。

LLM 不能：

- generate optimizer；
- modify BaseOpt；
- generate scheduler/controller；
- select optimizer；
- access test feedback；
- tune on test set；
- generate arbitrary executable code outside typed AST。

## 4. LOCO 行为边界

LOCO 可以：

- 合并 shared variables 上的冲突更新；
- 为 shared-variable candidate updates 分配协调权重；
- 在冲突不确定时返回 no-op；
- 输出审计 metadata；
- 触发显式记录的 budget-consuming evaluation。

LOCO 不可以：

- 更新所有变量；
- 替代 BaseOpt 的搜索机制；
- 选择另一个 optimizer；
- 改变 evaluation budget 规则；
- 静默调用 `f(x)`；
- 使用未报告的 oracle grouping 信息；
- 访问 function id；
- 访问 benchmark name；
- 访问 true optimum location；
- 访问 test-set metadata；
- 访问 future evaluations；
- 访问 hidden test information；
- 在 no-overlap 场景中制造不必要干扰。

## 5. 测试阶段禁止项

Stage 0 测试阶段必须满足：

- frozen testing；
- `calls_llm = false`；
- `runs_evolution = false`；
- `tunes_parameters = false`；
- `generates_benchmark = false`；
- `runs_optimizer = false`；
- `claims_utility = false`。

任何测试如果需要真实 objective function 或 optimization runtime，都不属于 Stage 0。

## 6. 失败处理原则

如果发现越界行为，Stage 0 的正确处理是：

1. 明确标记失败；
2. 指出违反的 boundary item；
3. 不用 fallback 伪造成功；
4. 不把失败解释成 performance result；
5. 修正 contract 或文档后重新运行 boundary tests。
