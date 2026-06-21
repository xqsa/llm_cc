# Stage 7.4 Optional CEC2013 F13/F14 Objective Panel Decision

创建日期：2026-06-21
执行者：Codex
阶段边界：Stage 7.4 是 decision gate。它读取 Stage 7.3 mixed synthetic evidence、Stage 7.3 claim boundary 和 Stage 1 MetaBox CEC2013 smoke evidence，决定是否需要一个可选的 CEC2013 F13/F14 objective panel。它不运行 CEC2013 panel，不做 new objective evaluation，不修改 selected operator，不修改 BaseOpt，也不是 not a final objective-value performance claim 或 not a SOTA claim。

## 1. Decision

Stage 7.4 decision:

```text
decision = RUN_OPTIONAL_CEC2013_F13_F14_PANEL
decision_reason = stage7_3_mixed_synthetic_evidence_needs_real_overlap_panel
```

原因很直接：

```text
Stage 7.3 shows mixed synthetic evidence.
best_overall_method = simple_consensus
selected_loco_operator_rank_overall = 4
```

如果论文要写强 empirical claim，不能只靠当前 synthetic evidence。需要一个明确边界的 real-overlap panel，至少覆盖 F13/F14。

## 2. Legal Inputs

Stage 7.4 只读取：

```text
artifacts/objective_eval/stage7_3/paper_tables_report.json
artifacts/objective_eval/stage7_3/method_ranking.json
artifacts/objective_eval/stage7_3/claim_boundary.json
docs/stage1/metabox_real_smoke_latest.json
docs/stage1/cec2013lsgo_semantics.md
```

It does not run MetaBox or evaluate any objective in Stage 7.4.

## 3. CEC2013 Readiness

Stage 1 smoke evidence says F13/F14 are usable through LOCO's MetaBox adapter:

```text
metabox_smoke_status = PASS
F13 ready = true
F14 ready = true
```

Important CEC2013 semantics:

```text
F13 overlap_semantics = conforming_overlap
F14 overlap_semantics = conflicting_overlap
D_formula = 905
D_api = 1000
shared_variable_count = 95
overlap_ratio = 95 / 905
```

Adapter details:

```text
F13 adapter_mode = implementation_api_adapter
F14 adapter_mode = direct_metabox_dimension
```

This means F13/F14 can be proposed as an optional real-overlap panel, but that panel must explicitly preserve D_formula/D_api semantics and count all extra FE.

## 4. Prepared Protocol

Stage 7.4 prepares but does not execute:

```text
artifacts/objective_eval/stage7_4/cec2013_optional_panel_protocol.json
```

The optional CEC2013 F13/F14 panel is not run in Stage 7.4.

Locked methods:

```text
identity_no_coord
simple_consensus
weighted_consensus
best_reward_select
selected_loco_operator
```

Required execution rules for the optional next stage:

```text
same_budget_across_methods = true
all_extra_fe_counted = true
oracle_and_detected_grouping_reported_separately = true
selected_operator_policy = frozen_no_revision
base_optimizer_policy = fixed_baseopt_no_modification
execution_status = NOT_RUN_IN_STAGE7_4
```

## 5. Outputs

Stage 7.4 produces:

```text
artifacts/objective_eval/stage7_4/cec2013_panel_decision.json
artifacts/objective_eval/stage7_4/cec2013_optional_panel_protocol.json
artifacts/objective_eval/stage7_4/cec2013_readiness_summary.json
artifacts/objective_eval/stage7_4/claim_boundary.json
artifacts/objective_eval/stage7_4/decision_report.json
```

## 6. Claim Boundary

Allowed claims:

```text
Stage 7.4 decides that an optional CEC2013 F13/F14 panel is warranted before strong empirical claims.
Stage 7.4 prepares a bounded protocol for F13/F14 but does not execute it.
A paper draft may still proceed as a failure-honest prototype if it clearly states the Stage 7.3 mixed evidence.
```

Forbidden claims:

```text
official CEC2013 performance claim
F13/F14 objective improvement
final objective-value performance superiority
SOTA improvement
BaseOpt improvement
optimizer generation
```

## 7. Boundary Flags

Stage 7.4 preserves:

```text
no LLM call
no new candidate generation
no selected-operator revision
no evolution/search run
no new objective evaluation
no CEC2013 panel run in Stage 7.4
no test-feedback tuning
no BaseOpt modification
no optimizer/controller/scheduler generation
not a SOTA claim
not a final objective-value performance claim
```

## 8. Next Step

Stage 7.4 next status:

```text
READY_FOR_STAGE7_5_OPTIONAL_CEC2013_PANEL_PROTOCOL_OR_PAPER_DRAFT
```

Recommended next stage:

```text
Stage 7.5: Optional CEC2013 F13/F14 Panel Protocol Or Paper Draft Decision
```

The next decision is practical: either implement a bounded F13/F14 panel runner under the prepared protocol, or start the paper as a failure-honest prototype/methodology paper with Stage 7.3 synthetic results and clear limitations.
