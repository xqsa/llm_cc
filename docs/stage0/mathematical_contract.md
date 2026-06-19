# Stage 0: Mathematical Contract

生成日期：2026-06-19  
执行者：Codex

## 1. 基本符号

| 符号 | 含义 |
|---|---|
| `D` | 决策变量维度 |
| `x in R^D` | 决策向量 |
| `Omega subset R^D` | 可行域 |
| `f: Omega -> R` | 单目标 objective function |
| `V = {1, ..., D}` | 变量索引全集 |
| `G_j subset V` | 第 `j` 个子组件变量集合 |
| `G = {G_1, ..., G_M}` | grouping 结果 |
| `m_i` | 变量 `i` 的 group membership count |
| `S = {i | m_i >= 2}` | shared variable set |
| `B` | function evaluation budget |
| `BaseOpt` | 固定基础优化器 |
| `O_theta` | LOCO coordination operator |
| `s_i^t` | 第 `t` 步 shared variable `i` 的 conflict/proposal state |

原始优化问题：

```text
min_{x in Omega} f(x)
```

该问题是单目标优化。所有 Stage 0 文档、配置和接口都必须保持这个定义。

## 2. Overlap 与 shared variables

变量 `i` 的 group membership count 定义为：

```text
m_i = |{j in {1, ..., M} | i in G_j}|
```

shared variables 定义为：

```text
S = {i in V | m_i >= 2}
```

non-shared variables 定义为：

```text
V_nonshared = V \ S
```

LOCO operator 的合法作用域：

```text
scope(O_theta) subset S
O_theta: s_i^t -> x_i^{t+1}, for i in S
```

## 3. Overlap graph 草案

可以用 overlap graph 表示子组件冲突：

```text
H = (G_nodes, E_overlap)
G_nodes = {1, ..., M}
E_overlap = {(a, b) | a != b and G_a cap G_b != empty}
```

其中 edge weight 可以记录：

```text
w_ab = |G_a cap G_b|
```

Stage 0 只定义该图的概念接口，不实现 graph construction 或 graph algorithm。

## 4. Coordination operator 输入契约

一个合法的 LOCO coordination operator `O_theta` 在后续阶段可以接收以下信息：

- shared variable indices: `I subset S`；
- current incumbent vector or projected view: `x_I`；
- candidate updates from BaseOpt on affected groups；
- conflict metadata derived without extra hidden function evaluations；
- local trace summary that does not reveal forbidden oracle-only labels unless experiment mode explicitly declares oracle grouping；
- budget ledger state。

非法输入包括：

- 直接替换 BaseOpt 所需的 optimizer code；
- scheduler/controller state that controls the full optimization loop；
- unreported oracle grouping labels in detected grouping mode；
- uncounted objective probes；
- benchmark generator internals；
- test-set leakage。

LOCO 不能访问以下信息，即使这些信息存在于 benchmark wrapper 或实验 metadata 中：

- function id；
- benchmark name；
- true optimum location；
- test-set metadata；
- future evaluations；
- hidden test information。

## 5. Coordination operator 输出契约

一个合法的 LOCO coordination operator 输出的是 shared variables 的协调结果，例如：

- accepted update for `I subset S`；
- conflict weight for competing updates；
- merge decision among BaseOpt-proposed shared-variable updates；
- no-op decision when conflict is absent or uncertain；
- budget-neutral metadata for audit。

输出必须满足：

```text
updated_indices subset S
```

不允许输出：

- full candidate solution generator；
- complete optimizer step for all variables；
- optimizer selection decision；
- scheduler/controller command；
- new benchmark instance；
- hidden objective value correction。

## 6. Budget accounting

设总预算为 `B`，到时间 `t` 已使用 function evaluations 为 `FE_t`。

每一次调用 `f(x)` 都必须满足：

```text
FE_{t+1} = FE_t + 1
FE_{t+1} <= B
```

LOCO 带来的额外 function evaluations 也必须计入：

```text
FE_total = FE_grouping + FE_proposal + FE_coordination_extra + FE_repair
```

其中：

- `FE_grouping` 包含 grouping / overlap detection 中调用 `f(x)` 的次数；
- `FE_proposal` 包含固定 BaseOpt 产生 candidate proposals 所调用 `f(x)` 的次数；
- `FE_coordination_extra` 包含 operator selection、operator validation、conflict probing 或 tie-breaking 额外调用 `f(x)` 的次数；
- `FE_repair` 包含 feasibility repair、invalid proposal repair 或 post-coordination repair 中调用 `f(x)` 的次数。

Stage 0 的测试不应调用 `f(x)`，因此只验证 ledger policy 的声明是否为 `count_all_extra_function_evaluations`。

## 7. Evaluation metric 边界

外层 evaluation 可以使用多个指标：

```text
M = {M_1, M_2, ..., M_q}
```

这些指标用于评价 `O_theta`，但不改变原始问题：

```text
min_{x in Omega} f(x)
```

因此文稿中必须避免以下误写：

- “LOCO solves a multi-objective optimization problem”；
- “the original objective is a vector objective”；
- “operator search metrics redefine f”。

正确表述是：

- “The original problem is single-objective optimization; multiple metrics are used only in the outer operator evaluation protocol.”
