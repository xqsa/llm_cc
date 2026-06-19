# Stage 0: Reviewer Risk Analysis

生成日期：2026-06-19  
执行者：Codex

## 1. 风险：被误解为 LLM 生成优化器

审稿风险：

Reviewer 可能认为 LOCO-LSGO 是又一个 “LLM generates optimizer” 项目。

防护边界：

- 标题和摘要中强调 coordination operators for shared-variable conflicts。
- 方法图中把 BaseOpt 与 LOCO operator 分开。
- 明确 LLM 输出是 coordination operator AST，不是 optimizer code。
- 明确 LLM 不能生成 typed AST 之外的 arbitrary executable code。
- 实验中固定 BaseOpt，不通过更强 optimizer 获益。

必须避免的表述：

- “LLM designs a new optimizer.”
- “LOCO replaces DE/SHADE/CMA-ES.”
- “The model controls the optimization process.”

## 2. 风险：被误解为 scheduler/controller

审稿风险：

如果 LOCO operator 决定何时运行哪个 group 或如何分配全局 budget，Reviewer 会将其归类为 scheduler/controller。

防护边界：

- LOCO 只处理 shared variables 上的冲突协调。
- group order、budget allocation、restart policy、optimizer switching 不属于 LOCO。
- 如果后续需要 scheduler，必须作为外部固定 protocol，而不是 LLM 生成对象。

## 3. 风险：被误解为 optimizer selection

审稿风险：

如果不同 operator 绑定不同 BaseOpt 或不同 hyperparameters，Reviewer 会认为贡献来自 optimizer selection。

防护边界：

- BaseOpt 固定。
- 主要 hyperparameters 固定。
- LOCO-enabled 与 BaseOpt-only 使用 same-budget ledger。
- 不允许因为 LOCO 方案不同而换 optimizer。

## 4. 风险：把外层多指标评价误写成 multi-objective optimization

审稿风险：

外层 operator evaluation 可能使用多个指标，容易被误解为原始问题变成 multi-objective optimization。

防护边界：

- 原始问题始终写为 `min_{x in Omega} f(x)`。
- 多个指标只用于 operator search/evaluation/reporting。
- 文稿中明确 “these metrics do not redefine the original objective”。

## 5. 风险：budget unfairness

审稿风险：

LOCO 可能通过额外 probing、validation 或 tie-breaking 获得隐形 function evaluations。

防护边界：

- 所有 `f(x)` 调用计入预算。
- 报告 `FE_BaseOpt`、`FE_LOCO_extra` 和 `FE_total`。
- 不允许 hidden validation evaluations。
- 报告 `FE_total = FE_grouping + FE_proposal + FE_coordination_extra + FE_repair`。
- same-budget 是正式比较的硬条件。

## 6. 风险：oracle grouping leakage

审稿风险：

oracle grouping 结果如果混入 detected grouping 实验，会形成不公平信息泄漏。

防护边界：

- oracle grouping 和 detected grouping 分开报告。
- detected grouping mode 禁止读取 oracle-only labels。
- 使用 oracle grouping 的结果只能作为 upper-bound 或 diagnostic，不可替代 realistic setting。

## 7. 风险：test information leakage

审稿风险：

如果 LOCO operator 或 LLM prompt 能访问 function id、benchmark name、true optimum location、test-set metadata、future evaluations 或 hidden test information，Reviewer 会认为 operator 记住了测试集或利用了不可用信息。

防护边界：

- 这些字段不能作为 operator 输入。
- 这些字段不能作为 LLM prompt feature。
- 这些字段不能参与 operator selection。
- detected grouping mode 禁止读取 oracle-only labels。
- test feedback 不能用于 tuning 或 evolution。

## 8. 风险：no-overlap / low-overlap 退化

审稿风险：

如果 LOCO 只在 high-overlap 场景有效，却在 no-overlap 或 low-overlap 场景明显退化，Reviewer 会质疑 reusable operator 的稳健性。

防护边界：

- no-overlap 应有 no-op path。
- low-overlap 应有 regression guard。
- 单独报告这些 regime。
- 若退化明显，claim 限制为 high-overlap diagnostic，不得宣称 general reusable coordination。

## 9. 风险：贡献与 grouping detection 混淆

审稿风险：

Reviewer 可能认为提升来自更好的 grouping detection，而不是 coordination operator。

防护边界：

- grouping layer 与 LOCO layer 分离。
- oracle grouping 与 detected grouping 均可作为输入模式，但结果分开。
- 同一 grouping input 下比较 BaseOpt-only 与 BaseOpt+LOCO。
- 不把 grouping detector 作为 Stage 0 或核心贡献。

## 10. 风险：Stage 0 过度 claim

审稿风险：

Stage 0 只定义边界，如果文档声称 utility，会削弱可信度。

防护边界：

- Stage 0 只能声明 problem locked 和 contract defined。
- 不声明 performance。
- 不声明 benchmark result。
- 不声明 learned operator 已经存在。
