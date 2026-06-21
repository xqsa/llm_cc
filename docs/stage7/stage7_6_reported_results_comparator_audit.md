# Stage 7.6 Reported-Results Comparator Audit

创建日期：2026-06-21  
执行者：Codex  
阶段边界：Stage 7.6 只做 published reported results 的 comparator audit。它不运行 objective，不调用 LLM，不做 evolution/search，不执行 AST，不修改 BaseOpt，也不把 paper table values 当作 runtime feedback 或 performance claim。

## 1. Purpose

Stage 7.5 已经锁定了 same-setting comparator contract。Stage 7.6 负责把 published reported results 分类成 direct comparator、background only 或 not admissible，并冻结一个最小 comparator registry。

这个阶段解决的是审稿时最容易被追问的一层：

```text
哪些论文结果可以直接比？
哪些只能当背景？
哪些根本不能进入同一张比较表？
```

## 2. Audit Sources

Stage 7.6 只用 Stage 7.5 锁定的比较规则来审计 published results。

Direct comparator source:

```text
HCC / A Novel Two-Phase Cooperative Co-evolution Framework for Large-Scale Global Optimization with Complex Overlapping
source = https://arxiv.org/abs/2503.21797
```

Background-only source:

```text
OEDG / An Enhanced Differential Grouping Method for Large-Scale Overlapping Problems
source = https://arxiv.org/abs/2404.10515
```

These are audit sources only. Stage 7.6 does not extract table values into runtime logic and does not use the reported numbers to tune any operator.

## 3. Comparator Classification Rule

Stage 7.6 applies the Stage 7.5 same-setting contract:

```text
direct comparator => same benchmark family, same function scope, same FE budget, same run count or explicitly compatible, explicit statistic, explicit source citation
background only => relevant paper evidence but settings are not same-setting CEC2013 comparators
not admissible => missing or contradictory setting evidence
```

## 4. Frozen Registry

The frozen registry written by Stage 7.6 contains:

```text
reported_results_comparator_registry.json
reported_results_comparator_audit_report.json
next_route_decision.json
```

Registry rules:

```text
source_contract = Stage 7.5 same-setting comparator contract
direct_comparator_sources = HCC
background_only_sources = OEDG
use_reported_results_as_runtime_feedback = false
not_sota_claim = true
```

## 5. Boundary

Stage 7.6 preserves:

```text
no LLM call
no evolution/search run
no AST execution
no objective evaluation
no benchmark run
no test-feedback tuning
no BaseOpt modification
no optimizer/controller/scheduler generation
not a SOTA claim
not a final performance claim
```

## 6. Next Step

Stage 7.6 next status:

```text
READY_FOR_STAGE8_0_TRAIN_ONLY_OPERATOR_IMPROVEMENT
```

This keeps the main line moving after comparator audit, without turning reported results into runtime feedback.
