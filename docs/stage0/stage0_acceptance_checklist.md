# Stage 0: Acceptance Checklist

生成日期：2026-06-19  
执行者：Codex

## 1. 通过标准

Stage 0 通过必须同时满足以下条件：

- [ ] `docs/stage0/research_problem.md` 明确核心研究问题和非目标。
- [ ] `docs/stage0/system_boundary.md` 明确 LOCO 只作用于 shared variables。
- [ ] `docs/stage0/mathematical_contract.md` 明确原始问题是单目标 `min f(x)`。
- [ ] `docs/stage0/allowed_and_forbidden_behaviors.md` 明确 LLM 只能生成 coordination operator AST。
- [ ] 数学符号统一包含 `G = {G_1, ..., G_M}`、`S = {i | m_i >= 2}` 和 `O_theta: s_i^t -> x_i^{t+1}`。
- [ ] LOCO 不能访问 function id、benchmark name、true optimum location、test-set metadata、future evaluations 和 hidden test information。
- [ ] FE 预算明确分解为 `FE_total = FE_grouping + FE_proposal + FE_coordination_extra + FE_repair`。
- [ ] `docs/stage0/reviewer_risk_analysis.md` 覆盖 optimizer generation、optimizer selection、scheduler/controller、multi-objective claim、budget unfairness 和 grouping leakage 风险。
- [ ] `docs/stage0/implementation_roadmap_from_stage0.md` 只定义后续阶段 gate，不实现算法。
- [ ] `configs/stage0_boundary.yaml` 存在且表达禁止项。
- [ ] `loco/contracts/stage0_types.py` 只包含接口草案与自验证，不包含 optimizer/evolution/benchmark 逻辑。
- [ ] `tests/stage0/test_boundary_contract.py` 不调用 LLM、不做 evolution、不调参、不运行 benchmark。
- [ ] BaseOpt 固定原则已写入文档和配置。
- [ ] oracle grouping 与 detected grouping 必须分开报告。
- [ ] 所有额外 function evaluations 必须计入预算。
- [ ] no-overlap / low-overlap regression guard 已写入验收标准。
- [ ] Stage 0 测试可以在本地通过。

## 2. 失败标准

出现任一情况，Stage 0 判定失败：

- 任一文档把原始问题写成 multi-objective optimization。
- 任一接口允许 LLM 生成 optimizer、controller、scheduler 或 benchmark。
- 任一接口允许 LLM 修改 BaseOpt、选择 optimizer、访问 test feedback、在 test set 上调参，或生成 typed AST 之外的 arbitrary executable code。
- 任一接口允许 LOCO 作用于 non-shared variables。
- 任一接口允许 LOCO 访问 function id、benchmark name、true optimum location、test-set metadata、future evaluations 或 hidden test information。
- 任一说明允许额外 `f(x)` 调用不计入预算。
- 任一测试调用 LLM、执行 evolution、调参或运行 benchmark。
- oracle grouping 与 detected grouping 被混合汇报。
- BaseOpt 可随 LOCO 方案变化而更换。
- no-overlap / low-overlap 场景没有 regression guard。
- Stage 0 产物宣称 LOCO 已经带来 performance improvement。
- typed contract 中出现完整 optimizer、benchmark generator 或 LLM search loop 实现。

## 3. Stage 0 验收命令

建议的最小验收命令：

```powershell
python -m pytest tests/stage0 -q
```

该命令只验证 boundary contract，不验证算法性能。

## 4. No-overlap / Low-overlap guard

后续阶段进入任何 performance experiment 前，必须定义：

- no-overlap problem subset；
- low-overlap problem subset；
- BaseOpt-only reference run；
- LOCO-enabled same-budget run；
- regression threshold；
- stop condition。

Stage 0 不运行这些实验，只要求边界中预留该 guard。

最低判定原则：

- no-overlap：LOCO 应为 no-op 或等价安全路径。
- low-overlap：LOCO 不应明显劣于固定 BaseOpt。
- 若明显退化，必须先诊断 shared-variable targeting 或 conflict detection，不得继续扩大 claim。

## 5. Stage 0 完成声明模板

只有当 checklist 全部满足且 boundary tests 通过时，才允许使用以下声明：

> Stage 0 has locked the LOCO-LSGO research problem, system boundary, mathematical contract, forbidden behaviors, evaluation boundary, reviewer-risk guard, and typed boundary tests. It does not claim algorithmic utility or benchmark performance.
