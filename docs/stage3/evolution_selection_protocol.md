# Evolution Selection Protocol

创建日期：2026-06-20
执行者：Codex
阶段边界：定义未来 Stage 3 evolution selection 的协议；Stage 3.0 no evolution run。

## 1. Evolution 的角色

Evolution 只允许在已经通过 schema/boundary validation 的 typed coordination operator AST 之间做筛选、组合或淘汰。

Evolution 不能：

- 生成 optimizer；
- 修改 BaseOpt；
- 生成 scheduler/controller；
- 选择 optimizer；
- 重写 benchmark objective；
- 使用 test feedback；
- 为了 test set 调参。

## 2. Selection Inputs

未来 Stage 3 selection 可以使用 train/validation 上的 operator-level metrics：

- final error；
- proposal_consensus_collapse_ratio；
- post_coordination_regenerated_conflict；
- oscillation；
- FE overhead；
- generalization proxy。

这些指标只服务于 coordination operator selection，不改变原始问题 `minimize f(x), x in Omega` 的 single-objective 性质。

## 3. Split Discipline

协议必须分开：

- train：candidate generation 和 evolution selection；
- validation：operator selection、early stopping、promotion decision；
- test：frozen final operator 的 sealed final reporting。

test feedback 不能回流到 prompt、candidate rejection、evolution selection 或 operator library 修改。

## 4. FE Accounting

所有额外 function evaluations 必须计入：

```text
FE_total = FE_grouping + FE_proposal + FE_coordination_extra + FE_repair
```

不同 method run 的 cross-method comparison evaluations 不能共享预算。

## 5. Stage 3.0 Claim Boundary

Stage 3.0 不运行 evolution。本文件只锁定未来 Stage 3 evolution selection 的合法边界。
