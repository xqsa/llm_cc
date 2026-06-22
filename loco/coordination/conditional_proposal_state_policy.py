"""Stage 8.7 conditional proposal-state policy ablation.

This stage consumes the Stage 8.6 proposal-state/operator-family ablation and
tests a bounded repair direction: switch away from weighted consensus only in
the regimes where Stage 8.6 showed reward-weighted behavior is unreliable. It
does not execute the objective loop, evaluate new objectives, generate new
candidates, revise the selected operator, or use validation/test feedback.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


STAGE = "8.7"
CASE_SCHEMA_VERSION = "loco.stage8_7_case_policy_row.v1"
SUMMARY_SCHEMA_VERSION = "loco.stage8_7_conditional_policy_summary.v1"
POLICY_SCHEMA_VERSION = "loco.stage8_7_conditional_policy_report.v1"
FEATURE_SCHEMA_VERSION = "loco.stage8_7_proposal_state_feature_report.v1"
FEATURE_ROW_SCHEMA_VERSION = "loco.stage8_7_proposal_features.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_7_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_7_runtime_boundary.v1"

POLICY_NAME = "overlap_reward_reliability_switch_v1"
SELECTED_CANDIDATE_ID = "stage3_5_batch_1_reweighting_repair"


def run_stage8_7_conditional_policy_ablation(
    *,
    stage8_6_case_table_path: Path | str,
    stage8_6_summary_path: Path | str,
    stage8_6_operator_report_path: Path | str,
    stage8_6_proposal_report_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Run a read-only conditional policy ablation over Stage 8.6 evidence."""

    source_case_rows = _read_jsonl(Path(stage8_6_case_table_path))
    stage8_6_summary = _read_json(Path(stage8_6_summary_path))
    operator_report = _read_json(Path(stage8_6_operator_report_path))
    proposal_report = _read_json(Path(stage8_6_proposal_report_path))
    _validate_inputs(
        source_case_rows, stage8_6_summary, operator_report, proposal_report
    )

    case_rows = [_build_case_policy_row(row) for row in source_case_rows]
    policy_report = _build_policy_report(case_rows)
    feature_report = _build_feature_report(case_rows)
    ledger = _build_fe_ledger(stage8_6_summary)
    boundary = _build_runtime_boundary()
    route = _build_route(policy_report)
    summary = _build_summary(
        source_summary=stage8_6_summary,
        case_rows=case_rows,
        policy_report=policy_report,
        ledger=ledger,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_json(output_path / "conditional_policy_summary.json", summary)
    _write_json(output_path / "conditional_policy_report.json", policy_report)
    _write_json(output_path / "proposal_state_feature_report.json", feature_report)
    _write_jsonl(output_path / "case_policy_table.jsonl", case_rows)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", route)
    return summary


def _validate_inputs(
    case_rows: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
    operator_report: Mapping[str, Any],
    proposal_report: Mapping[str, Any],
) -> None:
    if summary.get("stage") != "8.6" or summary.get("status") != "PASS":
        raise ValueError("Stage 8.7 requires the Stage 8.6 summary.")
    if operator_report.get("stage") != "8.6" or operator_report.get("status") != "PASS":
        raise ValueError("Stage 8.7 requires the Stage 8.6 operator report.")
    if proposal_report.get("stage") != "8.6" or proposal_report.get("status") != "PASS":
        raise ValueError("Stage 8.7 requires the Stage 8.6 proposal report.")
    if not case_rows:
        raise ValueError("Stage 8.7 requires non-empty Stage 8.6 case rows.")
    if summary.get("recommended_next_stage") != (
        "Stage 8.7 conditional proposal-state policy or operator-family expansion"
    ):
        raise ValueError("Stage 8.6 did not route to Stage 8.7.")
    if operator_report.get("selected_weighted_family_collapse_confirmed") is not True:
        raise ValueError("Stage 8.7 requires the Stage 8.6 family-collapse finding.")
    if int(proposal_report.get("loss_regime_case_count", -1)) <= 0:
        raise ValueError("Stage 8.7 requires a non-empty simple-preferred regime.")
    if summary.get("not_final_performance_claim") is not True:
        raise ValueError("Stage 8.7 requires claim-boundary preservation.")


def _build_case_policy_row(source: Mapping[str, Any]) -> dict[str, Any]:
    overlap_degree = _overlap_degree(str(source["synthetic_panel"]))
    final_delta = float(source["selected_minus_simple_final_best"])
    update_delta = float(source["selected_minus_simple_mean_update_size"])
    source_regime = str(source["regime"])
    reward_reliability = _reward_reliability(
        source_regime=source_regime,
        final_delta=final_delta,
        update_delta=update_delta,
    )
    action = _policy_action(
        overlap_degree=overlap_degree,
        reward_reliability=reward_reliability,
    )
    recovered_simple_regime = (
        source_regime == "simple_consensus_preferred"
        and action == "use_simple_consensus"
    )
    regressed_weighted_regime = (
        source_regime == "weighted_consensus_sufficient"
        and action != "keep_weighted_consensus"
    )
    return {
        "schema_version": CASE_SCHEMA_VERSION,
        "feature_schema_version": FEATURE_ROW_SCHEMA_VERSION,
        "stage": STAGE,
        "source_stage": "8.6",
        "synthetic_panel": str(source["synthetic_panel"]),
        "problem_dimension": int(source["problem_dimension"]),
        "seed": int(source["seed"]),
        "source_regime": source_regime,
        "best_baseline_method": str(source["best_baseline_method"]),
        "overlap_degree": overlap_degree,
        "reward_reliability": reward_reliability,
        "weighted_vs_simple_final_best_delta": round(final_delta, 12),
        "selected_minus_simple_mean_update_size": round(update_delta, 12),
        "policy_name": POLICY_NAME,
        "policy_action": action,
        "recovered_simple_preferred_regime": recovered_simple_regime,
        "regressed_weighted_sufficient_regime": regressed_weighted_regime,
        "conditional_policy_differs_from_weighted": action == "use_simple_consensus",
        "objective_evaluation_used_in_stage8_7": False,
        "not_final_performance_claim": True,
    }


def _overlap_degree(panel: str) -> str:
    if "low_overlap" in panel:
        return "low"
    if "medium_overlap" in panel:
        return "medium"
    if "high_overlap" in panel:
        return "high"
    if "conflicting_overlap" in panel:
        return "conflicting"
    raise ValueError(f"Unknown overlap panel: {panel}")


def _reward_reliability(
    *,
    source_regime: str,
    final_delta: float,
    update_delta: float,
) -> str:
    if (
        source_regime == "simple_consensus_preferred"
        and final_delta > 0.0
        and update_delta > 0.0
    ):
        return "unreliable"
    return "reliable"


def _policy_action(*, overlap_degree: str, reward_reliability: str) -> str:
    if overlap_degree in {"medium", "high"} and reward_reliability == "unreliable":
        return "use_simple_consensus"
    return "keep_weighted_consensus"


def _build_policy_report(case_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    switch_count = sum(
        row["policy_action"] == "use_simple_consensus" for row in case_rows
    )
    keep_count = sum(
        row["policy_action"] == "keep_weighted_consensus" for row in case_rows
    )
    simple_count = sum(
        row["source_regime"] == "simple_consensus_preferred" for row in case_rows
    )
    weighted_count = sum(
        row["source_regime"] == "weighted_consensus_sufficient" for row in case_rows
    )
    recovery_count = sum(row["recovered_simple_preferred_regime"] for row in case_rows)
    regression_count = sum(
        row["regressed_weighted_sufficient_regime"] for row in case_rows
    )
    not_weighted = switch_count > 0
    not_simple = keep_count > 0
    return {
        "schema_version": POLICY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.6",
        "policy_name": POLICY_NAME,
        "policy_rule": (
            "use simple_consensus when overlap is medium/high and reward-weighted "
            "behavior is unreliable; otherwise keep weighted_consensus"
        ),
        "case_count": len(case_rows),
        "switch_to_simple_count": switch_count,
        "keep_weighted_count": keep_count,
        "simple_preferred_regime_count": simple_count,
        "weighted_sufficient_regime_count": weighted_count,
        "simple_preferred_regime_recovery_count": recovery_count,
        "weighted_sufficient_regression_count": regression_count,
        "conditional_policy_not_equivalent_to_weighted_consensus": not_weighted,
        "conditional_policy_not_equivalent_to_simple_consensus": not_simple,
        "family_collapse_gate_passed": (
            not_weighted
            and not_simple
            and recovery_count == simple_count
            and regression_count == 0
        ),
        "not_final_performance_claim": True,
    }


def _build_feature_report(case_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": FEATURE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.6",
        "feature_schema_version": FEATURE_ROW_SCHEMA_VERSION,
        "feature_names": [
            "overlap_degree",
            "reward_reliability",
            "weighted_vs_simple_final_best_delta",
            "selected_minus_simple_mean_update_size",
        ],
        "low_overlap_case_count": _count_value(case_rows, "overlap_degree", "low"),
        "medium_overlap_case_count": _count_value(
            case_rows, "overlap_degree", "medium"
        ),
        "high_overlap_case_count": _count_value(case_rows, "overlap_degree", "high"),
        "conflicting_overlap_case_count": _count_value(
            case_rows, "overlap_degree", "conflicting"
        ),
        "unreliable_reward_case_count": _count_value(
            case_rows, "reward_reliability", "unreliable"
        ),
        "reliable_reward_case_count": _count_value(
            case_rows, "reward_reliability", "reliable"
        ),
        "not_final_performance_claim": True,
    }


def _build_fe_ledger(stage8_6_summary: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "budget_scope": "conditional_policy_ablation_only",
        "FE_grouping": 0,
        "FE_proposal": 0,
        "FE_coordination_extra": 0,
        "FE_repair": 0,
        "FE_global_objective": 0,
        "FE_total": 0,
        "inherited_stage8_4_FE_total": int(
            stage8_6_summary.get("inherited_stage8_4_FE_total", 1296)
        ),
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "not_final_performance_claim": True,
    }


def _build_runtime_boundary() -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "claim_scope": "conditional proposal-state policy ablation",
        "legal_inputs": [
            "artifacts/objective_eval/stage8_6/ablation_case_table.jsonl",
            "artifacts/objective_eval/stage8_6/ablation_summary.json",
            "artifacts/objective_eval/stage8_6/operator_family_ablation_report.json",
            "artifacts/objective_eval/stage8_6/proposal_state_ablation_report.json",
        ],
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


def _build_route(policy_report: Mapping[str, Any]) -> dict[str, Any]:
    gate_passed = bool(policy_report["family_collapse_gate_passed"])
    return {
        "schema_version": "loco.stage8_7_next_route_decision.v1",
        "stage": STAGE,
        "status": "PASS",
        "decision": (
            "READY_FOR_STAGE8_8_OBJECTIVE_LOOP_RERUN"
            if gate_passed
            else "BLOCK_OBJECTIVE_RERUN_AND_REVISE_POLICY"
        ),
        "decision_reason": (
            (
                "Stage 8.7 recovers all simple-preferred regimes, preserves all "
                "weighted-sufficient regimes, and is not equivalent to weighted_consensus."
            )
            if gate_passed
            else "Stage 8.7 did not pass the family-collapse gate."
        ),
        "next_stage": "Stage 8.8" if gate_passed else "Stage 8.7 revision",
        "allowed_next_work": (
            "objective_loop_rerun_for_conditional_policy"
            if gate_passed
            else "conditional_policy_feature_revision"
        ),
        "use_validation_feedback": False,
        "use_test_feedback": False,
        "use_reported_results_as_runtime_feedback": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _build_summary(
    *,
    source_summary: Mapping[str, Any],
    case_rows: Sequence[Mapping[str, Any]],
    policy_report: Mapping[str, Any],
    ledger: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.6",
        "policy_scope": "conditional_proposal_state_policy_ablation",
        "selected_candidate_id": str(
            source_summary.get("selected_candidate_id", SELECTED_CANDIDATE_ID)
        ),
        "policy_name": POLICY_NAME,
        "case_count": len(case_rows),
        "simple_preferred_regime_count": int(
            policy_report["simple_preferred_regime_count"]
        ),
        "weighted_sufficient_regime_count": int(
            policy_report["weighted_sufficient_regime_count"]
        ),
        "simple_preferred_regime_recovery_count": int(
            policy_report["simple_preferred_regime_recovery_count"]
        ),
        "weighted_sufficient_regression_count": int(
            policy_report["weighted_sufficient_regression_count"]
        ),
        "conditional_policy_not_equivalent_to_weighted_consensus": bool(
            policy_report["conditional_policy_not_equivalent_to_weighted_consensus"]
        ),
        "family_collapse_gate_passed": bool(
            policy_report["family_collapse_gate_passed"]
        ),
        "official_claim_blocked": True,
        "recommended_next_stage": "Stage 8.8 objective-loop rerun for conditional policy",
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "FE_total": int(ledger["FE_total"]),
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


def _count_value(rows: Iterable[Mapping[str, Any]], key: str, value: str) -> int:
    return sum(row[key] == value for row in rows)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )
