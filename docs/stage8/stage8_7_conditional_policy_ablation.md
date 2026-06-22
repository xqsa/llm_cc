# Stage 8.7 Conditional Proposal-State Policy Ablation

创建日期：2026-06-22  
执行者：Codex  
阶段边界：Stage 8.7 只读取 Stage 8.6 artifacts，测试一个 overlap/reward-reliability aware conditional policy。它不执行 objective loop，不做 new objective evaluation，不调用 LLM，不生成新 candidate，不修改 selected operator，不使用 validation/test feedback，不修改 BaseOpt，也不声称 SOTA 或 final objective-value performance improvement。

## 1. Goal

Stage 8.7 回答：

```text
能否让 coordination operator 在 proposal-state 上做条件切换，
从而不再退化成 weighted_consensus，
并恢复 simple_consensus 更强的 high/medium-overlap cases？
```

## 2. Inputs

Stage 8.7 只读取：

```text
artifacts/objective_eval/stage8_6/ablation_case_table.jsonl
artifacts/objective_eval/stage8_6/ablation_summary.json
artifacts/objective_eval/stage8_6/operator_family_ablation_report.json
artifacts/objective_eval/stage8_6/proposal_state_ablation_report.json
```

## 3. Conditional Policy

Policy name:

```text
overlap_reward_reliability_switch_v1
```

Rule:

```text
use simple_consensus when overlap is medium/high and reward-weighted behavior is unreliable;
otherwise keep weighted_consensus
```

Stage 8.7 uses these proposal-state features:

```text
overlap_degree
reward_reliability
weighted_vs_simple_final_best_delta
selected_minus_simple_mean_update_size
```

## 4. Result

```text
status = PASS
case_count = 36
simple_preferred_regime_count = 12
weighted_sufficient_regime_count = 24
simple_preferred_regime_recovery_count = 12
weighted_sufficient_regression_count = 0
conditional_policy_not_equivalent_to_weighted_consensus = true
family_collapse_gate_passed = true
FE_total = 0
```

This means Stage 8.7 does not prove final objective-loop performance. It proves the bounded repair direction is coherent: the policy switches exactly on the regimes where Stage 8.6 showed simple_consensus was needed, while preserving weighted_consensus where it was already sufficient.

## 5. Boundary

Stage 8.7 preserves:

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

## 6. Next Step

Recommended next stage:

```text
Stage 8.8 objective-loop rerun for conditional policy
```

Stage 8.8 should place the conditional policy into the objective-level loop and compare it against simple_consensus, weighted_consensus, the old frozen operator, and the Stage 8.3 selected operator under counted FE. Until that rerun exists, Stage 8.7 remains a policy-ablation gate, not a benchmark-performance claim.
