"""Stage 8.35 failure-honest diagnosis for Stage 8.34 bounded checkpoint."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


STAGE = "8.35"
REPORT_SCHEMA_VERSION = "loco.stage8_35_bounded_guarded_checkpoint_diagnosis.v1"
CAUSE_SCHEMA_VERSION = "loco.stage8_35_one_of_six_less_loss_cause_report.v1"
CASE_SCHEMA_VERSION = "loco.stage8_35_case_diagnosis_row.v1"
BRANCH_SCHEMA_VERSION = "loco.stage8_35_guard_branch_diagnosis.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_35_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_35_runtime_boundary.v1"
NEXT_ROUTE_SCHEMA_VERSION = "loco.stage8_35_next_route_decision.v1"

NEXT_STAGE = "Stage 8.36"
NEXT_WORK = "proposal_quality_or_best_reward_reliability_repair_before_formal_panel"
ROOT_CAUSE_SUMMARY = (
    "guard fixes only the reliable-best-reward overcorrection case; most cases "
    "either remain tied or still need objective-level proposal repair"
)


def run_stage8_35_bounded_guarded_checkpoint_diagnosis(
    *,
    stage8_34_checkpoint_report_path: Path | str,
    stage8_34_case_table_path: Path | str,
    stage8_34_win_loss_path: Path | str,
    stage8_34_branch_report_path: Path | str,
    stage8_34_fe_ledger_path: Path | str,
    stage8_34_runtime_boundary_path: Path | str,
    stage8_34_next_route_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Diagnose why Stage 8.34 only reduced loss in one of six cases."""

    checkpoint = _read_json(Path(stage8_34_checkpoint_report_path))
    case_rows_834 = _read_jsonl(Path(stage8_34_case_table_path))
    win_loss = _read_json(Path(stage8_34_win_loss_path))
    branch_834 = _read_json(Path(stage8_34_branch_report_path))
    ledger_834 = _read_json(Path(stage8_34_fe_ledger_path))
    boundary_834 = _read_json(Path(stage8_34_runtime_boundary_path))
    route_834 = _read_json(Path(stage8_34_next_route_path))
    _validate_inputs(
        checkpoint=checkpoint,
        case_rows_834=case_rows_834,
        win_loss=win_loss,
        branch_834=branch_834,
        ledger_834=ledger_834,
        boundary_834=boundary_834,
        route_834=route_834,
    )

    case_rows = _build_case_diagnosis_rows(case_rows_834)
    causes = _build_cause_report(checkpoint, case_rows)
    branch = _build_branch_diagnosis(branch_834)
    ledger = _build_fe_ledger(ledger_834)
    boundary = _build_runtime_boundary()
    route = _build_next_route()
    report = _build_report(
        checkpoint=checkpoint,
        causes=causes,
        branch=branch,
        ledger=ledger,
        route=route,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_json(output_path / "bounded_guarded_checkpoint_diagnosis_report.json", report)
    _write_json(output_path / "one_of_six_less_loss_cause_report.json", causes)
    _write_jsonl(output_path / "case_diagnosis_table.jsonl", case_rows)
    _write_json(output_path / "guard_branch_diagnosis.json", branch)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", route)
    return report


def _validate_inputs(
    *,
    checkpoint: Mapping[str, Any],
    case_rows_834: Sequence[Mapping[str, Any]],
    win_loss: Mapping[str, Any],
    branch_834: Mapping[str, Any],
    ledger_834: Mapping[str, Any],
    boundary_834: Mapping[str, Any],
    route_834: Mapping[str, Any],
) -> None:
    if checkpoint.get("stage") != "8.34" or checkpoint.get("status") != "PASS":
        raise ValueError("Stage 8.35 requires passing Stage 8.34 checkpoint evidence.")
    if int(checkpoint.get("comparison_case_count", -1)) != 6:
        raise ValueError("Stage 8.35 requires the six-case Stage 8.34 surface.")
    if int(checkpoint.get("less_loss_case_count", -1)) != 1:
        raise ValueError("Stage 8.35 is scoped to the one-of-six less-loss diagnosis.")
    if checkpoint.get("checkpoint_promising") is not False:
        raise ValueError("Stage 8.35 requires a non-promising checkpoint.")
    if len(case_rows_834) != 6:
        raise ValueError("Stage 8.35 requires six Stage 8.34 case rows.")
    if win_loss.get("stage") != "8.34" or int(win_loss["less_loss_case_count"]) != 1:
        raise ValueError("Stage 8.35 requires Stage 8.34 win/loss evidence.")
    if branch_834.get("stage") != "8.34":
        raise ValueError("Stage 8.35 requires Stage 8.34 branch evidence.")
    if int(ledger_834.get("FE_total", -1)) != 0:
        raise ValueError("Stage 8.35 requires zero-FE Stage 8.34 replay input.")
    if boundary_834.get("new_objective_evaluation_used") is not False:
        raise ValueError("Stage 8.35 refuses new-objective Stage 8.34 input.")
    if route_834.get("next_stage") != "Stage 8.35":
        raise ValueError("Stage 8.35 requires the Stage 8.34 route.")


def _build_case_diagnosis_rows(
    case_rows_834: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for row in case_rows_834:
        guarded_result = str(row["guarded_vs_best_reward_select_result"])
        less_loss = bool(row["less_loss_vs_stage8_30_behavior"])
        if less_loss:
            label = "explained_less_loss"
            reason = (
                "reliable-best-reward guard reduced the overcorrection delta, "
                "but the case still remained a loss"
            )
        elif guarded_result == "loss":
            label = "remaining_loss"
            reason = (
                "guarded break/owner proposal path did not improve proposal quality "
                "against best_reward_select"
            )
        elif guarded_result == "tie":
            label = "unchanged_tie"
            reason = "no additional objective-level signal to move beyond the inherited tie"
        else:
            label = "unchanged_win"
            reason = "pre-existing win preserved rather than newly created by the guard"
        rows.append(
            {
                "schema_version": CASE_SCHEMA_VERSION,
                "stage": STAGE,
                "source_stage": "8.34",
                "function_id": str(row["function_id"]),
                "seed": int(row["seed"]),
                "guard_action": str(row["guard_action"]),
                "guard_reason": str(row["guard_reason"]),
                "diagnosis_label": label,
                "diagnosis_reason": reason,
                "stage8_30_behavior_vs_best_reward_select_delta": float(
                    row["stage8_30_behavior_vs_best_reward_select_delta"]
                ),
                "guarded_vs_best_reward_select_delta": float(
                    row["guarded_vs_best_reward_select_delta"]
                ),
                "guarded_vs_best_reward_select_result": guarded_result,
                "less_loss_vs_stage8_30_behavior": less_loss,
                "FE_total": 0,
                "not_sota_claim": True,
                "not_final_performance_claim": True,
            }
        )
    return rows


def _build_cause_report(
    checkpoint: Mapping[str, Any], case_rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    labels = Counter(str(row["diagnosis_label"]) for row in case_rows)
    total_loss_count = sum(
        str(row["guarded_vs_best_reward_select_result"]) == "loss"
        for row in case_rows
    )
    return {
        "schema_version": CAUSE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.34",
        "less_loss_case_count": int(checkpoint["less_loss_case_count"]),
        "comparison_case_count": int(checkpoint["comparison_case_count"]),
        "less_loss_rate": float(checkpoint["less_loss_rate"]),
        "total_loss_case_count": int(total_loss_count),
        "remaining_loss_case_count": int(labels["remaining_loss"]),
        "unchanged_case_count": int(checkpoint["unchanged_case_count"]),
        "dominant_cause": "limited_guard_applicability",
        "secondary_cause": "no_new_proposal_or_optimizer_signal",
        "explanation": ROOT_CAUSE_SUMMARY,
        "formal_25_run_recommended_now": False,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_branch_diagnosis(branch_834: Mapping[str, Any]) -> dict[str, Any]:
    case_count = int(branch_834["case_count"])
    trust = int(branch_834["trust_best_reward_count"])
    owner_select = int(branch_834["owner_proposal_select_count"])
    unchanged = int(branch_834["unchanged_or_inherited_count"])
    return {
        "schema_version": BRANCH_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.34",
        "case_count": case_count,
        "trust_best_reward_count": trust,
        "owner_proposal_select_count": owner_select,
        "unchanged_or_inherited_count": unchanged,
        "trust_best_reward_share": trust / case_count,
        "owner_proposal_select_share": owner_select / case_count,
        "unchanged_or_inherited_share": unchanged / case_count,
        "branch_limitation": "guard_applies_to_too_few_cases_to_change_panel_result",
        "FE_total": 0,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_fe_ledger(ledger_834: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "budget_scope": "read_only_stage8_34_failure_diagnosis",
        "inherited_stage8_34_FE_total": int(ledger_834["FE_total"]),
        "FE_grouping": 0,
        "FE_proposal": 0,
        "FE_coordination_extra": 0,
        "FE_repair": 0,
        "FE_global_objective": 0,
        "FE_total": 0,
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "cec_checkpoint_executed": False,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_runtime_boundary() -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "claim_scope": "Stage 8.34 failure diagnosis only",
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "cec_checkpoint_executed": False,
        "formal_25_run_panel_executed": False,
        "forbidden_behaviors": {
            "llm_call": False,
            "new_candidate_generation": False,
            "new_llm_strategy_generation": False,
            "selected_policy_revision": False,
            "evolution_search": False,
            "objective_loop_execution": False,
            "new_objective_evaluation": False,
            "cec_checkpoint_execution": False,
            "formal_25_run_panel_execution": False,
            "validation_feedback": False,
            "test_feedback": False,
            "reported_results_runtime_feedback": False,
            "baseopt_modification": False,
            "optimizer_generation": False,
            "controller_scheduler_generation": False,
        },
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_next_route() -> dict[str, Any]:
    return {
        "schema_version": NEXT_ROUTE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "decision": "BLOCK_FORMAL_PANEL_REPAIR_PROPOSAL_SIGNAL_FIRST",
        "next_stage": NEXT_STAGE,
        "allowed_next_work": NEXT_WORK,
        "run_full_25_run_panel_next": False,
        "run_cec_checkpoint_next": False,
        "run_new_objective_next": False,
        "call_llm_next": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _build_report(
    *,
    checkpoint: Mapping[str, Any],
    causes: Mapping[str, Any],
    branch: Mapping[str, Any],
    ledger: Mapping[str, Any],
    route: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.34",
        "diagnosis_scope": "failure_honest_bounded_guarded_checkpoint_diagnosis",
        "stage8_34_less_loss_case_count": int(checkpoint["less_loss_case_count"]),
        "stage8_34_comparison_case_count": int(checkpoint["comparison_case_count"]),
        "stage8_34_less_loss_rate": float(checkpoint["less_loss_rate"]),
        "stage8_34_checkpoint_promising": bool(checkpoint["checkpoint_promising"]),
        "root_cause_summary": ROOT_CAUSE_SUMMARY,
        "primary_limitation": "limited_guard_applicability",
        "secondary_limitation": "no_new_proposal_or_optimizer_signal",
        "less_loss_case_explained": int(causes["less_loss_case_count"]) == 1,
        "remaining_loss_cases_explained": int(causes["remaining_loss_case_count"]) == 2
        and int(causes["total_loss_case_count"]) == 3,
        "trust_best_reward_share": float(branch["trust_best_reward_share"]),
        "owner_proposal_select_share": float(branch["owner_proposal_select_share"]),
        "formal_25_run_recommended_now": False,
        "recommended_next_stage": route["next_stage"],
        "recommended_next_work": route["allowed_next_work"],
        "FE_total": int(ledger["FE_total"]),
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "cec_checkpoint_executed": False,
        "llm_call_used": False,
        "new_candidate_generation_used": False,
        "new_llm_strategy_generation_used": False,
        "selected_policy_revision_used": False,
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
