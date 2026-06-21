# Stage 8.5 Failure-Honest Stage 8.4 Analysis

创建日期：2026-06-21  
执行者：Codex  
阶段边界：Stage 8.5 只读取 Stage 8.4 artifacts，分析为什么 selected operator 能赢旧 frozen operator，但不能赢 best simple baseline。它不重新运行 objective loop，不做 new objective evaluation，不调用 LLM，不生成新 candidate，不修改 selected operator，不使用 validation/test feedback，不修改 BaseOpt，也不声称 SOTA 或 final objective-value performance improvement。

## 1. Question

Stage 8.5 回答：

```text
为什么 stage3_5_batch_1_reweighting_repair 能赢旧 frozen Stage 5.1 operator，
但不能赢 best simple baseline？
```

## 2. Inputs

Stage 8.5 只读取：

```text
artifacts/objective_eval/stage8_4/objective_trace.jsonl
artifacts/objective_eval/stage8_4/win_loss_report.json
artifacts/objective_eval/stage8_4/method_summary.json
artifacts/objective_eval/stage8_4/panel_report.json
```

## 3. Main Finding

大白话结论：

```text
selected operator is numerically equivalent to weighted_consensus.
```

也就是说，Stage 8.3 选出的：

```text
stage3_5_batch_1_reweighting_repair
```

在 Stage 8.4 这个 panel 里，行为上等价于 `weighted_consensus`。它不是在这个 panel 上学出了比 best baseline 更强的新协调行为，而是复现了 weighted consensus 这一条简单 baseline 的效果。

## 4. Why It Wins The Old Frozen Operator

它能赢旧 frozen Stage 5.1 operator：

```text
stage3_5_batch_1_weighted_consensus_projection
```

主要原因是：

```text
wins the old frozen operator by removing the projection penalty
```

旧 operator 是 `weighted_consensus -> projection`。在当前 Stage 8.4 panel 中，这个 projection 路径带来了稳定但不大的额外损失。新 selected operator 的 `reweighting -> repair` 路径没有这个 penalty，所以它稳定赢旧 frozen operator。

Stage 8.4 结果：

```text
vs frozen Stage 5.1 operator = 36 wins / 0 ties / 0 losses
```

## 5. Why It Does Not Beat Best Baseline

它不能赢 best simple baseline 的原因是：

```text
stage8_3_selected_operator behavior is numerically identical to weighted_consensus
```

因此当 `weighted_consensus` 是 best baseline 时，selected operator 只能打平；当 `simple_consensus` 更好时，selected operator 会输。

Stage 8.4 结果：

```text
vs best simple baseline = 0 wins / 24 ties / 12 losses
```

其中：

```text
weighted_consensus best baseline cases = 24
simple_consensus best baseline cases = 12
```

## 6. Where It Loses

Loss cases 集中在：

```text
synthetic_high_overlap_panel = 9 cases
synthetic_medium_overlap_panel = 3 cases
```

所有 12 个 loss cases 的 best baseline 都是：

```text
simple_consensus
```

更具体地说：

```text
all high-overlap cases
seed-0 medium-overlap cases
```

这说明当前 proposal construction / reward weighting 下，reward-weighted coordination 在这些情形里偏离了更稳的 simple averaging。

## 7. Boundary

Stage 8.5:

```text
FE_total = 0
inherited_stage8_4_FE_total = 1296
objective_loop_executed = false
new_objective_evaluation_used = false
```

保留：

```text
no LLM call
no new candidate generation
no selected-operator revision
no evolution/search
no validation feedback
no test feedback
no BaseOpt modification
not a final objective-value performance claim
not a SOTA claim
```

## 8. Current Diagnosis

```text
primary_diagnosis = selected_operator_equivalent_to_weighted_consensus_baseline
secondary_diagnosis = simple_consensus_beats_selected_operator_on_high_and_seed0_medium_cases
why_win_old_frozen = stage8_3_selected_operator removes the frozen Stage 5.1 projection penalty
why_not_beat_best_baseline = stage8_3_selected_operator behavior is numerically identical to weighted_consensus
```

## 9. Next Step

Recommended next stage:

```text
Stage 8.6 proposal-state/operator-family ablation before official claims
```

Stage 8.6 should not start from a SOTA claim. It should isolate whether the current gap comes from:

```text
operator family degenerating to weighted consensus
proposal reward signal being too aligned with weighted consensus
simple consensus being more robust in high-overlap cases
repair/projection semantics adding or removing penalty without adding new behavior
objective-loop proposal construction making learned operators indistinguishable from simple baselines
```
