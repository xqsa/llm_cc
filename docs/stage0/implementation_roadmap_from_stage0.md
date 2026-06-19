# Implementation Roadmap From Stage 0

生成日期：2026-06-19  
执行者：Codex

## 1. 路线图原则

本路线图只定义 Stage 0 之后的阶段边界和 gate，不实现算法。

所有后续阶段必须继承 Stage 0 的硬约束：

- 原始问题是单目标 `min f(x)`；
- LOCO 只作用于 shared variables；
- LLM 只能生成 coordination operator AST；
- LLM 不能生成 typed AST 之外的 arbitrary executable code；
- LOCO 不能访问 function id、benchmark name、true optimum location、test-set metadata、future evaluations 或 hidden test information；
- BaseOpt 固定；
- oracle grouping 与 detected grouping 分开报告；
- 所有额外 function evaluations 计入预算；
- `FE_total = FE_grouping + FE_proposal + FE_coordination_extra + FE_repair` 必须可审计；
- no-overlap / low-overlap 设置 regression guard。

## 2. Stage 1: Minimal Contract Runtime

目标：

- 实现 coordination operator AST schema validator；
- 实现 shared-variable scope checker；
- 实现 budget ledger stub；
- 实现 no-op operator baseline；
- 仍不做 LLM search，不做 evolution。

进入条件：

- Stage 0 checklist 全部通过；
- `tests/stage0` 全部通过；
- 文档无 multi-objective 原始问题误写；
- boundary config 可被 Stage 1 读取。

退出条件：

- 非法 AST 被拒绝；
- non-shared target 被拒绝；
- budget ledger 可以记录所有 `f(x)` 调用；
- no-op operator 在 no-overlap 场景中不改变 BaseOpt 行为。

## 3. Stage 2: Fixed-Operator Smoke Harness

目标：

- 在固定 BaseOpt 下接入手写或冻结的少量 coordination operators；
- 只做 smoke-level harness；
- 不做 LLM evolution；
- 不做调参；
- 不宣称 final performance。

进入条件：

- Stage 1 scope checker 与 budget ledger 通过；
- BaseOpt 已固定；
- problem set 与 grouping mode 已声明。

退出条件：

- BaseOpt-only 与 BaseOpt+LOCO same-budget ledger 可对齐；
- oracle grouping 与 detected grouping report 分离；
- no-overlap / low-overlap guard 可运行；
- 所有额外 `f(x)` 调用可追踪。

## 4. Stage 3: LLM-Generated Operator AST Pilot

目标：

- 允许 LLM 生成 coordination operator AST；
- 不允许 LLM 生成 optimizer/controller/scheduler；
- 使用 validator 拒绝越界 AST；
- 只做小规模 pilot。

进入条件：

- Stage 2 harness 通过；
- AST grammar 已冻结；
- forbidden behavior tests 覆盖 optimizer/controller/scheduler 生成尝试；
- LLM provenance logging 已定义。

退出条件：

- 所有 accepted AST 都通过 scope checker；
- rejected AST 有明确 reject reason；
- 不存在 LLM 直接控制 optimization loop 的路径；
- pilot 结果只作为 feasibility evidence，不作为 SOTA claim。

## 5. Stage 4: Operator Search / Evolution

目标：

- 在冻结 AST grammar 和 validator 下做 operator search；
- 使用多指标评价筛选 operator；
- 保持原始问题单目标；
- 所有额外 evaluations 计入预算。

进入条件：

- Stage 3 accepted AST provenance 完整；
- same-budget protocol 可重复；
- no-overlap / low-overlap guard 已纳入自动报告。

退出条件：

- search logs 可复现；
- operator selection 不越界为 optimizer selection；
- multi-metric evaluation 不被写成 multi-objective problem；
- failed operators 与 rejected operators 分开统计。

## 6. Stage 5: Formal Evaluation

目标：

- 正式比较 BaseOpt-only 与 BaseOpt+LOCO；
- 分开 oracle grouping 与 detected grouping；
- 分 overlap regime 报告；
- 做 ablation 与 reviewer-risk audit。

进入条件：

- Stage 4 产生冻结 operator set；
- evaluation protocol 冻结；
- seeds、budgets、BaseOpt、grouping mode 全部声明。

退出条件：

- same-budget results；
- no hidden evaluations；
- no-overlap / low-overlap regression report；
- oracle/detected grouping separated report；
- failure cases included；
- claim boundary 与 evidence 匹配。

## 7. Stop Conditions

任一阶段出现以下情况，必须停止扩大 claim：

- LLM 输出 optimizer/controller/scheduler；
- LOCO 作用于 non-shared variables；
- BaseOpt 被替换；
- 额外 `f(x)` 调用未计入预算；
- oracle grouping 泄漏到 detected grouping；
- no-overlap / low-overlap 明显退化且未解释；
- 外层指标被误写成原始 multi-objective optimization；
- 测试或报告使用隐藏 fallback 制造成功。
