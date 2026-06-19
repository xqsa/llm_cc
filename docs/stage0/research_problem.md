# Stage 0: Research Problem Locking

生成日期：2026-06-19  
执行者：Codex  
项目暂名：LOCO-LSGO, LLM-Evolved Coordination Operators for Overlapping Large-Scale Global Optimization

## 1. 核心研究问题

LOCO-LSGO 的核心研究问题是：

> Can we learn reusable coordination operators that resolve shared-variable conflicts in overlapping large-scale global optimization problems?

中文表述：

> 能否学习一组可复用的 coordination operators，用于解决 overlapping LSGO 中 shared variables 的冲突问题？

这里的 reusable 指 operator 不应只记住某一个 problem instance 或某一次 grouping 结果，而应在同一类 overlap structure、shared-variable conflict pattern 或 optimization trace condition 下保持可复用的行为接口。

## 2. 原始优化问题

原始优化问题是 single-objective LSGO：

```text
minimize f(x), x in Omega
```

记为：

```text
min_{x in Omega} f(x)
```

其中：

- `x = (x_1, ..., x_D)` 是 D 维决策变量。
- `f: Omega -> R` 是单个标量 objective function。
- `Omega` 是可行域，通常由变量上下界或简单约束定义。
- 本项目 Stage 0 不引入原始问题的 multi-objective formulation。

## 3. 外层 operator search 与多指标评价的边界

LOCO 可以在外层 operator selection/search 中使用多个评价指标，例如：

- final error；
- conflict intensity；
- oscillation；
- FE overhead；
- generalization across problem instances / seeds / grouping modes；
- no-overlap / low-overlap regression guard；
- operator validity rate。

这些指标只用于评价、筛选或分析 coordination operator，不改变原始优化问题的数学定义。换言之：

- 原始问题仍然是 `min f(x)`；
- 多个评价指标不是把原始问题改写成 multi-objective optimization；
- 如果后续阶段使用 scalar score、Pareto-style report 或 rank aggregation，它们只属于 outer evaluation protocol，不属于被优化问题本身。

## 4. 研究对象

LOCO 的研究对象不是完整优化器，而是 shared-variable conflict resolution 的 coordination operator。

在 overlapping LSGO 中，多个子组件或变量组可能共享同一批变量。共享变量会导致以下冲突：

- 一个 shared variable 被多个子组件提出不同更新方向；
- 局部子问题的 improvement 与全局 objective improvement 不一致；
- 子组件之间重复消耗 function evaluations；
- grouping 误差放大 shared-variable 的不稳定更新；
- 高 overlap density 区域比 non-shared variables 更容易产生干扰。

LOCO 只研究如何对这些 shared variables 的候选更新、权重、同步、冲突检测或冲突裁决进行协调。形式上，变量分组记为 `G = {G_1, ..., G_M}`，shared variable set 记为 `S = {i | m_i >= 2}`。LOCO operator 只允许在 `i in S` 上做局部协调映射：

```text
O_theta: s_i^t -> x_i^{t+1}
```

其中 `s_i^t` 表示第 `t` 步 shared variable `i` 的局部冲突状态或 proposal state；`x_i^{t+1}` 是该 shared variable 的下一步协调结果。该映射不生成完整解向量，不接管 BaseOpt，也不决定 scheduler/controller。

## 5. 明确非目标

LOCO-LSGO 不是以下项目：

- 不是让 LLM 生成全局优化器；
- 不是生成 DE、CMA-ES、SHADE、CC、DECC 或任何完整 optimizer；
- 不是 optimizer selection；
- 不是 scheduler/controller generation；
- 不是 automatic hyperparameter tuning；
- 不是 benchmark generator；
- 不是用 LLM 直接求解 `min f(x)`；
- 不是让 LLM 生成 typed AST 之外的任意 executable code；
- 不是把 overlap grouping 本身作为最终贡献包装；
- 不是把多指标评价伪装成 multi-objective optimizer。

## 6. Stage 0 的锁定范围

Stage 0 只交付研究边界、数学接口、系统禁止项、输入输出契约、实验边界、审稿风险防护和验收标准。

Stage 0 允许：

- 创建中文规格文档；
- 创建 boundary config 草案；
- 创建 typed contract 草案；
- 创建 boundary contract 测试。

Stage 0 禁止：

- 实现完整优化算法；
- 写 benchmark；
- 写 LLM 搜索逻辑；
- 调用 LLM；
- 做 evolution；
- 做调参；
- 运行真实 optimization experiment 并宣称 utility。

## 7. 研究 claim 边界

Stage 0 最多可以宣称：

- 研究问题已锁定；
- LOCO 与 optimizer/controller/scheduler 的边界已定义；
- 原始优化问题、operator interface、budget accounting 和 grouping reporting 的协议已形成草案；
- 后续实现需要通过 boundary tests 才能进入 Stage 1。

Stage 0 不能宣称：

- LOCO 已经有效；
- 学到的 operator 优于 baseline；
- 已经解决 overlapping LSGO；
- 已达到 SOTA；
- 已具备官方 benchmark 结论。
