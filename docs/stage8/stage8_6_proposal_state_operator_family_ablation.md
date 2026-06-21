# Stage 8.6 Proposal-State / Operator-Family Ablation

创建日期：2026-06-21  
执行者：Codex  
阶段边界：Stage 8.6 只读取 Stage 8.4 / Stage 8.5 artifacts，做 proposal-state 与 operator-family 的诊断性 ablation。它不执行 objective loop，不做 new objective evaluation，不调用 LLM，不生成新 candidate，不修改 selected operator，不使用 validation/test feedback，不修改 BaseOpt，也不声称 SOTA 或 final objective-value performance improvement。

## 1. Goal

Stage 8.6 回答：

```text
Stage 8.5 已经发现 selected operator 等价 weighted_consensus。
那么问题到底来自 operator family 坍缩，还是来自 proposal-state regime？
```

## 2. Inputs

Stage 8.6 只读取：

```text
artifacts/objective_eval/stage8_4/objective_trace.jsonl
artifacts/objective_eval/stage8_4/win_loss_report.json
artifacts/objective_eval/stage8_5/failure_honest_diagnosis_report.json
artifacts/objective_eval/stage8_5/baseline_equivalence_report.json
artifacts/objective_eval/stage8_5/topology_gap_report.json
```

## 3. Operator-Family Finding

核心结论：

```text
operator-family collapse to weighted_consensus
```

Stage 8.6 confirms:

```text
selected_weighted_coord_value_max_abs_delta = 0.0
selected_weighted_update_size_max_abs_delta = 0.0
selected_weighted_final_best_max_abs_delta = 0.0
```

这说明 `stage3_5_batch_1_reweighting_repair` 在 Stage 8.4 panel 上没有形成独立于 weighted_consensus 的新行为。它赢旧 frozen operator 的主要原因仍然是：

```text
removing the projection penalty
```

而不是产生了更强的 coordination family。

## 4. Proposal-State Finding

第二个结论：

```text
simple_consensus is needed in 12 high/medium-overlap cases
```

Stage 8.6 separates the 36 cases into:

```text
weighted_consensus_sufficient = 24 cases
simple_consensus_preferred = 12 cases
```

Loss regimes:

```text
synthetic_high_overlap_panel = 9
synthetic_medium_overlap_panel = 3
best baseline in all loss cases = simple_consensus
```

这说明问题不只是 “selected operator 不够好”，而是当前 proposal-state 没有告诉 operator 何时应该从 reward-weighted behavior 切换到 simple averaging behavior。

## 5. Result

```text
status = PASS
case_count = 36
loss_regime_case_count = 12
weighted_sufficient_case_count = 24
operator_family_collapse_confirmed = true
proposal_state_gap_confirmed = true
official_claim_blocked = true
FE_total = 0
```

## 6. Boundary

Stage 8.6 preserves:

```text
no LLM call
no new candidate generation
no selected-operator revision
no evolution/search
no objective-loop execution
no new objective evaluation
no validation feedback
no test feedback
no BaseOpt modification
not a final objective-value performance claim
not a SOTA claim
```

## 7. Next Step

Recommended next stage:

```text
Stage 8.7 conditional proposal-state policy or operator-family expansion
```

Stage 8.7 should not go to official claims yet. It should test one of two directions:

```text
1. Add proposal-state features that detect when simple_consensus is safer.
2. Expand operator families beyond weighted/reweighting clones toward conditional or simple-consensus-aware coordination.
```

The key target is no longer “run more benchmark cases”. The key target is to prevent the learned family from collapsing to weighted_consensus while preserving the benefit of avoiding projection penalties.
