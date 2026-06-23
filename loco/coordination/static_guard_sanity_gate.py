"""Stage 8.33 static sanity gate for the Stage 8.32 guard.

This stage is read-only over Stage 8.32 artifacts. It does not run a CEC
checkpoint, does not execute objective loops, and does not launch a 25-run
panel.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from loco.coordination.overcorrection_guard_design import (
    GuardedOwnerTrustPolicy,
    guarded_static_fixtures,
)


STAGE = "8.33"
REPORT_SCHEMA_VERSION = "loco.stage8_33_static_guard_sanity_report.v1"
MATRIX_SCHEMA_VERSION = "loco.stage8_33_guard_decision_matrix.v1"
COLLAPSE_SCHEMA_VERSION = "loco.stage8_33_collapse_audit_report.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_33_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_33_runtime_boundary.v1"
NEXT_ROUTE_SCHEMA_VERSION = "loco.stage8_33_next_route_decision.v1"

REPAIR_POLICY_ID = "stage8_32_guarded_owner_trust_repair_v1"
NEXT_STAGE = "Stage 8.34"
NEXT_WORK = "bounded_guarded_policy_checkpoint"


def run_stage8_33_static_guard_sanity_gate(
    *,
    stage8_32_repair_design_path: Path | str,
    stage8_32_policy_payload_path: Path | str,
    stage8_32_guard_spec_path: Path | str,
    stage8_32_static_coverage_path: Path | str,
    stage8_32_fe_ledger_path: Path | str,
    stage8_32_runtime_boundary_path: Path | str,
    stage8_32_next_route_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Run static guard sanity checks without objective or CEC work."""

    repair_design = _read_json(Path(stage8_32_repair_design_path))
    policy_payload = _read_json(Path(stage8_32_policy_payload_path))
    guard_spec = _read_json(Path(stage8_32_guard_spec_path))
    static_coverage = _read_json(Path(stage8_32_static_coverage_path))
    stage8_32_ledger = _read_json(Path(stage8_32_fe_ledger_path))
    stage8_32_boundary = _read_json(Path(stage8_32_runtime_boundary_path))
    stage8_32_route = _read_json(Path(stage8_32_next_route_path))
    _validate_inputs(
        repair_design=repair_design,
        policy_payload=policy_payload,
        guard_spec=guard_spec,
        static_coverage=static_coverage,
        stage8_32_ledger=stage8_32_ledger,
        stage8_32_boundary=stage8_32_boundary,
        stage8_32_route=stage8_32_route,
    )

    matrix_rows = _build_decision_matrix_rows()
    collapse = _build_collapse_audit_report(matrix_rows, guard_spec)
    ledger = _build_fe_ledger(stage8_32_ledger)
    boundary = _build_runtime_boundary()
    route = _build_next_route(collapse)
    report = _build_report(
        repair_design=repair_design,
        collapse=collapse,
        ledger=ledger,
        route=route,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_json(output_path / "static_guard_sanity_report.json", report)
    _write_jsonl(output_path / "guard_decision_matrix.jsonl", matrix_rows)
    _write_json(output_path / "collapse_audit_report.json", collapse)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", route)
    return report


def _validate_inputs(
    *,
    repair_design: Mapping[str, Any],
    policy_payload: Mapping[str, Any],
    guard_spec: Mapping[str, Any],
    static_coverage: Mapping[str, Any],
    stage8_32_ledger: Mapping[str, Any],
    stage8_32_boundary: Mapping[str, Any],
    stage8_32_route: Mapping[str, Any],
) -> None:
    if repair_design.get("stage") != "8.32" or repair_design.get("status") != "PASS":
        raise ValueError("Stage 8.33 requires a passing Stage 8.32 repair design.")
    if repair_design.get("overcorrection_guard_designed") is not True:
        raise ValueError("Stage 8.33 requires a designed overcorrection guard.")
    if repair_design.get("cec_checkpoint_executed") is not False:
        raise ValueError("Stage 8.33 refuses CEC-executed Stage 8.32 input.")
    if policy_payload.get("strategy_id") != REPAIR_POLICY_ID:
        raise ValueError("Stage 8.33 requires the Stage 8.32 guarded policy payload.")
    if guard_spec.get("guarded_against_overcorrection") is not True:
        raise ValueError("Stage 8.33 requires the Stage 8.32 guard spec.")
    if guard_spec.get("forbidden_degenerate_pattern") != "always_contribution_leader_break":
        raise ValueError("Stage 8.33 requires the overcorrection degeneracy guard.")
    if static_coverage.get("all_required_guard_paths_covered") is not True:
        raise ValueError("Stage 8.33 requires Stage 8.32 guard path coverage.")
    if int(stage8_32_ledger.get("FE_total", -1)) != 0:
        raise ValueError("Stage 8.33 requires zero-FE Stage 8.32 input.")
    if stage8_32_boundary.get("objective_loop_executed") is not False:
        raise ValueError("Stage 8.33 refuses objective-loop Stage 8.32 input.")
    if stage8_32_boundary.get("cec_checkpoint_executed") is not False:
        raise ValueError("Stage 8.33 refuses CEC-checkpoint Stage 8.32 input.")
    if stage8_32_route.get("next_stage") != "Stage 8.33":
        raise ValueError("Stage 8.33 requires the Stage 8.32 route.")
    if stage8_32_route.get("run_full_25_run_panel_next") is not False:
        raise ValueError("Stage 8.33 refuses a 25-run route.")


def _build_decision_matrix_rows() -> list[dict[str, Any]]:
    policy = GuardedOwnerTrustPolicy()
    rows = []
    for fixture in guarded_static_fixtures():
        decision = policy.decide(fixture)
        rows.append(
            {
                "schema_version": MATRIX_SCHEMA_VERSION,
                "stage": STAGE,
                "source_stage": "8.32",
                "fixture_id": str(fixture["fixture_id"]),
                "repair_policy_id": REPAIR_POLICY_ID,
                "input_flags": {
                    key: bool(value)
                    for key, value in fixture.items()
                    if key != "fixture_id"
                },
                "decision": decision,
                "is_break": decision["linkage_decision"] == "break",
                "is_contribution_leader": (
                    decision["shared_variable_owner"] == "contribution_leader"
                ),
                "is_best_reward_trust": (
                    decision["coordination_action"] == "trust_best_reward"
                    and decision["linkage_decision"] == "preserve"
                    and decision["shared_variable_owner"] == "best_reward_group"
                ),
                "FE_total": 0,
                "not_sota_claim": True,
                "not_final_performance_claim": True,
            }
        )
    return rows


def _build_collapse_audit_report(
    matrix_rows: Sequence[Mapping[str, Any]], guard_spec: Mapping[str, Any]
) -> dict[str, Any]:
    decisions = [dict(row["decision"]) for row in matrix_rows]
    action_counts = Counter(str(decision["coordination_action"]) for decision in decisions)
    owner_counts = Counter(str(decision["shared_variable_owner"]) for decision in decisions)
    linkage_counts = Counter(str(decision["linkage_decision"]) for decision in decisions)
    break_rows = [row for row in matrix_rows if bool(row["is_break"])]
    unguarded_break = any(
        row["fixture_id"] != "strong_owner_conflict_best_reward_misleading"
        for row in break_rows
    )
    always_contribution_leader_break = (
        len(matrix_rows) > 0
        and owner_counts["contribution_leader"] == len(matrix_rows)
        and linkage_counts["break"] == len(matrix_rows)
    )
    reliable_row = _row_by_fixture(matrix_rows, "best_reward_reliable_preserve")
    conflict_row = _row_by_fixture(
        matrix_rows, "strong_owner_conflict_best_reward_misleading"
    )
    reliable_trust = bool(reliable_row["is_best_reward_trust"])
    conflict_guarded_break = (
        conflict_row["decision"]["shared_variable_owner"] == "contribution_leader"
        and conflict_row["decision"]["linkage_decision"] == "break"
        and conflict_row["decision"]["coordination_action"] == "owner_proposal_select"
    )
    return {
        "schema_version": COLLAPSE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.32",
        "repair_policy_id": REPAIR_POLICY_ID,
        "forbidden_degenerate_pattern": guard_spec["forbidden_degenerate_pattern"],
        "fixture_count": len(matrix_rows),
        "branch_counts": _zero_filled_counts(
            action_counts,
            [
                "trust_best_reward",
                "owner_proposal_select",
                "shrinkage_repair",
                "weighted_consensus",
                "simple_consensus",
            ],
        ),
        "owner_counts": _zero_filled_counts(
            owner_counts,
            [
                "best_reward_group",
                "contribution_leader",
                "historical_owner",
                "multi_owner",
            ],
        ),
        "linkage_decision_counts": _zero_filled_counts(
            linkage_counts, ["preserve", "break"]
        ),
        "always_contribution_leader_break_detected": bool(
            always_contribution_leader_break
        ),
        "unguarded_break_detected": bool(unguarded_break),
        "guard_not_collapsed": not bool(always_contribution_leader_break)
        and not bool(unguarded_break),
        "reliable_best_reward_preserves_trust": reliable_trust,
        "misleading_conflict_breaks_only_when_guarded": bool(
            conflict_guarded_break and len(break_rows) == 1
        ),
        "allow_bounded_checkpoint_next": (
            not bool(always_contribution_leader_break)
            and not bool(unguarded_break)
            and reliable_trust
            and conflict_guarded_break
        ),
        "FE_total": 0,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_fe_ledger(stage8_32_ledger: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "budget_scope": "static_guard_sanity_no_objective_no_cec_no_25run",
        "inherited_stage8_32_FE_total": int(stage8_32_ledger["FE_total"]),
        "FE_grouping": 0,
        "FE_proposal": 0,
        "FE_coordination_extra": 0,
        "FE_repair": 0,
        "FE_global_objective": 0,
        "FE_total": 0,
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "cec_checkpoint_executed": False,
        "formal_25_run_panel_executed": False,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_runtime_boundary() -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "claim_scope": "static guard sanity only",
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


def _build_next_route(collapse: Mapping[str, Any]) -> dict[str, Any]:
    allow_bounded = bool(collapse["allow_bounded_checkpoint_next"])
    return {
        "schema_version": NEXT_ROUTE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "decision": (
            "ALLOW_BOUNDED_GUARDED_POLICY_CHECKPOINT"
            if allow_bounded
            else "BLOCK_CHECKPOINT_REPAIR_STATIC_GUARD_FIRST"
        ),
        "next_stage": NEXT_STAGE,
        "allowed_next_work": NEXT_WORK,
        "allow_bounded_checkpoint_next": allow_bounded,
        "run_full_25_run_panel_next": False,
        "run_cec_checkpoint_next": False,
        "run_new_objective_next": False,
        "call_llm_next": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _build_report(
    *,
    repair_design: Mapping[str, Any],
    collapse: Mapping[str, Any],
    ledger: Mapping[str, Any],
    route: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.32",
        "sanity_scope": "static_guard_sanity_only",
        "repair_policy_id": repair_design["repair_policy_id"],
        "guard_not_collapsed": bool(collapse["guard_not_collapsed"]),
        "reliable_best_reward_preserves_trust": bool(
            collapse["reliable_best_reward_preserves_trust"]
        ),
        "misleading_conflict_breaks_only_when_guarded": bool(
            collapse["misleading_conflict_breaks_only_when_guarded"]
        ),
        "unguarded_break_detected": bool(collapse["unguarded_break_detected"]),
        "always_contribution_leader_break_detected": bool(
            collapse["always_contribution_leader_break_detected"]
        ),
        "allow_bounded_checkpoint_next": bool(route["allow_bounded_checkpoint_next"]),
        "run_full_25_run_panel_next": False,
        "formal_25_run_recommended_now": False,
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "cec_checkpoint_executed": False,
        "FE_total": int(ledger["FE_total"]),
        "recommended_next_stage": route["next_stage"],
        "recommended_next_work": route["allowed_next_work"],
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


def _row_by_fixture(
    rows: Sequence[Mapping[str, Any]], fixture_id: str
) -> Mapping[str, Any]:
    for row in rows:
        if row["fixture_id"] == fixture_id:
            return row
    raise ValueError(f"missing fixture row: {fixture_id}")


def _zero_filled_counts(counter: Counter[str], names: Sequence[str]) -> dict[str, int]:
    return {name: int(counter.get(name, 0)) for name in names}


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
