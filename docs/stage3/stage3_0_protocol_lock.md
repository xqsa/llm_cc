# Stage 3.0 Protocol Lock

创建日期：2026-06-20
执行者：Codex
阶段边界：Stage 3.0 只锁定 protocol；no LLM call、no evolution run、no objective evaluation、no optimizer generation、no scheduler/controller generation、no test feedback。

## 1. 阶段目标

Stage 3.0 的目标不是开始搜索，而是在进入任何 LLM/evolution search 之前，把合法搜索空间、candidate schema、test feedback firewall、selection protocol 和失败标准固定下来。

Stage 3.0 依赖 Stage 2.10 的 readiness decision：

```text
READY_FOR_STAGE3_BOUNDARY_ONLY
```

该 decision 只允许下一阶段做：

```text
LLM/evolution search over typed coordination operator ASTs only
```

这不是 performance claim，不表示已经学到了 reusable coordination operators，也不表示 optimizer performance improvement。

## 2. 原始问题不变

LOCO-LSGO 的原始优化问题仍然是 single-objective LSGO：

```text
minimize f(x), x in Omega
```

外层 operator selection 可以记录 final error、conflict intensity、oscillation、FE overhead、generalization 等多个评价指标，但这些是 coordination operator 的评价指标，不把原始 LSGO 问题改成 multi-objective optimization。

## 3. Stage 3 允许什么

Stage 3 只允许：

```text
typed coordination operator AST
```

该 AST 必须只作用于 shared variables，并复用 Stage 2.2 已经锁定的 `loco.dsl.v1` boundary。

LLM 的角色：

```text
propose candidate AST structures only
```

Evolution 的角色：

```text
select among validated candidate ASTs using train/validation operator metrics only
```

## 4. Stage 3 禁止什么

Stage 3 继续禁止：

- no optimizer generation；
- no BaseOpt modification；
- no scheduler/controller generation；
- no optimizer selection；
- no benchmark objective rewrite；
- no arbitrary executable code；
- no test feedback；
- no test-set tuning；
- no benchmark-specific metadata。

LLM 不能生成 DE、CMA-ES、PSO、SHADE、L-SHADE、optimizer selector、scheduler、controller 或任意 Python callable。LLM 输出必须是 typed coordination operator AST wrapper。

## 5. Stage 3.0 自身禁止动作

Stage 3.0 是 protocol lock，因此本阶段自身禁止：

- no LLM call；
- no evolution run；
- no candidate generation；
- no objective evaluation；
- no optimizer implementation；
- no controller/scheduler implementation；
- no benchmark modification。

Stage 3.0 只能新增文档、配置、schema/helper 和边界测试。

## 6. 阶段通过标准

Stage 3.0 PASS 需要同时满足：

- Stage 2.10 readiness decision 为 `READY_FOR_STAGE3_BOUNDARY_ONLY`；
- prompt contract 已锁定；
- candidate wrapper schema 已锁定；
- Stage 2 typed AST boundary 被复用，而不是重写一套 AST 规则；
- test feedback firewall 已文档化；
- Stage 3.0 tests pass；
- Stage 3.0 import 不加载 LLM/evolution client；
- no LLM call、no evolution run、no objective evaluation；
- 文档明确写明 not a performance claim。

## 7. 阶段失败标准

任一情况出现即 Stage 3.0 FAIL：

- Stage 2.10 readiness decision 不是 `READY_FOR_STAGE3_BOUNDARY_ONLY`；
- candidate 可以绕过 typed AST schema；
- candidate 可以作用于 non-shared variables；
- prompt contract 允许 optimizer/controller/scheduler；
- selection protocol 可以访问 test feedback；
- Stage 3.0 调用了 LLM、运行 evolution 或调用 objective function；
- 文档把 protocol lock 误写成 learned operator 或 performance success。

## 8. 下一阶段边界

Stage 3.0 完成后，下一阶段才可以进入小规模 Stage 3.1：

```text
first small-batch LLM candidate generation, train-only, audit-heavy
```

Stage 3.1 仍必须使用本阶段锁定的 prompt contract、candidate schema、test feedback firewall 和 train/validation/test split discipline。
