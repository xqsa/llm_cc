"""Stage 8.9 failure-honest interpretation over Stage 8.8 evidence.

This stage is interpretation only. It reads the Stage 8.8 conditional-policy
objective-loop artifacts and turns them into a bounded claim surface before any
official-like benchmark or SOTA-targeted claim. It performs no objective-loop
execution and no new objective evaluation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


STAGE = "8.9"
INTERPRETATION_SCHEMA_VERSION = "loco.stage8_9_interpretation_report.v1"
CLAIM_BOUNDARY_SCHEMA_VERSION = "loco.stage8_9_claim_boundary_report.v1"
READINESS_SCHEMA_VERSION = "loco.stage8_9_paper_claim_readiness_report.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_9_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_9_runtime_boundary.v1"

CONDITIONAL_POLICY_NAME = "overlap_reward_reliability_switch_v1"
CONDITIONAL_METHOD = "stage8_7_conditional_policy"

PRIMARY_POSITIVE_CLAIM = (
    "conditional proposal-state coordination fixes weighted-consensus collapse "
    "and recovers simple-preferred overlap regimes in objective-loop execution"
)
PRIMARY_NEGATIVE_BOUNDARY = (
    "conditional policy matches but does not beat the best simple baseline; "
    "not final performance and not SOTA"
)
RESEARCH_MEANING = (
    "the useful object is an overlap/reward-reliability aware coordination "
    "policy over operator families, not another weighted-consensus clone"
)


def run_stage8_9_failure_honest_interpretation(
    *,
    stage8_8_panel_report_path: Path | str,
    stage8_8_win_loss_path: Path | str,
    stage8_8_policy_runtime_path: Path | str,
    stage8_8_fe_ledger_path: Path | str,
    stage8_8_runtime_boundary_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Interpret Stage 8.8 evidence without running new objective work."""

    panel_report = _read_json(Path(stage8_8_panel_report_path))
    win_loss = _read_json(Path(stage8_8_win_loss_path))
    policy_runtime = _read_json(Path(stage8_8_policy_runtime_path))
    fe_ledger = _read_json(Path(stage8_8_fe_ledger_path))
    runtime_boundary = _read_json(Path(stage8_8_runtime_boundary_path))
    _validate_inputs(
        panel_report=panel_report,
        win_loss=win_loss,
        policy_runtime=policy_runtime,
        fe_ledger=fe_ledger,
        runtime_boundary=runtime_boundary,
    )

    ledger = _build_fe_ledger(fe_ledger)
    boundary = _build_runtime_boundary()
    claim_boundary = _build_claim_boundary_report(win_loss)
    readiness = _build_readiness_report()
    route = _build_route()
    interpretation = _build_interpretation_report(
        panel_report=panel_report,
        win_loss=win_loss,
        policy_runtime=policy_runtime,
        ledger=ledger,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_json(output_path / "interpretation_report.json", interpretation)
    _write_json(output_path / "claim_boundary_report.json", claim_boundary)
    _write_json(output_path / "paper_claim_readiness_report.json", readiness)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", route)
    return interpretation


def _validate_inputs(
    *,
    panel_report: Mapping[str, Any],
    win_loss: Mapping[str, Any],
    policy_runtime: Mapping[str, Any],
    fe_ledger: Mapping[str, Any],
    runtime_boundary: Mapping[str, Any],
) -> None:
    if panel_report.get("stage") != "8.8" or panel_report.get("status") != "PASS":
        raise ValueError("Stage 8.9 requires a passing Stage 8.8 panel report.")
    if win_loss.get("stage") != "8.8" or win_loss.get("status") != "PASS":
        raise ValueError("Stage 8.9 requires a passing Stage 8.8 win/loss report.")
    if policy_runtime.get("stage") != "8.8" or policy_runtime.get("status") != "PASS":
        raise ValueError(
            "Stage 8.9 requires a passing Stage 8.8 policy runtime report."
        )
    if fe_ledger.get("stage") != "8.8" or fe_ledger.get("status") != "PASS":
        raise ValueError("Stage 8.9 requires a passing Stage 8.8 FE ledger.")
    if (
        runtime_boundary.get("stage") != "8.8"
        or runtime_boundary.get("status") != "PASS"
    ):
        raise ValueError("Stage 8.9 requires a passing Stage 8.8 boundary report.")
    if panel_report.get("objective_loop_executed") is not True:
        raise ValueError("Stage 8.9 requires objective-loop evidence from Stage 8.8.")
    if panel_report.get("new_objective_evaluation_used") is not True:
        raise ValueError("Stage 8.9 requires Stage 8.8 objective-evaluation evidence.")
    if panel_report.get("conditional_policy_name") != CONDITIONAL_POLICY_NAME:
        raise ValueError("Stage 8.9 received the wrong conditional policy evidence.")
    if panel_report.get("not_final_performance_claim") is not True:
        raise ValueError("Stage 8.9 requires Stage 8.8 claim-boundary preservation.")
    if panel_report.get("not_sota_claim") is not True:
        raise ValueError("Stage 8.9 requires Stage 8.8 SOTA-boundary preservation.")
    if (
        runtime_boundary.get("forbidden_behaviors", {}).get("test_feedback")
        is not False
    ):
        raise ValueError("Stage 8.9 refuses test-feedback-contaminated inputs.")
    if (
        runtime_boundary.get("forbidden_behaviors", {}).get("validation_feedback")
        is not False
    ):
        raise ValueError("Stage 8.9 refuses validation-feedback-contaminated inputs.")
    if int(fe_ledger["FE_total"]) != int(panel_report["FE_total"]):
        raise ValueError("Stage 8.8 FE ledger does not match the panel report.")
    if win_loss["conditional_vs_best_baseline"] != {
        "loss": 0,
        "tie": 36,
        "win": 0,
    }:
        raise ValueError("Stage 8.9 expects the Stage 8.8 best-baseline tie result.")


def _build_interpretation_report(
    *,
    panel_report: Mapping[str, Any],
    win_loss: Mapping[str, Any],
    policy_runtime: Mapping[str, Any],
    ledger: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": INTERPRETATION_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.8",
        "interpretation_scope": "failure_honest_stage8_8_interpretation",
        "selected_candidate_id": str(panel_report["selected_candidate_id"]),
        "previous_frozen_candidate_id": str(
            panel_report["previous_frozen_candidate_id"]
        ),
        "conditional_policy_name": CONDITIONAL_POLICY_NAME,
        "method_name": CONDITIONAL_METHOD,
        "stage8_8_result_interpreted": True,
        "positive_claim_is_bounded": True,
        "negative_boundary_is_explicit": True,
        "best_baseline_not_beaten_is_recorded": True,
        "conditional_policy_utility_is_recorded": True,
        "primary_positive_claim": PRIMARY_POSITIVE_CLAIM,
        "primary_negative_boundary": PRIMARY_NEGATIVE_BOUNDARY,
        "research_meaning": RESEARCH_MEANING,
        "conditional_vs_stage8_3_selected_operator": dict(
            win_loss["conditional_vs_stage8_3_selected_operator"]
        ),
        "conditional_vs_weighted_consensus": dict(
            win_loss["conditional_vs_weighted_consensus"]
        ),
        "conditional_vs_simple_consensus": dict(
            win_loss["conditional_vs_simple_consensus"]
        ),
        "conditional_vs_best_baseline": dict(win_loss["conditional_vs_best_baseline"]),
        "simple_preferred_case_recovery_count": int(
            win_loss["simple_preferred_case_recovery_count"]
        ),
        "weighted_sufficient_case_regression_count": int(
            win_loss["weighted_sufficient_case_regression_count"]
        ),
        "conditional_policy_not_equivalent_to_weighted_consensus": bool(
            policy_runtime["conditional_policy_not_equivalent_to_weighted_consensus"]
        ),
        "switch_to_simple_trace_row_count": int(
            policy_runtime["switch_to_simple_trace_row_count"]
        ),
        "keep_weighted_trace_row_count": int(
            policy_runtime["keep_weighted_trace_row_count"]
        ),
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "FE_total": int(ledger["FE_total"]),
        "inherited_stage8_8_FE_total": int(ledger["inherited_stage8_8_FE_total"]),
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "selected_operator_revision_used": False,
        "evolution_search_used": False,
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "reported_results_used_as_runtime_feedback": False,
        "baseopt_modified": False,
        "optimizer_generation_used": False,
        "controller_scheduler_generation_used": False,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_claim_boundary_report(win_loss: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": CLAIM_BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.8",
        "claim_scope": "failure-honest interpretation before official claims",
        "positive_claim_allowed": True,
        "positive_claim": PRIMARY_POSITIVE_CLAIM,
        "negative_boundary": PRIMARY_NEGATIVE_BOUNDARY,
        "conditional_vs_best_baseline": dict(win_loss["conditional_vs_best_baseline"]),
        "best_baseline_not_beaten": True,
        "blocked_claim_reason": (
            "conditional policy ties but does not beat the best simple baseline"
        ),
        "official_benchmark_claim_allowed": False,
        "sota_claim_allowed": False,
        "final_performance_claim_allowed": False,
        "allowed_paper_claim": (
            "On the locked synthetic objective panel, the conditional coordination "
            "policy recovers the 12 simple-preferred cases and ties the best "
            "simple baseline without claiming final performance."
        ),
        "forbidden_claims": [
            "official CEC2013 benchmark success",
            "SOTA improvement",
            "final objective-value performance superiority",
            "BaseOpt improvement",
        ],
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_readiness_report() -> dict[str, Any]:
    return {
        "schema_version": READINESS_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.8",
        "method_claim_ready": True,
        "synthetic_panel_claim_ready": True,
        "paper_experiment_paragraph_ready": True,
        "official_benchmark_claim_ready": False,
        "sota_claim_ready": False,
        "final_performance_claim_ready": False,
        "ready_claim_summary": (
            "Failure-honest synthetic-panel paragraph is ready: conditional "
            "coordination repairs weighted-consensus collapse but only matches "
            "the best baseline."
        ),
        "blocked_claim_summary": (
            "Official/SOTA/final-performance claims require an official-like panel "
            "or a policy-generalization decision after Stage 8.9."
        ),
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_fe_ledger(stage8_8_ledger: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "budget_scope": "failure_honest_interpretation_only",
        "FE_grouping": 0,
        "FE_proposal": 0,
        "FE_coordination_extra": 0,
        "FE_repair": 0,
        "FE_global_objective": 0,
        "FE_total": 0,
        "inherited_stage8_8_FE_total": int(stage8_8_ledger["FE_total"]),
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "not_final_performance_claim": True,
    }


def _build_runtime_boundary() -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "claim_scope": "failure-honest Stage 8.8 interpretation",
        "legal_inputs": [
            "artifacts/objective_eval/stage8_8/panel_report.json",
            "artifacts/objective_eval/stage8_8/win_loss_report.json",
            "artifacts/objective_eval/stage8_8/conditional_policy_runtime_report.json",
            "artifacts/objective_eval/stage8_8/fe_ledger.json",
            "artifacts/objective_eval/stage8_8/runtime_boundary.json",
        ],
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "forbidden_behaviors": {
            "llm_call": False,
            "new_candidate_generation": False,
            "selected_operator_revision": False,
            "evolution_search": False,
            "objective_loop_execution": False,
            "new_objective_evaluation": False,
            "validation_feedback": False,
            "test_feedback": False,
            "reported_results_runtime_feedback": False,
            "baseopt_modification": False,
            "optimizer_generation": False,
            "controller_scheduler_generation": False,
        },
        "forbidden_claims": [
            "SOTA improvement",
            "final objective-value performance improvement",
            "official CEC2013 large-scale benchmark success",
            "BaseOpt improvement",
        ],
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_route() -> dict[str, Any]:
    return {
        "schema_version": "loco.stage8_9_next_route_decision.v1",
        "stage": STAGE,
        "status": "PASS",
        "decision": (
            "READY_FOR_STAGE8_10_OFFICIAL_LIKE_PANEL_OR_POLICY_GENERALIZATION_DECISION"
        ),
        "decision_reason": (
            "Stage 8.9 records that the conditional policy has bounded synthetic "
            "utility but only ties the best simple baseline, so the next step must "
            "choose official-like evaluation or further policy generalization."
        ),
        "next_stage": "Stage 8.10",
        "allowed_next_work": "official_like_panel_or_policy_generalization_decision",
        "use_validation_feedback": False,
        "use_test_feedback": False,
        "use_reported_results_as_runtime_feedback": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
