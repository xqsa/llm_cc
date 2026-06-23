"""Stage 8.31 failure-honest diagnosis for Stage 8.30 CEC checkpoint.

This stage is read-only. It diagnoses why the frozen Stage 8.29
behavior-distinct policy was exercised but should not proceed to a formal
25-run CEC panel.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence


STAGE = "8.31"
DIAGNOSIS_SCHEMA_VERSION = "loco.stage8_31_failure_diagnosis_report.v1"
OVERCORRECTION_SCHEMA_VERSION = "loco.stage8_31_overcorrection_diagnosis.v1"
CASE_DELTA_SCHEMA_VERSION = "loco.stage8_31_case_delta_table.v1"
BRANCH_USAGE_SCHEMA_VERSION = "loco.stage8_31_branch_usage_diagnosis.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_31_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_31_runtime_boundary.v1"
NEXT_ROUTE_SCHEMA_VERSION = "loco.stage8_31_next_route_decision.v1"

OVER_CORRECTION_TYPE = "contribution_leader_break_overcorrection"
NEXT_STAGE = "Stage 8.32"
NEXT_WORK = "design_overcorrection_guard_or_conditional_owner_trust_repair"


def run_stage8_31_behavior_distinct_checkpoint_failure_diagnosis(
    *,
    stage8_30_checkpoint_report_path: Path | str,
    stage8_30_win_loss_path: Path | str,
    stage8_30_method_summary_path: Path | str,
    stage8_30_policy_branch_path: Path | str,
    stage8_30_fe_ledger_path: Path | str,
    stage8_30_runtime_boundary_path: Path | str,
    stage8_30_next_route_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Diagnose Stage 8.30 checkpoint failure without new objective work."""

    checkpoint_report = _read_json(Path(stage8_30_checkpoint_report_path))
    win_loss = _read_json(Path(stage8_30_win_loss_path))
    method_summary = _read_json(Path(stage8_30_method_summary_path))
    branch_report = _read_json(Path(stage8_30_policy_branch_path))
    stage8_30_ledger = _read_json(Path(stage8_30_fe_ledger_path))
    stage8_30_boundary = _read_json(Path(stage8_30_runtime_boundary_path))
    stage8_30_route = _read_json(Path(stage8_30_next_route_path))
    _validate_inputs(
        checkpoint_report=checkpoint_report,
        win_loss=win_loss,
        method_summary=method_summary,
        branch_report=branch_report,
        stage8_30_ledger=stage8_30_ledger,
        stage8_30_boundary=stage8_30_boundary,
        stage8_30_route=stage8_30_route,
    )

    case_rows = _build_case_delta_rows(win_loss)
    branch_usage = _build_branch_usage_diagnosis(branch_report)
    overcorrection = _build_overcorrection_diagnosis(
        win_loss=win_loss,
        case_rows=case_rows,
        branch_usage=branch_usage,
        method_summary=method_summary,
    )
    ledger = _build_fe_ledger(stage8_30_ledger)
    boundary = _build_runtime_boundary()
    route = _build_next_route()
    report = _build_failure_diagnosis_report(
        checkpoint_report=checkpoint_report,
        win_loss=win_loss,
        case_rows=case_rows,
        branch_usage=branch_usage,
        overcorrection=overcorrection,
        ledger=ledger,
        route=route,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_json(output_path / "failure_diagnosis_report.json", report)
    _write_json(output_path / "overcorrection_diagnosis.json", overcorrection)
    _write_jsonl(output_path / "case_delta_table.jsonl", case_rows)
    _write_json(output_path / "branch_usage_diagnosis.json", branch_usage)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", route)
    return report


def _validate_inputs(
    *,
    checkpoint_report: Mapping[str, Any],
    win_loss: Mapping[str, Any],
    method_summary: Mapping[str, Any],
    branch_report: Mapping[str, Any],
    stage8_30_ledger: Mapping[str, Any],
    stage8_30_boundary: Mapping[str, Any],
    stage8_30_route: Mapping[str, Any],
) -> None:
    if checkpoint_report.get("stage") != "8.30" or checkpoint_report.get("status") != "PASS":
        raise ValueError("Stage 8.31 requires a passing Stage 8.30 checkpoint report.")
    if checkpoint_report.get("checkpoint_promising") is not False:
        raise ValueError("Stage 8.31 only diagnoses a non-promising Stage 8.30 checkpoint.")
    if (
        checkpoint_report.get("recommended_next_work")
        != "failure_honest_behavior_distinct_checkpoint_diagnosis"
    ):
        raise ValueError("Stage 8.30 did not route to failure-honest diagnosis.")
    if checkpoint_report.get("run_full_25_run_panel_next") is not False:
        raise ValueError("Stage 8.31 refuses inputs routed to a 25-run panel.")
    if win_loss.get("stage") != "8.30" or win_loss.get("status") != "PASS":
        raise ValueError("Stage 8.31 requires the Stage 8.30 win/loss report.")
    if win_loss.get("checkpoint_promising") is not False:
        raise ValueError("Stage 8.31 expects a non-promising win/loss report.")
    if method_summary.get("stage") != "8.30" or method_summary.get("status") != "PASS":
        raise ValueError("Stage 8.31 requires the Stage 8.30 method summary.")
    if branch_report.get("stage") != "8.30" or branch_report.get("status") != "PASS":
        raise ValueError("Stage 8.31 requires the Stage 8.30 branch report.")
    if branch_report.get("ownership_action_exercised") is not True:
        raise ValueError("Stage 8.31 requires evidence that the policy was exercised.")
    if stage8_30_ledger.get("stage") != "8.30" or stage8_30_ledger.get("status") != "PASS":
        raise ValueError("Stage 8.31 requires the Stage 8.30 FE ledger.")
    if int(stage8_30_ledger["FE_total"]) != int(checkpoint_report["FE_total"]):
        raise ValueError("Stage 8.30 FE ledger does not match the checkpoint report.")
    if (
        stage8_30_boundary.get("stage") != "8.30"
        or stage8_30_boundary.get("status") != "PASS"
    ):
        raise ValueError("Stage 8.31 requires the Stage 8.30 runtime boundary.")
    if stage8_30_boundary.get("not_sota_claim") is not True:
        raise ValueError("Stage 8.31 requires no-SOTA Stage 8.30 inputs.")
    if stage8_30_route.get("stage") != "8.30" or stage8_30_route.get("status") != "PASS":
        raise ValueError("Stage 8.31 requires the Stage 8.30 route decision.")
    if (
        stage8_30_route.get("allowed_next_work")
        != "failure_honest_behavior_distinct_checkpoint_diagnosis"
    ):
        raise ValueError("Stage 8.30 route did not select failure diagnosis.")
    if stage8_30_route.get("run_full_25_run_panel_next") is not False:
        raise ValueError("Stage 8.31 refuses a route that proceeds to 25 runs.")


def _build_case_delta_rows(win_loss: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in win_loss["case_rows"]:
        result_vs_best_reward = str(row["behavior_vs_best_reward_select_result"])
        best_baseline_method = str(row["best_baseline_method"])
        rows.append(
            {
                "schema_version": CASE_DELTA_SCHEMA_VERSION,
                "stage": STAGE,
                "source_stage": "8.30",
                "function_id": str(row["function_id"]),
                "seed": int(row["seed"]),
                "selected_strategy_id": str(row["selected_strategy_id"]),
                "best_baseline_method": best_baseline_method,
                "behavior_policy_final_best": float(row["behavior_policy_final_best"]),
                "best_reward_select_final_best": float(
                    row["best_reward_select_final_best"]
                ),
                "best_baseline_final_best": float(row["best_baseline_final_best"]),
                "behavior_vs_best_reward_select_delta": float(
                    row["behavior_vs_best_reward_select_delta"]
                ),
                "behavior_vs_best_baseline_delta": float(
                    row["behavior_vs_best_baseline_delta"]
                ),
                "behavior_vs_best_reward_select_result": result_vs_best_reward,
                "behavior_vs_best_baseline_result": str(
                    row["behavior_vs_best_baseline_result"]
                ),
                "best_reward_favored_loss_case": (
                    best_baseline_method == "best_reward_select"
                    and result_vs_best_reward == "loss"
                ),
                "not_sota_claim": True,
                "not_final_performance_claim": True,
            }
        )
    return rows


def _build_branch_usage_diagnosis(branch_report: Mapping[str, Any]) -> dict[str, Any]:
    action_counts = dict(branch_report["coordination_action_counts"])
    owner_counts = dict(branch_report["owner_counts"])
    linkage_counts = dict(branch_report["linkage_decision_counts"])
    policy_trace_count = int(branch_report["policy_trace_row_count"])
    owner_proposal_select_count = int(action_counts.get("owner_proposal_select", 0))
    shrinkage_repair_count = int(action_counts.get("shrinkage_repair", 0))
    trust_best_reward_count = int(action_counts.get("trust_best_reward", 0))
    contribution_leader_count = int(owner_counts.get("contribution_leader", 0))
    best_reward_group_count = int(owner_counts.get("best_reward_group", 0))
    break_count = int(linkage_counts.get("break", 0))
    preserve_count = int(linkage_counts.get("preserve", 0))
    return {
        "schema_version": BRANCH_USAGE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.30",
        "selected_strategy_id": str(branch_report["selected_strategy_id"]),
        "selected_strategy_origin": str(branch_report["selected_strategy_origin"]),
        "policy_trace_row_count": policy_trace_count,
        "coordination_action_counts": action_counts,
        "owner_counts": owner_counts,
        "linkage_decision_counts": linkage_counts,
        "owner_proposal_select_count": owner_proposal_select_count,
        "shrinkage_repair_count": shrinkage_repair_count,
        "trust_best_reward_count": trust_best_reward_count,
        "contribution_leader_count": contribution_leader_count,
        "best_reward_group_count": best_reward_group_count,
        "break_count": break_count,
        "preserve_count": preserve_count,
        "owner_proposal_select_share": _share(owner_proposal_select_count, policy_trace_count),
        "shrinkage_repair_share": _share(shrinkage_repair_count, policy_trace_count),
        "trust_best_reward_share": _share(trust_best_reward_count, policy_trace_count),
        "contribution_leader_share": _share(contribution_leader_count, policy_trace_count),
        "best_reward_group_share": _share(best_reward_group_count, policy_trace_count),
        "break_share": _share(break_count, policy_trace_count),
        "preserve_share": _share(preserve_count, policy_trace_count),
        "policy_branch_collapse_confirmed": (
            policy_trace_count > 0
            and contribution_leader_count == policy_trace_count
            and break_count == policy_trace_count
            and trust_best_reward_count == 0
            and preserve_count == 0
            and best_reward_group_count == 0
        ),
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_overcorrection_diagnosis(
    *,
    win_loss: Mapping[str, Any],
    case_rows: Sequence[Mapping[str, Any]],
    branch_usage: Mapping[str, Any],
    method_summary: Mapping[str, Any],
) -> dict[str, Any]:
    wins = int(win_loss["behavior_policy_vs_best_reward_select"]["win"])
    losses = int(win_loss["behavior_policy_vs_best_reward_select"]["loss"])
    best_reward_favored_loss_count = sum(
        1 for row in case_rows if bool(row["best_reward_favored_loss_case"])
    )
    best_mean_method = _best_mean_method(method_summary)
    branch_collapse = bool(branch_usage["policy_branch_collapse_confirmed"])
    best_reward_trust_absent = (
        int(branch_usage["trust_best_reward_count"]) == 0
        and int(branch_usage["best_reward_group_count"]) == 0
        and int(branch_usage["preserve_count"]) == 0
    )
    overcorrection_confirmed = (
        win_loss.get("checkpoint_promising") is False
        and losses > wins
        and best_reward_favored_loss_count >= 1
        and branch_collapse
        and best_reward_trust_absent
    )
    return {
        "schema_version": OVERCORRECTION_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.30",
        "overcorrection_confirmed": overcorrection_confirmed,
        "overcorrection_type": OVER_CORRECTION_TYPE if overcorrection_confirmed else "not_confirmed",
        "primary_diagnosis": (
            "The frozen behavior-distinct policy is exercised, but it collapses "
            "to contribution_leader + break with owner_proposal_select or "
            "shrinkage behavior and never preserves/trusts best_reward_select, "
            "so it overcorrects away from the CEC F13/F14 regimes where "
            "best_reward_select is favored."
        ),
        "diagnostic_basis": {
            "checkpoint_not_promising": win_loss.get("checkpoint_promising") is False,
            "losses_exceed_wins_vs_best_reward_select": losses > wins,
            "best_reward_favored_loss_case_count": int(best_reward_favored_loss_count),
            "branch_collapse": branch_collapse,
            "best_reward_trust_absent": best_reward_trust_absent,
            "best_mean_method": best_mean_method,
        },
        "repair_direction": (
            "Add an overcorrection guard or conditional owner-trust path before "
            "any formal panel; do not rerun 25 times until this diagnosis is addressed."
        ),
        "formal_25_run_recommended_now": False,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_fe_ledger(stage8_30_ledger: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "budget_scope": "read_only_behavior_distinct_checkpoint_failure_diagnosis",
        "FE_grouping": 0,
        "FE_proposal": 0,
        "FE_coordination_extra": 0,
        "FE_repair": 0,
        "FE_global_objective": 0,
        "FE_total": 0,
        "inherited_stage8_30_FE_total": int(stage8_30_ledger["FE_total"]),
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "not_final_performance_claim": True,
    }


def _build_runtime_boundary() -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "claim_scope": "Stage 8.30 failure diagnosis only",
        "legal_inputs": [
            "artifacts/objective_eval/stage8_30/checkpoint_pilot_report.json",
            "artifacts/objective_eval/stage8_30/win_loss_report.json",
            "artifacts/objective_eval/stage8_30/method_summary.json",
            "artifacts/objective_eval/stage8_30/policy_branch_report.json",
            "artifacts/objective_eval/stage8_30/fe_ledger.json",
            "artifacts/objective_eval/stage8_30/runtime_boundary.json",
            "artifacts/objective_eval/stage8_30/next_route_decision.json",
        ],
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "forbidden_behaviors": {
            "llm_call": False,
            "new_candidate_generation": False,
            "new_llm_strategy_generation": False,
            "selected_policy_revision": False,
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
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_next_route() -> dict[str, Any]:
    return {
        "schema_version": NEXT_ROUTE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "decision": "CONFIRM_OVERCORRECTION_DIAGNOSE_BEFORE_REPAIR",
        "decision_reason": (
            "Stage 8.31 confirms that the behavior-distinct policy is exercised "
            "but over-applies contribution_leader + break / owner-proposal or "
            "shrinkage behavior without a best-reward trust/preserve path."
        ),
        "next_stage": NEXT_STAGE,
        "allowed_next_work": NEXT_WORK,
        "run_full_25_run_panel_next": False,
        "run_new_objective_next": False,
        "call_llm_next": False,
        "use_validation_feedback": False,
        "use_test_feedback": False,
        "use_reported_results_as_runtime_feedback": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _build_failure_diagnosis_report(
    *,
    checkpoint_report: Mapping[str, Any],
    win_loss: Mapping[str, Any],
    case_rows: Sequence[Mapping[str, Any]],
    branch_usage: Mapping[str, Any],
    overcorrection: Mapping[str, Any],
    ledger: Mapping[str, Any],
    route: Mapping[str, Any],
) -> dict[str, Any]:
    best_reward_favored_loss_count = sum(
        1 for row in case_rows if bool(row["best_reward_favored_loss_case"])
    )
    return {
        "schema_version": DIAGNOSIS_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.30",
        "diagnosis_scope": "read_only_behavior_distinct_checkpoint_failure_diagnosis",
        "selected_strategy_id": str(checkpoint_report["selected_strategy_id"]),
        "selected_strategy_origin": str(checkpoint_report["selected_strategy_origin"]),
        "stage8_30_checkpoint_promising": bool(win_loss["checkpoint_promising"]),
        "stage8_30_behavior_policy_vs_best_reward_select": dict(
            win_loss["behavior_policy_vs_best_reward_select"]
        ),
        "stage8_30_behavior_policy_vs_best_baseline": dict(
            win_loss["behavior_policy_vs_best_baseline"]
        ),
        "comparison_case_count": int(win_loss["comparison_case_count"]),
        "win_case_count": int(win_loss["behavior_policy_vs_best_reward_select"]["win"]),
        "tie_case_count": int(win_loss["behavior_policy_vs_best_reward_select"]["tie"]),
        "loss_case_count": int(win_loss["behavior_policy_vs_best_reward_select"]["loss"]),
        "best_reward_favored_loss_case_count": int(best_reward_favored_loss_count),
        "overcorrection_confirmed": bool(overcorrection["overcorrection_confirmed"]),
        "overcorrection_type": str(overcorrection["overcorrection_type"]),
        "policy_branch_collapse_confirmed": bool(
            branch_usage["policy_branch_collapse_confirmed"]
        ),
        "owner_proposal_select_count": int(branch_usage["owner_proposal_select_count"]),
        "shrinkage_repair_count": int(branch_usage["shrinkage_repair_count"]),
        "contribution_leader_count": int(branch_usage["contribution_leader_count"]),
        "break_count": int(branch_usage["break_count"]),
        "trust_best_reward_count": int(branch_usage["trust_best_reward_count"]),
        "preserve_count": int(branch_usage["preserve_count"]),
        "best_reward_group_count": int(branch_usage["best_reward_group_count"]),
        "formal_25_run_recommended_now": False,
        "run_full_25_run_panel_next": False,
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "FE_total": int(ledger["FE_total"]),
        "inherited_stage8_30_FE_total": int(ledger["inherited_stage8_30_FE_total"]),
        "recommended_next_stage": str(route["next_stage"]),
        "recommended_next_work": str(route["allowed_next_work"]),
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


def _best_mean_method(method_summary: Mapping[str, Any]) -> str:
    rows = list(method_summary["method_rows"])
    return str(min(rows, key=lambda row: float(row["mean_final_best"]))["method_name"])


def _share(count: int, total: int) -> float:
    if int(total) <= 0:
        return 0.0
    return round(float(count) / float(total), 12)


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
