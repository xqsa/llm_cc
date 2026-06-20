# Operator AST Search Space

创建日期：2026-06-20
执行者：Codex
阶段边界：描述 Stage 3 的合法 search space；no LLM call、no evolution run、no objective evaluation。

## 1. Search Target

Stage 3 的唯一 search target 是：

```text
typed coordination operator AST
```

该 AST 不是 optimizer，不是 scheduler/controller，不是 optimizer selector，也不是 arbitrary executable code。

## 2. Target Scope

LOCO 只作用于 shared variables：

```text
S = {i | m_i >= 2}
```

candidate AST 的所有 node target 必须满足：

```text
target.variable_id in S
```

任何作用于 non-shared variables 的 candidate 必须 rejected。

## 3. Reused Stage 2 Boundary

Stage 3.0 复用 Stage 2.2 的 `loco.dsl.v1`：

- allowed node kinds: consensus、weighted_consensus、best_reward_select、projection、dampening、reweighting、clip、repair；
- forbidden node kinds: optimizer、DE/CMA-ES/PSO/SHADE/L-SHADE、controller、scheduler、optimizer_selection；
- forbidden metadata: function_id、benchmark_name、true_optimum_location、test_set_metadata、future_evaluations、hidden_test_information；
- forbidden code: import、eval、exec、lambda、def、class、subprocess 等任意可执行代码字符串。

Stage 3.0 不重新实现 AST 规则，避免形成第二事实源。

## 4. LLM Candidate Wrapper

LLM 输出必须包装为：

```text
schema_version = loco.llm_candidate.v1
ast.schema_version = loco.dsl.v1
declared_scope.target = shared_variables_only
```

所有负边界声明必须为 true：

- not_optimizer；
- not_controller；
- not_scheduler；
- not_optimizer_selection；
- not_benchmark_specific；
- no_test_feedback。

## 5. Claim Boundary

该 search space 只定义候选结构边界，不表示任何 candidate 已经有效，也不构成 performance claim。
