# Stage 8.3 Objective-Level Utility Evidence Selection

创建日期：2026-06-21  
执行者：Codex  
阶段边界：Stage 8.3 只读取 Stage 8.2 utility_report.json 和相关已冻结报告，把 objective-level utility evidence 转换为 selection decision。它不调用 LLM，不生成新候选，不运行 evolution/search，不执行 AST，不重新跑 objective loop，不做新 objective evaluation，不使用 validation/test feedback，不修改 BaseOpt，也不声称 SOTA 或 final performance improvement。

## 1. Goal

Stage 8.3 回答的问题是：

```text
在 Stage 8.2 已经产生 objective-level utility evidence 后，
哪个 LOCO candidate 应该进入下一步 large-scale objective panel？
```

本阶段不是静态审计，也不是新一轮优化实验。它是一个 evidence-to-selection gate：

```text
Stage 8.2 utility evidence
-> rank LOCO candidates by objective_final_best
-> select the utility-positive candidate
-> write bounded selection decision
-> keep test/validation/runtime feedback sealed
```

## 2. Inputs

Stage 8.3 只读取：

```text
artifacts/selection_audit/stage8_1/selection_decision.json
artifacts/objective_eval/stage8_2/pilot_report.json
artifacts/objective_eval/stage8_2/utility_report.json
artifacts/objective_eval/stage8_2/fe_ledger.json
```

核心证据源是 Stage 8.2 utility_report.json。

## 3. Selection Rule

候选范围只包括 Stage 8.2 utility report 中的 LOCO candidates：

```text
frozen_stage5_selected_operator
selection_ready_stage8_operator
```

排序规则：

```text
primary key = objective_final_best
direction = ascending
tie breaker = candidate_id
```

当前选择：

```text
selected_candidate_id = stage3_5_batch_1_reweighting_repair
previous_frozen_candidate_id = stage3_5_batch_1_weighted_consensus_projection
selected_candidate_final_best = 15.625468195938
previous_frozen_candidate_final_best = 15.688775831979
objective_utility_delta_vs_previous_frozen = -0.063307636041
```

这个结果只说明 Stage 8.2 的受控 objective-level pilot 里，新的 selection-ready operator 优于 frozen Stage 5.1 selected operator。它不是 large-scale benchmark success，也不是 SOTA claim。

## 4. FE Accounting

Stage 8.3 不新增 objective evaluation：

```text
FE_grouping = 0
FE_proposal = 0
FE_coordination_extra = 0
FE_repair = 0
FE_global_objective = 0
FE_total = 0
inherited_stage8_2_FE_total = 36
```

Stage 8.3 只做 selection over evidence，不运行 objective loop。

## 5. Outputs

Stage 8.3 produces:

```text
artifacts/selection_audit/stage8_3/objective_utility_evidence_table.jsonl
artifacts/selection_audit/stage8_3/objective_utility_selection_decision.json
artifacts/selection_audit/stage8_3/objective_utility_selection_report.json
artifacts/selection_audit/stage8_3/fe_ledger.json
artifacts/selection_audit/stage8_3/runtime_boundary.json
artifacts/selection_audit/stage8_3/next_route_decision.json
```

The selected operator status is:

```text
OBJECTIVE_UTILITY_SELECTED_NOT_FINAL_NOT_FROZEN_FOR_TEST
```

Allowed next use:

```text
large-scale objective panel evaluation under locked protocol
```

## 6. Boundary Flags

Stage 8.3 preserves:

```text
no LLM call
no new candidate generation
no selected-operator revision
no evolution/search run
no objective-loop execution
no new objective evaluation
no validation feedback
no test feedback
no test-feedback tuning
no BaseOpt modification
no optimizer/controller/scheduler generation
not a SOTA claim
not a final objective-value performance claim
```

## 7. Current Result

```text
status = PASS
source_stage = 8.2
selection_scope = objective_level_utility_evidence_selection
selected_candidate_id = stage3_5_batch_1_reweighting_repair
previous_frozen_candidate_id = stage3_5_batch_1_weighted_consensus_projection
objective_level_utility_evidence_used = true
objective_loop_executed = false
objective_evaluation_used = false
FE_total = 0
inherited_stage8_2_FE_total = 36
next_status = READY_FOR_STAGE8_4_LARGE_SCALE_OBJECTIVE_PANEL
```

## 8. Next Step

The next stage should be:

```text
Stage 8.4: large-scale objective panel evaluation under locked protocol
```

Stage 8.4 is where the selected operator must stop living only in pilot evidence and start being tested on a larger objective-level panel. It must still keep BaseOpt fixed, count all FE, avoid test feedback, and avoid SOTA claims until a proper benchmark comparison exists.
