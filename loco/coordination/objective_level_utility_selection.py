"""Stage 8.3 objective-level utility evidence selection.

This stage consumes the Stage 8.2 objective-level utility report and turns it
into a bounded selection decision. It does not rerun the objective loop,
evaluate objectives, call LLMs, generate candidates, or use validation/test
feedback.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence


STAGE = "8.3"
EVIDENCE_SCHEMA_VERSION = "loco.stage8_3_objective_utility_evidence_row.v1"
DECISION_SCHEMA_VERSION = "loco.stage8_3_objective_utility_selection_decision.v1"
REPORT_SCHEMA_VERSION = "loco.stage8_3_objective_utility_selection_report.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_3_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_3_runtime_boundary.v1"


def run_stage8_3_objective_level_utility_selection(
    *,
    stage8_1_selection_decision_path: Path | str,
    stage8_2_pilot_report_path: Path | str,
    stage8_2_utility_report_path: Path | str,
    stage8_2_fe_ledger_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Select a LOCO candidate using frozen Stage 8.2 utility evidence."""

    stage8_1_decision = _read_json(Path(stage8_1_selection_decision_path))
    pilot_report = _read_json(Path(stage8_2_pilot_report_path))
    utility_report = _read_json(Path(stage8_2_utility_report_path))
    stage8_2_ledger = _read_json(Path(stage8_2_fe_ledger_path))
    _validate_inputs(stage8_1_decision, pilot_report, utility_report, stage8_2_ledger)

    evidence_rows = _build_evidence_rows(stage8_1_decision, utility_report)
    selected = evidence_rows[0]
    previous = next(
        row for row in evidence_rows if row["role"] == "previous_frozen_stage5_operator"
    )
    decision = _build_selection_decision(selected, previous)
    ledger = _build_fe_ledger(stage8_2_ledger)
    boundary = _build_runtime_boundary()
    report = _build_report(
        selected=selected,
        previous=previous,
        decision=decision,
        evidence_rows=evidence_rows,
        inherited_stage8_2_fe_total=int(stage8_2_ledger["FE_total"]),
    )
    route = _build_route()

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_path / "objective_utility_evidence_table.jsonl", evidence_rows)
    _write_json(output_path / "objective_utility_selection_decision.json", decision)
    _write_json(output_path / "objective_utility_selection_report.json", report)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", route)
    return report


def _validate_inputs(
    stage8_1_decision: Mapping[str, Any],
    pilot_report: Mapping[str, Any],
    utility_report: Mapping[str, Any],
    stage8_2_ledger: Mapping[str, Any],
) -> None:
    if stage8_1_decision.get("stage") != "8.1":
        raise ValueError("Stage 8.3 requires the Stage 8.1 selection decision.")
    if stage8_1_decision.get("status") != "PASS":
        raise ValueError("Stage 8.1 selection decision must pass.")
    if pilot_report.get("stage") != "8.2":
        raise ValueError("Stage 8.3 requires the Stage 8.2 pilot report.")
    if pilot_report.get("status") != "PASS":
        raise ValueError("Stage 8.2 pilot report must pass.")
    if (
        pilot_report.get("next_status")
        != "READY_FOR_STAGE8_3_TRAIN_ONLY_OR_VALIDATION_SELECTION"
    ):
        raise ValueError("Stage 8.2 is not ready for Stage 8.3 selection.")
    if pilot_report.get("objective_utility_evaluated") is not True:
        raise ValueError("Stage 8.3 requires objective-level utility evidence.")
    if utility_report.get("stage") != "8.2":
        raise ValueError("Stage 8.3 requires the Stage 8.2 utility report.")
    if utility_report.get("status") != "PASS":
        raise ValueError("Stage 8.2 utility report must pass.")
    if utility_report.get("objective_level_utility_evaluated") is not True:
        raise ValueError("Stage 8.2 utility report lacks objective utility evidence.")
    if (
        utility_report.get("selection_ready_improved_over_frozen_selected_operator")
        is not True
    ):
        raise ValueError(
            "Stage 8.3 requires a utility-positive selection-ready candidate."
        )
    if stage8_2_ledger.get("stage") != "8.2":
        raise ValueError("Stage 8.3 requires the Stage 8.2 FE ledger.")
    for source in [stage8_1_decision, pilot_report, utility_report, stage8_2_ledger]:
        if (
            source.get("not_performance_claim") is not True
            and source.get("not_final_performance_claim") is not True
        ):
            raise ValueError("Stage 8.3 requires claim-boundary preservation.")


def _build_evidence_rows(
    stage8_1_decision: Mapping[str, Any],
    utility_report: Mapping[str, Any],
) -> list[dict[str, Any]]:
    selection_ready_by_id = {
        str(row["candidate_id"]): row
        for row in stage8_1_decision["selection_ready_candidates"]
    }
    method_to_candidate = {
        "frozen_stage5_selected_operator": str(
            utility_report["baseline_selected_candidate_id"]
        ),
        "selection_ready_stage8_operator": str(
            utility_report["selection_ready_candidate_id"]
        ),
    }
    roles = {
        "frozen_stage5_selected_operator": "previous_frozen_stage5_operator",
        "selection_ready_stage8_operator": "stage8_selection_ready_operator",
    }
    rows = []
    for utility_row in utility_report["utility_candidates"]:
        method_name = str(utility_row["method_name"])
        if method_name not in method_to_candidate:
            continue
        candidate_id = method_to_candidate[method_name]
        selection_ready_member = candidate_id in selection_ready_by_id
        source_row = selection_ready_by_id.get(candidate_id, {})
        rows.append(
            {
                "schema_version": EVIDENCE_SCHEMA_VERSION,
                "stage": STAGE,
                "source_stage": "8.2",
                "candidate_id": candidate_id,
                "method_name": method_name,
                "role": roles[method_name],
                "operator_family": str(source_row.get("operator_family", "unknown")),
                "kind_sequence": str(source_row.get("kind_sequence", "unknown")),
                "stage8_1_selection_ready_member": selection_ready_member,
                "objective_final_best": float(utility_row["objective_final_best"]),
                "objective_final_value": float(utility_row["objective_final_value"]),
                "improved_or_equal_steps": int(utility_row["improved_or_equal_steps"]),
                "target_scope": "shared_variables_only",
                "objective_loop_executed_in_stage8_3": False,
                "objective_evaluation_used_in_stage8_3": False,
                "validation_feedback_used": False,
                "test_feedback_used": False,
                "not_final_performance_claim": True,
            }
        )
    if len(rows) != 2:
        raise ValueError("Stage 8.3 requires exactly two LOCO utility candidates.")
    rows.sort(key=lambda row: (row["objective_final_best"], row["candidate_id"]))
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
        row["selected_by_stage8_3"] = rank == 1
    return rows


def _build_selection_decision(
    selected: Mapping[str, Any], previous: Mapping[str, Any]
) -> dict[str, Any]:
    delta = round(
        float(selected["objective_final_best"])
        - float(previous["objective_final_best"]),
        12,
    )
    return {
        "schema_version": DECISION_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.2",
        "selected_candidate_id": str(selected["candidate_id"]),
        "previous_frozen_candidate_id": str(previous["candidate_id"]),
        "selected_operator_status": "OBJECTIVE_UTILITY_SELECTED_NOT_FINAL_NOT_FROZEN_FOR_TEST",
        "allowed_next_use": "large-scale objective panel evaluation under locked protocol",
        "selection_reason": "lowest objective_final_best among Stage 8.2 LOCO candidates",
        "selected_candidate_final_best": float(selected["objective_final_best"]),
        "previous_frozen_candidate_final_best": float(previous["objective_final_best"]),
        "objective_utility_delta_vs_previous_frozen": delta,
        "stage8_1_selection_ready_member": bool(
            selected["stage8_1_selection_ready_member"]
        ),
        "target_scope": "shared_variables_only",
        "objective_level_utility_evidence_used": True,
        "objective_loop_executed": False,
        "objective_evaluation_used": False,
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "reported_results_used_as_runtime_feedback": False,
        "baseopt_modified": False,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_fe_ledger(stage8_2_ledger: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "budget_scope": "objective_level_utility_selection_only",
        "FE_grouping": 0,
        "FE_proposal": 0,
        "FE_coordination_extra": 0,
        "FE_repair": 0,
        "FE_global_objective": 0,
        "FE_total": 0,
        "inherited_stage8_2_FE_total": int(stage8_2_ledger["FE_total"]),
        "objective_evaluation_used": False,
        "objective_loop_executed": False,
        "all_extra_fe_counted": True,
        "not_final_performance_claim": True,
    }


def _build_runtime_boundary() -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "claim_scope": "objective-level utility selection",
        "forbidden_behaviors": {
            "llm_call": False,
            "new_candidate_generation": False,
            "selected_operator_revision": False,
            "evolution_search": False,
            "objective_loop_execution": False,
            "new_objective_evaluation": False,
            "validation_feedback": False,
            "test_feedback": False,
            "test_feedback_tuning": False,
            "baseopt_modification": False,
            "optimizer_generation": False,
            "controller_scheduler_generation": False,
        },
        "forbidden_claims": [
            "SOTA improvement",
            "final objective-value performance improvement",
            "large-scale benchmark success",
        ],
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_report(
    *,
    selected: Mapping[str, Any],
    previous: Mapping[str, Any],
    decision: Mapping[str, Any],
    evidence_rows: Sequence[Mapping[str, Any]],
    inherited_stage8_2_fe_total: int,
) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.2",
        "selection_scope": "objective_level_utility_evidence_selection",
        "selection_decision": "SELECT_STAGE8_OBJECTIVE_UTILITY_CANDIDATE",
        "selected_candidate_id": str(selected["candidate_id"]),
        "previous_frozen_candidate_id": str(previous["candidate_id"]),
        "selected_candidate_final_best": float(selected["objective_final_best"]),
        "previous_frozen_candidate_final_best": float(previous["objective_final_best"]),
        "objective_utility_delta_vs_previous_frozen": float(
            decision["objective_utility_delta_vs_previous_frozen"]
        ),
        "evidence_candidate_count": len(evidence_rows),
        "objective_level_utility_evidence_used": True,
        "objective_loop_executed": False,
        "objective_evaluation_used": False,
        "inherited_stage8_2_FE_total": int(inherited_stage8_2_fe_total),
        "FE_total": 0,
        "next_status": "READY_FOR_STAGE8_4_LARGE_SCALE_OBJECTIVE_PANEL",
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


def _build_route() -> dict[str, Any]:
    return {
        "schema_version": "loco.stage8_3_next_route_decision.v1",
        "stage": STAGE,
        "status": "PASS",
        "decision": "LOCK_OBJECTIVE_UTILITY_SELECTION",
        "decision_reason": (
            "Stage 8.3 selected the utility-positive Stage 8.1 candidate using "
            "the frozen Stage 8.2 objective-level utility evidence."
        ),
        "next_stage": "Stage 8.4",
        "allowed_next_work": "large_scale_objective_panel_evaluation",
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


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )
