# Stage 3.7 Coordination Family Literature Grounding and Allowed Vocabulary Lock

创建日期：2026-06-20
执行者：Codex
阶段边界：Stage 3.7 只锁定 Stage 4 前的 coordination family vocabulary。它不调用 LLM、不运行 evolution、不执行 AST、不做 objective evaluation、不接入 validation/test feedback，也不是 not a performance claim。

## 1. Purpose

Stage 3.6 已经冻结 quality-pass candidate pool。Stage 3.7 在进入 Stage 4 train-only evolution/search 前补一层文献和 vocabulary lock，回答一个审稿风险问题：

```text
这些 coordination families 为什么合理，而不是 LLM 随机拼出来？
```

本阶段的输出是：

```text
docs/stage4/coordination_family_literature_review.md
configs/stage4_coordination_family_space.yaml
tests/stage4/test_coordination_family_space.py
```

它只约束 Stage 4 的 allowed vocabulary，不生成 optimizer，不修改 BaseOpt，不执行候选 AST，也不声称任何 operator performance improvement。

## 2. Literature Grounding

LOCO-LSGO 的研究对象是 overlapping LSGO 中 shared variables 的 proposal conflict coordination。相关文献只作为 family design 的相邻领域依据：

- CEC2013 LSGO technical report 定义了 large-scale benchmark categories，并包含 F13 conforming overlap 与 F14 conflicting overlap 等 overlapping functions。LOCO 使用这条线来说明 shared-variable conflict 是官方 LSGO 结构中的核心对象之一，而不是自造问题。Source: https://titan.csit.rmit.edu.au/~e46507/cec13-lsgo/competition/cec2013-lsgo-benchmark-tech-report.pdf
- OEDG 这类 overlapping LSGO grouping 工作关注 overlapping problem 中 subcomponents 与 shared variables 的识别。LOCO 不替代 grouping method，而是在 shared variables 已被识别或报告后研究 coordination operator。Source: https://arxiv.org/html/2404.10515v1
- HCC / complex overlapping CC 与 RDG3 类工作说明 overlapping components 会给 cooperative coevolution 带来更复杂的 decomposition 与 component interaction 问题。LOCO 借用问题背景，不声称实现这些算法。Source: https://eprints.whiterose.ac.uk/id/eprint/156232/1/RDG3_v3.pdf
- ADMM 和 distributed consensus 提供 local variables 与 global consensus variable 的思想类比。LOCO 只能借鉴 consensus / residual balancing 的结构直觉，不能声称实现 ADMM optimizer。Source: https://web.stanford.edu/~boyd/papers/pdf/admm_distr_stats.pdf
- robust aggregation 文献中的 median、trimmed mean、geometric median 等思想支持 robust_consensus family，用于降低异常 proposal 的影响。LOCO 只把它们作为 shared-variable proposal aggregation primitive 的设计来源。Sources: https://arxiv.org/pdf/1912.13445 and https://proceedings.mlr.press/v80/yin18a/yin18a.pdf
- contribution-based cooperative coevolution 支持 reward_or_contribution_weighting family 的直觉：不同 component proposal 的贡献可以影响 shared-variable proposal weighting。但 LOCO 不能把这一步扩展成 resource scheduler、optimizer selection 或 full CC controller。
- trust-region 与 projection / repair 提供 conservative step control 和 feasibility correction 的相邻思想。LOCO 只能使用 dampening、clip、projection、repair 这类局部 shared-variable primitive，不能声称实现 trust-region optimizer。

## 3. Global Boundary

所有 family 必须满足：

```text
search target = typed coordination operator AST
scope = shared variables only
updated_indices subset S
allowed split = train
validation usage = selection only after train search
test usage = sealed final reporting only
```

所有 Stage 4 额外 function evaluations 必须完整计入：

```text
FE_total = FE_grouping + FE_proposal + FE_coordination_extra + FE_repair
```

禁止访问或生成：

```text
optimizer
controller
scheduler
optimizer_selection
BaseOpt modification
function_id
benchmark_name
true_optimum
test_metadata
future_evaluations
hidden_test_information
DE / CMA-ES / PSO / SHADE / L-SHADE
benchmark objective rewrite
```

## 4. Family Lock

### F0 identity_no_coord_low_overlap_safeguard

来源：no-overlap / low-overlap regression guard 和 CEC2013 LSGO overlap categories。

LOCO 含义：当 shared-variable conflict 不存在、overlap 很低、或 coordination 风险高于收益时，保留 BaseOpt proposal，不做额外协调。

允许 primitives：`no_coord`, `conditional`。

合法 train-time signals：low-overlap/no-overlap guard state、proposal_conflict_magnitude、budget_ledger_state。

边界：shared variables only；不能修改 BaseOpt；不能把 no-op 包装成性能提升。

### F1 consensus

来源：ADMM / distributed consensus 中 local copies 与 global consensus 的类比。

LOCO 含义：多个 overlapping subcomponents 对同一个 shared variable 给出 proposals 时，把它们聚合成一个 consensus update。

允许 primitives：`consensus`, `weighted_consensus`, `clip`。

合法 train-time signals：proposal_values、proposal_deltas、proposal_disagreement、budget_ledger_state。

边界：只处理 shared-variable proposal，不实现 ADMM optimizer。

### F2 robust_consensus

来源：robust aggregation 中 median、trimmed mean、geometric median 等抗异常聚合思想。

LOCO 含义：当某些 component proposals 明显偏离其它 proposals 时，降低 outlier influence，再输出 shared-variable consensus。

允许 primitives：`robust_consensus`, `clip`, `conditional`。

合法 train-time signals：proposal_values、proposal_deltas、proposal_disagreement、budget_ledger_state。

边界：不能访问 benchmark_name、function_id、true_optimum 或 test_metadata 来判断 outlier。

### F3 reward_or_contribution_weighting

来源：contribution-based cooperative coevolution 与 component credit assignment。

LOCO 含义：用 train split 上合法记录的 proposal reward 或 contribution trace 给 competing proposals 加权。

允许 primitives：`reweighting`, `weighted_consensus`, `clip`。

合法 train-time signals：proposal_rewards_or_contributions、proposal_values、budget_ledger_state、fe_overhead。

边界：只能影响 shared-variable proposal weighting，不能变成 scheduler、controller 或 optimizer_selection。

### F4 winner_or_soft_selection

来源：local proposal winner selection、soft selection 与 rank aggregation。

LOCO 含义：在多个 shared-variable proposals 中选择一个 winner，或按 legal train-time evidence 软混合多个 proposals。

允许 primitives：`best_reward_select`, `soft_select`, `clip`。

合法 train-time signals：proposal_rewards_or_contributions、proposal_conflict_magnitude、budget_ledger_state。

边界：不能为完整 optimizer 选择 component 或资源分配策略。

### F5 dampening_trust_region_like_step_control

来源：trust-region step control 和 conservative update dampening。

LOCO 含义：对 shared-variable update size 做 dampening / clip，避免 conflicting proposals 放大震荡。

允许 primitives：`dampening`, `clip`, `conditional`。

合法 train-time signals：proposal_deltas、proposal_conflict_magnitude、historical_coordination_trace_on_train_split、budget_ledger_state。

边界：只是 trust-region-like step control，不是 trust-region optimizer。

### F6 projection_repair

来源：projection 与 feasibility repair。

LOCO 含义：把协调后的 shared-variable update 投影或修复回合法 bounds、安全 proposal range 或 typed AST 允许的局部状态。

允许 primitives：`projection`, `repair`, `clip`。

合法 train-time signals：proposal_values、proposal_deltas、budget_ledger_state、fe_overhead。

边界：repair 的额外 FE 必须计入 FE accounting；不能重写 benchmark objective。

### F7 residual_dual_memory_conflict_balancing

来源：ADMM residual balancing 的结构类比，以及 train-only coordination trace memory。

LOCO 含义：记录 train split 中 shared-variable proposal disagreement 的 residual / dual-memory style trace，用于保守调整之后的 coordination。

允许 primitives：`residual_balance`, `dual_memory_balance`, `dampening`, `conditional`。

合法 train-time signals：historical_coordination_trace_on_train_split、proposal_disagreement、budget_ledger_state、fe_overhead。

边界：不能读取 future_evaluations 或 validation/test feedback。

### F8 temporal_hysteresis_anti_oscillation

来源：iterative coordination 中的 anti-oscillation safeguard 和 temporal hysteresis。

LOCO 含义：当 shared-variable update 在连续 rounds 中快速反向或震荡时，用 hysteresis / dampening 降低 flip-flop。

允许 primitives：`temporal_hysteresis`, `anti_oscillation`, `dampening`, `conditional`。

合法 train-time signals：historical_coordination_trace_on_train_split、proposal_deltas、proposal_conflict_magnitude、budget_ledger_state。

边界：只能使用 train split 历史，不使用 validation/test metadata。

### F9 conditional_composition_within_typed_ast

来源：typed AST composition 与受约束的 hyper-heuristic style rule composition。

LOCO 含义：在 typed coordination operator AST 内按显式条件组合多个合法 primitives，例如 conflict 高时 robust_consensus，低时 no_coord，震荡时 dampening。

允许 primitives：`conditional`, `no_coord`, `weighted_consensus`, `robust_consensus`, `best_reward_select`, `dampening`, `projection`, `repair`, `reweighting`, `temporal_hysteresis`。

合法 train-time signals：proposal_conflict_magnitude、proposal_disagreement、historical_coordination_trace_on_train_split、budget_ledger_state、fe_overhead。

边界：conditional composition 不能绕开 typed AST，不能生成 arbitrary executable code，不能生成 optimizer/controller/scheduler。

## 5. Stage 4 Use

Stage 4 可以在 frozen Stage 3.6 candidate pool 上进行 train-only evolution/search，但必须先满足本文件和 `configs/stage4_coordination_family_space.yaml` 的 vocabulary lock。

Stage 4 仍必须保持：

```text
BaseOpt fixed
all extra FE counted
train-only search
validation selection only after train search
sealed test final reporting
oracle grouping and detected grouping reported separately
not a performance claim until held-out evaluation permits such a claim
```

