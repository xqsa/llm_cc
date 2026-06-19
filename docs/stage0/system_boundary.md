# Stage 0: System Boundary Definition

生成日期：2026-06-19  
执行者：Codex

## 1. 系统边界总览

LOCO-LSGO 的系统由五层组成：

1. Problem layer：定义原始单目标优化问题 `min_{x in Omega} f(x)`。
2. Grouping layer：提供 oracle grouping 或 detected grouping。
3. BaseOpt layer：固定基础优化器 BaseOpt，负责产生候选更新或局部搜索行为。
4. LOCO layer：只对 shared variables 应用 coordination operator。
5. Evaluation layer：记录 objective、budget、grouping mode、overlap regime 和 regression guard。

Stage 0 只定义这些层之间的契约，不实现任何一层的完整运行时逻辑。

## 2. LOCO 的唯一作用域

LOCO 只作用于 shared variables。

设变量索引全集为：

```text
V = {1, 2, ..., D}
```

设 grouping 产生的子组件变量集合为：

```text
G = {G_1, G_2, ..., G_M}, where G_j subset V
```

shared variables 定义为：

```text
S = {i in V | m_i >= 2}
m_i = |{j | i in G_j}|
```

LOCO coordination operator 的合法 target scope 必须满足：

```text
target(operator) subset S
O_theta: s_i^t -> x_i^{t+1}, only for i in S
```

非 shared variables 的更新仍由固定 BaseOpt 或既有 cooperative coevolution 流程处理。LOCO 不接管完整优化过程。

## 3. LLM 输出边界

LLM 在后续阶段最多只能生成 coordination operator AST。

LLM 允许输出的对象：

- operator name；
- operator AST；
- shared-variable target declaration；
- operator-local parameters 的有限声明；
- input/output schema version；
- safety annotations。

LLM 禁止输出的对象：

- optimizer；
- controller；
- scheduler；
- BaseOpt replacement；
- benchmark；
- evaluation harness；
- problem generator；
- budget policy；
- grouping oracle；
- result postprocessor that changes objective values。

LLM 也禁止：

- generate optimizer；
- modify BaseOpt；
- generate scheduler/controller；
- select optimizer；
- access test feedback；
- tune on test set；
- generate arbitrary executable code outside typed AST。

Stage 0 测试阶段不调用 LLM。

## 4. LOCO 信息访问边界

LOCO operator 与 LLM-generated typed AST 不得访问以下信息：

- function id；
- benchmark name；
- true optimum location；
- test-set metadata；
- future evaluations；
- hidden test information。

这些信息只能出现在离线审计或最终报告的外部 metadata 中，不能作为 operator 输入、condition、prompt feature 或 selection feature。

## 5. BaseOpt 固定原则

BaseOpt 必须固定。

LOCO 的比较不能通过换用更强 optimizer 获得优势。任何实验比较必须保持：

- 相同 BaseOpt family；
- 相同 BaseOpt implementation；
- 相同主要 hyperparameters；
- 相同 initialization protocol；
- 相同 function evaluation budget accounting；
- 相同 problem set 与 seed policy。

如果后续阶段必须更换 BaseOpt，则该变更必须作为新的实验分支单独报告，不能与 LOCO operator utility 混合归因。

## 6. Grouping 报告边界

oracle grouping 与 detected grouping 必须分开报告。

- oracle grouping：使用真实或构造已知的 group/overlap structure。
- detected grouping：使用算法检测得到的 group/overlap structure。

报告中必须至少分开标注：

- grouping mode；
- overlap density；
- shared-variable count；
- grouping error 或 uncertainty；
- LOCO operator 是否依赖 oracle-only information。

任何使用 oracle grouping 得到的结果，不得直接替代 detected grouping 结论。

## 7. Budget 边界

所有额外 function evaluations 必须计入预算。

正式记账分解为：

```text
FE_total = FE_grouping + FE_proposal + FE_coordination_extra + FE_repair
```

其中：

- `FE_grouping`：grouping 或 overlap detection 需要调用 `f(x)` 时产生的预算；
- `FE_proposal`：固定 BaseOpt 产生 candidate proposals 时使用的预算；
- `FE_coordination_extra`：LOCO 为 conflict probing、operator scoring 或 tie-breaking 额外调用 `f(x)` 的预算；
- `FE_repair`：为了修复非法或不可行 proposal 而调用 `f(x)` 的预算。

包括但不限于：

- conflict probing；
- operator scoring；
- validation re-evaluation；
- ablation re-check；
- grouping verification；
- restart selection；
- tie-breaking that evaluates `f(x)`。

允许不计入 objective budget 的操作仅限不调用 `f(x)` 的纯结构检查，例如 AST schema validation、索引集合检查和静态配置检查。

## 8. Testing 边界

Stage 0 testing 只验证边界契约。

Stage 0 测试必须满足：

- frozen testing；
- 不调用 LLM；
- 不运行 evolution；
- 不调参；
- 不生成 benchmark；
- 不运行完整 optimizer；
- 不宣称 performance improvement；
- 只检查 contract、config 与禁止项。

## 9. No-overlap / Low-overlap 边界

LOCO 面向 overlapping LSGO，但必须在 no-overlap 或 low-overlap 场景下设置 regression guard。

最低要求：

- no-overlap 时，LOCO 应退化为 no-op 或等价安全路径；
- low-overlap 时，LOCO 不应明显干扰 BaseOpt；
- 报告中必须单独列出 no-overlap / low-overlap 结果；
- 如果这些场景明显退化，不能声称 operator reusable。
