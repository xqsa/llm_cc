# Stage 7.5 SOTA-Targeted Real Benchmark Protocol Lock

创建日期：2026-06-21  
执行者：Codex  
阶段边界：Stage 7.5 只锁定 SOTA-facing real-benchmark comparison 的协议，不运行 CEC2013，不抽取论文表格数值，不修改 selected operator，不修改 BaseOpt，也不做任何 performance claim。

## 1. Why This Stage Exists

Stage 7.3 的 synthetic objective evidence 是 mixed 的：`simple_consensus` 仍然排在前面，而 `selected_loco_operator` 在当前面板里只排到第 4。Stage 7.4 因此只决定“是否需要真实 overlap panel”，没有把任何结果升级为 SOTA 证据。

Stage 7.5 进一步回答的是另一个更严格的问题：

```text
哪些 published results 可以被当作 direct comparator？
什么条件下只能当 background context？
F13/F14 的 overlap evidence 能不能直接升级成 full CEC2013 LSGO SOTA claim？
```

答案是：

```text
F13/F14-only can support overlap-focused evidence.
Full CEC2013 LSGO SOTA requires same-setting comparison against the official benchmark contract.
```

## 2. Literature Grounding

This stage is grounded in the following sources:

- Official CEC2013 LSGO technical report: defines the benchmark family, the 15-function suite, and the canonical large-scale evaluation framing.
- Stage 1.6 CEC2013 semantics correction in this repository: records the local contract for `D_formula`, `D_api`, `F13`, `F14`, overlap semantics, and FE accounting.
- Recent overlapping-LSGO / grouping literature:
  - `A Novel Two-Phase Cooperative Co-evolution Framework for Large-Scale Global Optimization with Complex Overlapping` (2025, arXiv).
  - `An Enhanced Differential Grouping Method for Large-Scale Overlapping Problems` (2024, arXiv).

These papers support the general claim that overlapping subcomponents and shared-variable grouping are active research problems, but they do **not** relax the comparison rules. They only justify why overlap-focused protocol work is necessary before any strong empirical claim.

## 3. Official Comparison Contract

The official CEC2013 LSGO setting is locked as:

```text
benchmark_suite = CEC2013_LSGO
function_count = 15
dimension = 1000
run_count = 25
MaxFEs = 3e6
max_fe = 3e6
termination = maximum_function_evaluations
checkpoints = 120000, 600000, 3000000
statistics = best, median, worst, mean, std
primary_ranking_statistic = median_at_checkpoints
```

Any direct comparator must record at least:

```text
benchmark_suite
function_ids
max_fe
run_count
statistic
objective_implementation
dimension_semantics
same_budget
source_citation
```

If any of those are missing or ambiguous, the result is treated as background-only rather than a direct SOTA comparator.

For the avoidance of doubt:

```text
25 runs
MaxFEs = 3e6
F13/F14-only is not full CEC2013 LSGO SOTA
current selected LOCO operator is not SOTA-ready
```

## 4. Reported Results Reuse Policy

Stage 7.5 allows reuse of published results only as a **paper comparator audit**, not as runtime feedback.

Allowed:

- cite paper table values when the benchmark setting matches
- use the paper's reported numbers as direct comparators only if the setting is compatible
- keep explicit source citation and table location

Forbidden:

- using reported results to tune operators
- using paper tables as hidden validation feedback
- claiming SOTA from mismatched settings
- treating partial overlap panels as full-suite SOTA evidence

## 5. Claim Tiers

```text
T0 = protocol-only
T1 = overlap-focused F13/F14 panel
T2 = CEC2013 subset claim
T3 = full same-setting CEC2013 LSGO SOTA-facing claim
```

Stage 7.5 locks the following rule:

```text
F13/F14-only evidence cannot be promoted directly to T3.
```

That is the whole point of this stage.

## 6. LOCO Boundary

Stage 7.5 preserves the core LOCO-LSGO boundary:

```text
no LLM call
no new candidate generation
no evolution/search run
no AST execution
no objective evaluation
no CEC2013 panel run
no BaseOpt modification
no optimizer/controller/scheduler generation
no performance claim
no SOTA claim
```

LOCO remains a coordination-operator discovery system for shared-variable conflicts. This stage only decides how its future benchmark evidence may be compared.

## 7. Next Step

Stage 7.5 next status:

```text
READY_FOR_STAGE7_6_REPORTED_RESULTS_COMPARATOR_AUDIT
```

Recommended next stage:

```text
Stage 7.6: Reported-Results Comparator Extraction And Admissibility Audit
```

That next stage may collect specific paper tables and compare them only under the contract locked here.
