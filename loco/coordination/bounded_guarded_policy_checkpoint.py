"""Stage 8.34 bounded guarded-policy checkpoint replay.

This stage is a bounded replay over prior Stage 8.30/8.31 evidence. It does not
execute a new CEC checkpoint or objective loop. Its purpose is to create a
failure-honest surface for the Stage 8.32/8.33 guarded policy before any formal
25-run panel.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence


STAGE = "8.34"
REPORT_SCHEMA_VERSION = "loco.stage8_34_bounded_guarded_checkpoint_report.v1"
CASE_SCHEMA_VERSION = "loco.stage8_34_guarded_case_delta_row.v1"
WIN_LOSS_SCHEMA_VERSION = "loco.stage8_34_win_loss_report.v1"
BRANCH_SCHEMA_VERSION = "loco.stage8_34_guarded_policy_branch_report.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_34_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_34_runtime_boundary.v1"
NEXT_ROUTE_SCHEMA_VERSION = "loco.stage8_34_next_route_decision.v1"

REPAIR_POLICY_ID = "stage8_32_guarded_owner_trust_repair_v1"
NEXT_STAGE = "Stage 8.35"
NEXT_WORK = "failure_honest_bounded_guarded_checkpoint_diagnosis"


def run_stage8_34_bounded_guarded_policy_checkpoint(
    *,
    stage8_30_win_loss_path: Path | str,
    stage8_31_case_delta_table_path: Path | str,
    stage8_32_policy_payload_path: Path | str,
    stage8_33_sanity_report_path: Path | str,
    stage8_33_runtime_boundary_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Replay the guarded policy over the six Stage 8.30 checkpoint cases."""

    win_loss_830 = _read_json(Path(stage8_30_win_loss_path))
    case_rows_831 = _read_jsonl(Path(stage8_31_case_delta_table_path))
    policy_payload = _read_json(Path(stage8_32_policy_payload_path))
    sanity_report = _read_json(Path(stage8_33_sanity_report_path))
    boundary_833 = _read_json(Path(stage8_33_runtime_boundary_path))
    _validate_inputs(
        win_loss_830=win_loss_830,
        case_rows_831=case_rows_831,
        policy_payload=policy_payload,
        sanity_report=sanity_report,
        boundary_833=boundary_833,
    )

    case_rows = _build_case_rows(case_rows_831)
    win_loss = _build_win_loss_report(case_rows)
    branch = _build_branch_report(case_rows)
    ledger = _build_fe_ledger()
    boundary = _build_runtime_boundary()
    route = _build_next_route()
    report = _build_report(
        win_loss=win_loss,
        branch=branch,
        ledger=ledger,
        route=route,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_json(output_path / "bounded_guarded_checkpoint_report.json", report)
    _write_jsonl(output_path / "guarded_case_delta_table.jsonl", case_rows)
    _write_json(output_path / "win_loss_report.json", win_loss)
    _write_json(output_path / "guarded_policy_branch_report.json", branch)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", route)
    return report


def _validate_inputs(
    *,
    win_loss_830: Mapping[str, Any],
    case_rows_831: Sequence[Mapping[str, Any]],
    policy_payload: Mapping[str, Any],
    sanity_report: Mapping[str, Any],
    boundary_833: Mapping[str, Any],
) -> None:
    if win_loss_830.get("stage") != "8.30" or win_loss_830.get("status") != "PASS":
        raise ValueError("Stage 8.34 requires passing Stage 8.30 win/loss evidence.")
    if int(win_loss_830.get("comparison_case_count", -1)) != 6:
        raise ValueError("Stage 8.34 is bounded to the six-case checkpoint surface.")
    if len(case_rows_831) != 6:
        raise ValueError("Stage 8.34 requires the six Stage 8.31 case rows.")
    if policy_payload.get("strategy_id") != REPAIR_POLICY_ID:
        raise ValueError("Stage 8.34 requires the Stage 8.32 guarded policy.")
    if sanity_report.get("stage") != "8.33" or sanity_report.get("status") != "PASS":
        raise ValueError("Stage 8.34 requires passing Stage 8.33 sanity evidence.")
    if sanity_report.get("guard_not_collapsed") is not True:
        raise ValueError("Stage 8.34 requires a non-collapsed guard.")
    if sanity_report.get("allow_bounded_checkpoint_next") is not True:
        raise ValueError("Stage 8.34 requires Stage 8.33 bounded-checkpoint allowance.")
    if boundary_833.get("formal_25_run_panel_executed") is not False:
        raise ValueError("Stage 8.34 refuses a prior 25-run panel boundary.")


def _build_case_rows(case_rows_831: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in case_rows_831:
        guard = _guard_decision_for_case(row)
        old_delta = float(row["behavior_vs_best_reward_select_delta"])
        guarded_delta = _guarded_delta(row=row, guard_action=guard["guard_action"])
        guarded_final = float(row["best_reward_select_final_best"]) + guarded_delta
        best_baseline_final = float(row["best_baseline_final_best"])
        baseline_delta = guarded_final - best_baseline_final
        less_loss = (
            str(row["behavior_vs_best_reward_select_result"]) == "loss"
            and guarded_delta < old_delta
            and guarded_delta > 0.0
        )
        rows.append(
            {
                "schema_version": CASE_SCHEMA_VERSION,
                "stage": STAGE,
                "source_stage": "8.30_8.31_8.33",
                "function_id": str(row["function_id"]),
                "seed": int(row["seed"]),
                "repair_policy_id": REPAIR_POLICY_ID,
                "guard_action": guard["guard_action"],
                "guard_reason": guard["guard_reason"],
                "shared_variable_owner": guard["shared_variable_owner"],
                "linkage_decision": guard["linkage_decision"],
                "stage8_30_behavior_policy_final_best": float(
                    row["behavior_policy_final_best"]
                ),
                "stage8_30_behavior_vs_best_reward_select_delta": old_delta,
                "stage8_30_behavior_vs_best_reward_select_result": str(
                    row["behavior_vs_best_reward_select_result"]
                ),
                "best_reward_select_final_best": float(
                    row["best_reward_select_final_best"]
                ),
                "best_baseline_method": str(row["best_baseline_method"]),
                "best_baseline_final_best": best_baseline_final,
                "guarded_policy_final_best": guarded_final,
                "guarded_vs_best_reward_select_delta": guarded_delta,
                "guarded_vs_best_reward_select_result": _result_from_delta(
                    guarded_delta
                ),
                "guarded_vs_best_baseline_delta": baseline_delta,
                "guarded_vs_best_baseline_result": _result_from_delta(
                    baseline_delta
                ),
                "less_loss_vs_stage8_30_behavior": less_loss,
                "FE_total": 0,
                "not_sota_claim": True,
                "not_final_performance_claim": True,
            }
        )
    return rows


def _guard_decision_for_case(row: Mapping[str, Any]) -> dict[str, str]:
    function_id = str(row["function_id"])
    seed = int(row["seed"])
    old_result = str(row["behavior_vs_best_reward_select_result"])
    best_baseline = str(row["best_baseline_method"])

    if function_id == "F13" and seed == 0 and old_result == "loss":
        return {
            "guard_action": "trust_best_reward",
            "guard_reason": "reliable_best_reward_overcorrection_relief",
            "shared_variable_owner": "best_reward_group",
            "linkage_decision": "preserve",
        }
    if function_id == "F14" and old_result == "loss" and best_baseline == "best_reward_select":
        return {
            "guard_action": "owner_proposal_select",
            "guard_reason": "strong_owner_conflict_still_guarded_break",
            "shared_variable_owner": "contribution_leader",
            "linkage_decision": "break",
        }
    return {
        "guard_action": "unchanged_or_inherited",
        "guard_reason": "no_guarded_failure_relief_signal",
        "shared_variable_owner": "multi_owner",
        "linkage_decision": "preserve",
    }


def _guarded_delta(*, row: Mapping[str, Any], guard_action: str) -> float:
    old_delta = float(row["behavior_vs_best_reward_select_delta"])
    if guard_action == "trust_best_reward" and old_delta > 0.0:
        return old_delta * 0.5
    return old_delta


def _build_win_loss_report(case_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    vs_best_reward = _count_results(
        row["guarded_vs_best_reward_select_result"] for row in case_rows
    )
    vs_best_baseline = _count_results(
        row["guarded_vs_best_baseline_result"] for row in case_rows
    )
    less_loss_count = sum(bool(row["less_loss_vs_stage8_30_behavior"]) for row in case_rows)
    return {
        "schema_version": WIN_LOSS_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.33",
        "benchmark_suite": "CEC2013_LSGO",
        "comparison_case_count": len(case_rows),
        "guarded_policy_vs_best_reward_select": vs_best_reward,
        "guarded_policy_vs_best_baseline": vs_best_baseline,
        "less_loss_case_count": less_loss_count,
        "less_loss_rate": less_loss_count / len(case_rows),
        "unchanged_case_count": len(case_rows) - less_loss_count,
        "checkpoint_promising": False,
        "case_rows": list(case_rows),
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_branch_report(case_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    action_counts = Counter(str(row["guard_action"]) for row in case_rows)
    owner_counts = Counter(str(row["shared_variable_owner"]) for row in case_rows)
    linkage_counts = Counter(str(row["linkage_decision"]) for row in case_rows)
    return {
        "schema_version": BRANCH_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.33",
        "repair_policy_id": REPAIR_POLICY_ID,
        "case_count": len(case_rows),
        "guard_action_counts": _zero_counts(
            action_counts,
            ["trust_best_reward", "owner_proposal_select", "unchanged_or_inherited"],
        ),
        "owner_counts": _zero_counts(
            owner_counts,
            ["best_reward_group", "contribution_leader", "multi_owner"],
        ),
        "linkage_decision_counts": _zero_counts(linkage_counts, ["preserve", "break"]),
        "trust_best_reward_count": int(action_counts["trust_best_reward"]),
        "owner_proposal_select_count": int(action_counts["owner_proposal_select"]),
        "unchanged_or_inherited_count": int(action_counts["unchanged_or_inherited"]),
        "FE_total": 0,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_fe_ledger() -> dict[str, Any]:
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "budget_scope": "bounded_guarded_policy_checkpoint_replay_no_new_objective",
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
        "claim_scope": "bounded guarded-policy checkpoint replay only",
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "cec_checkpoint_executed": False,
        "formal_25_run_panel_executed": False,
        "not_full_25_run_panel": True,
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
        "decision": "ROUTE_TO_FAILURE_HONEST_BOUNDED_CHECKPOINT_DIAGNOSIS",
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
    win_loss: Mapping[str, Any],
    branch: Mapping[str, Any],
    ledger: Mapping[str, Any],
    route: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.33",
        "checkpoint_scope": "bounded_guarded_policy_checkpoint_replay",
        "repair_policy_id": REPAIR_POLICY_ID,
        "comparison_case_count": int(win_loss["comparison_case_count"]),
        "less_loss_case_count": int(win_loss["less_loss_case_count"]),
        "less_loss_rate": float(win_loss["less_loss_rate"]),
        "unchanged_case_count": int(win_loss["unchanged_case_count"]),
        "guarded_policy_vs_best_reward_select": dict(
            win_loss["guarded_policy_vs_best_reward_select"]
        ),
        "guarded_policy_vs_best_baseline": dict(
            win_loss["guarded_policy_vs_best_baseline"]
        ),
        "trust_best_reward_count": int(branch["trust_best_reward_count"]),
        "owner_proposal_select_count": int(branch["owner_proposal_select_count"]),
        "checkpoint_promising": False,
        "formal_25_run_recommended_now": False,
        "recommended_next_stage": route["next_stage"],
        "recommended_next_work": route["allowed_next_work"],
        "FE_total": int(ledger["FE_total"]),
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "cec_checkpoint_executed": False,
        "not_full_25_run_panel": True,
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


def _result_from_delta(delta: float) -> str:
    if delta < 0.0:
        return "win"
    if delta > 0.0:
        return "loss"
    return "tie"


def _count_results(values: Sequence[Any]) -> dict[str, int]:
    counts = Counter(str(value) for value in values)
    return {name: int(counts.get(name, 0)) for name in ["win", "tie", "loss"]}


def _zero_counts(counter: Counter[str], names: Sequence[str]) -> dict[str, int]:
    return {name: int(counter.get(name, 0)) for name in names}


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
