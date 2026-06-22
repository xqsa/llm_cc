"""Stage 8.15 failure-honest diagnosis for the CEC2013 smoke failure.

This stage is diagnosis-only. It reads Stage 8.14 single-run smoke artifacts,
identifies why the generalized policy should not proceed directly to the
25-run panel, and preserves the no-revision/no-feedback claim boundary.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np


STAGE = "8.15"
POLICY_NAME = "regime_safe_adaptive_shrinkage_v1"
POLICY_METHOD = "stage8_11_generalized_policy"
DIAGNOSIS_SCHEMA_VERSION = "loco.stage8_15_diagnosis_report.v1"
METHOD_GAP_SCHEMA_VERSION = "loco.stage8_15_method_gap_report.v1"
BRANCH_SCHEMA_VERSION = "loco.stage8_15_branch_diagnostics.v1"
ROOT_CAUSE_SCHEMA_VERSION = "loco.stage8_15_root_cause_hypotheses.v1"
CLAIM_BOUNDARY_SCHEMA_VERSION = "loco.stage8_15_claim_boundary_report.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_15_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_15_runtime_boundary.v1"
NEXT_ROUTE_SCHEMA_VERSION = "loco.stage8_15_next_route_decision.v1"

PRIMARY_DIAGNOSIS = (
    "CEC2013 F13/F14 smoke favors direct best-reward proposal selection; "
    "the generalized policy branches to simple/weighted/zero-anchor safety "
    "instead of exploiting the best-reward proposal."
)
DOMINANT_FAILURE_MODE = "best_reward_select_alignment_gap"


def run_stage8_15_cec2013_smoke_failure_diagnosis(
    *,
    stage8_14_smoke_report_path: Path | str,
    stage8_14_win_loss_path: Path | str,
    stage8_14_method_summary_path: Path | str,
    stage8_14_objective_trace_path: Path | str,
    stage8_14_fe_ledger_path: Path | str,
    stage8_14_runtime_boundary_path: Path | str,
    stage8_14_next_route_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Diagnose the Stage 8.14 single-run smoke failure without new FE."""

    smoke_report = _read_json(Path(stage8_14_smoke_report_path))
    win_loss = _read_json(Path(stage8_14_win_loss_path))
    method_summary = _read_json(Path(stage8_14_method_summary_path))
    trace_rows = _read_jsonl(Path(stage8_14_objective_trace_path))
    fe_ledger = _read_json(Path(stage8_14_fe_ledger_path))
    runtime_boundary = _read_json(Path(stage8_14_runtime_boundary_path))
    next_route = _read_json(Path(stage8_14_next_route_path))
    _validate_inputs(
        smoke_report=smoke_report,
        win_loss=win_loss,
        method_summary=method_summary,
        trace_rows=trace_rows,
        fe_ledger=fe_ledger,
        runtime_boundary=runtime_boundary,
        next_route=next_route,
    )

    method_gap = _build_method_gap_report(win_loss)
    branch = _build_branch_diagnostics(trace_rows)
    root_cause = _build_root_cause_hypotheses(method_gap, branch)
    claim = _build_claim_boundary_report()
    ledger = _build_fe_ledger(fe_ledger)
    boundary = _build_runtime_boundary()
    route = _build_next_route()
    report = _build_diagnosis_report(
        smoke_report=smoke_report,
        win_loss=win_loss,
        method_gap=method_gap,
        branch=branch,
        root_cause=root_cause,
        ledger=ledger,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_json(output_path / "diagnosis_report.json", report)
    _write_json(output_path / "method_gap_report.json", method_gap)
    _write_json(output_path / "branch_diagnostics.json", branch)
    _write_json(output_path / "root_cause_hypotheses.json", root_cause)
    _write_json(output_path / "claim_boundary_report.json", claim)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", route)
    return report


def _validate_inputs(
    *,
    smoke_report: Mapping[str, Any],
    win_loss: Mapping[str, Any],
    method_summary: Mapping[str, Any],
    trace_rows: Sequence[Mapping[str, Any]],
    fe_ledger: Mapping[str, Any],
    runtime_boundary: Mapping[str, Any],
    next_route: Mapping[str, Any],
) -> None:
    if smoke_report.get("stage") != "8.14" or smoke_report.get("status") != "PASS":
        raise ValueError("Stage 8.15 requires a passing Stage 8.14 smoke report.")
    if smoke_report.get("single_run_promising") is not False:
        raise ValueError("Stage 8.15 only diagnoses a non-promising smoke.")
    if smoke_report.get("recommended_next_work") != "failure_honest_cec2013_smoke_diagnosis":
        raise ValueError("Stage 8.14 did not route to failure-honest diagnosis.")
    if win_loss.get("stage") != "8.14" or win_loss.get("status") != "PASS":
        raise ValueError("Stage 8.15 requires the Stage 8.14 win/loss report.")
    if win_loss.get("single_run_promising") is not False:
        raise ValueError("Stage 8.15 expects the Stage 8.14 non-promising result.")
    if method_summary.get("stage") != "8.14" or method_summary.get("status") != "PASS":
        raise ValueError("Stage 8.15 requires the Stage 8.14 method summary.")
    if not trace_rows:
        raise ValueError("Stage 8.15 requires the Stage 8.14 objective trace.")
    if fe_ledger.get("stage") != "8.14" or fe_ledger.get("status") != "PASS":
        raise ValueError("Stage 8.15 requires the Stage 8.14 FE ledger.")
    if int(fe_ledger["FE_total"]) != int(smoke_report["FE_total"]):
        raise ValueError("Stage 8.14 FE ledger does not match the smoke report.")
    if runtime_boundary.get("stage") != "8.14" or runtime_boundary.get("status") != "PASS":
        raise ValueError("Stage 8.15 requires the Stage 8.14 runtime boundary.")
    if runtime_boundary.get("not_sota_claim") is not True:
        raise ValueError("Stage 8.15 requires no-SOTA Stage 8.14 inputs.")
    if next_route.get("stage") != "8.14" or next_route.get("status") != "PASS":
        raise ValueError("Stage 8.15 requires the Stage 8.14 route decision.")
    if next_route.get("run_failure_diagnosis_next") is not True:
        raise ValueError("Stage 8.14 route did not select failure diagnosis.")
    if next_route.get("run_full_25_run_panel_next") is not False:
        raise ValueError("Stage 8.15 refuses a route that proceeds to 25 runs.")


def _build_method_gap_report(win_loss: Mapping[str, Any]) -> dict[str, Any]:
    case_rows = []
    for row in win_loss["case_rows"]:
        best = float(row["best_baseline_final_best"])
        policy = float(row["policy_final_best"])
        delta = policy - best
        case_rows.append(
            {
                "function_id": str(row["function_id"]),
                "best_baseline_method": str(row["best_baseline_method"]),
                "best_baseline_final_best": best,
                "policy_final_best": policy,
                "policy_vs_best_baseline_delta": delta,
                "relative_gap_vs_best_baseline": delta / max(abs(best), 1e-12),
                "policy_vs_best_baseline_result": str(
                    row["policy_vs_best_baseline_result"]
                ),
            }
        )
    method_counts = Counter(row["best_baseline_method"] for row in case_rows)
    loss_count = sum(
        1 for row in case_rows if row["policy_vs_best_baseline_result"] == "loss"
    )
    return {
        "schema_version": METHOD_GAP_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.14",
        "case_count": len(case_rows),
        "loss_count": loss_count,
        "best_baseline_method_count": dict(method_counts),
        "case_rows": case_rows,
        "dominant_failure_mode": DOMINANT_FAILURE_MODE,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_branch_diagnostics(trace_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    functions = sorted({str(row["function_id"]) for row in trace_rows})
    branch_rows: dict[str, dict[str, Any]] = {}
    final_by_function = {
        function_id: _final_best_by_method(trace_rows, function_id)
        for function_id in functions
    }
    for function_id in functions:
        policy_rows = [
            row
            for row in trace_rows
            if row["function_id"] == function_id and row["method_name"] == POLICY_METHOD
        ]
        counts = Counter(str(row.get("policy_branch")) for row in policy_rows)
        dominant_branch, dominant_count = counts.most_common(1)[0]
        branch_rows[function_id] = {
            "function_id": function_id,
            "branch_counts": dict(counts),
            "dominant_branch": dominant_branch,
            "dominant_branch_count": dominant_count,
            "trace_row_count": len(policy_rows),
        }

    return {
        "schema_version": BRANCH_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.14",
        "policy_name": POLICY_NAME,
        "policy_method_name": POLICY_METHOD,
        "branch_rows_by_function": branch_rows,
        "final_best_by_function": final_by_function,
        "f13_policy_equivalent_to_simple_consensus": _same_final(
            final_by_function["F13"][POLICY_METHOD],
            final_by_function["F13"]["simple_consensus"],
        ),
        "f14_policy_equivalent_to_weighted_consensus": _same_final(
            final_by_function["F14"][POLICY_METHOD],
            final_by_function["F14"]["weighted_consensus"],
        ),
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_root_cause_hypotheses(
    method_gap: Mapping[str, Any], branch: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "schema_version": ROOT_CAUSE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.14",
        "top_hypothesis_id": "H1_best_reward_alignment_gap",
        "hypothesis_count": 4,
        "hypotheses": [
            {
                "hypothesis_id": "H1_best_reward_alignment_gap",
                "support": "best_reward_select is the best baseline on both F13 and F14",
                "diagnosis": (
                    "The generalized policy prioritizes safety branches while the "
                    "smoke rewards direct best-reward proposal selection."
                ),
                "evidence": dict(method_gap["best_baseline_method_count"]),
            },
            {
                "hypothesis_id": "H2_branch_transfer_mismatch",
                "support": "F13 collapses to simple_safety and F14 mostly to zero_anchor",
                "diagnosis": (
                    "Synthetic branch rules do not transfer cleanly to the CEC2013 "
                    "F13/F14 proposal state."
                ),
                "evidence": dict(branch["branch_rows_by_function"]),
            },
            {
                "hypothesis_id": "H3_proposal_construction_mismatch",
                "support": "Best-reward proposals dominate in the smoke but were not the Stage 8.11 target behavior",
                "diagnosis": (
                    "The proposal generator may be producing CEC2013 states where "
                    "reward is more reliable than the synthetic panels assumed."
                ),
            },
            {
                "hypothesis_id": "H4_single_shared_variable_scope_limit",
                "support": "Stage 8.14 exercises one shared-variable update path",
                "diagnosis": (
                    "The smoke may underrepresent multi-shared-variable interaction "
                    "benefits, so it blocks 25 runs but does not falsify the whole idea."
                ),
            },
        ],
        "do_not_run_25_until_diagnosed": True,
        "policy_revision_from_smoke_forbidden": True,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_claim_boundary_report() -> dict[str, Any]:
    return {
        "schema_version": CLAIM_BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.14",
        "claim_scope": "failure-honest CEC2013 smoke diagnosis only",
        "allowed_claim": (
            "The single-run F13/F14 CEC2013 smoke exposed a best-reward-selection "
            "alignment gap that should be diagnosed before any 25-run panel."
        ),
        "official_benchmark_claim_allowed": False,
        "sota_claim_allowed": False,
        "final_performance_claim_allowed": False,
        "policy_revision_allowed": False,
        "forbidden_claims": [
            "SOTA improvement",
            "final objective-value performance improvement",
            "full 25-run CEC2013 result",
            "full F1..F15 CEC2013 result",
            "policy repair success",
        ],
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_fe_ledger(stage8_14_ledger: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "budget_scope": "cec2013_smoke_failure_diagnosis_only",
        "FE_grouping": 0,
        "FE_proposal": 0,
        "FE_coordination_extra": 0,
        "FE_repair": 0,
        "FE_global_objective": 0,
        "FE_total": 0,
        "inherited_stage8_14_FE_total": int(stage8_14_ledger["FE_total"]),
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "not_final_performance_claim": True,
    }


def _build_runtime_boundary() -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "claim_scope": "failure-honest CEC2013 smoke diagnosis",
        "legal_inputs": [
            "artifacts/objective_eval/stage8_14/single_run_smoke_report.json",
            "artifacts/objective_eval/stage8_14/win_loss_report.json",
            "artifacts/objective_eval/stage8_14/method_summary.json",
            "artifacts/objective_eval/stage8_14/objective_trace.jsonl",
            "artifacts/objective_eval/stage8_14/fe_ledger.json",
            "artifacts/objective_eval/stage8_14/runtime_boundary.json",
            "artifacts/objective_eval/stage8_14/next_route_decision.json",
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
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_next_route() -> dict[str, Any]:
    return {
        "schema_version": NEXT_ROUTE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "decision": "ROUTE_TO_TRAIN_SIDE_PROPOSAL_POLICY_ALIGNMENT_REPAIR",
        "decision_reason": (
            "Stage 8.15 diagnoses the Stage 8.14 smoke as a best-reward-selection "
            "alignment gap, so the full 25-run panel remains blocked."
        ),
        "next_stage": "Stage 8.16",
        "allowed_next_work": "train_side_proposal_policy_alignment_repair",
        "run_full_25_run_panel_next": False,
        "use_validation_feedback": False,
        "use_test_feedback": False,
        "use_reported_results_as_runtime_feedback": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _build_diagnosis_report(
    *,
    smoke_report: Mapping[str, Any],
    win_loss: Mapping[str, Any],
    method_gap: Mapping[str, Any],
    branch: Mapping[str, Any],
    root_cause: Mapping[str, Any],
    ledger: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": DIAGNOSIS_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.14",
        "diagnosis_scope": "failure_honest_cec2013_smoke_diagnosis",
        "stage8_14_result_interpreted": True,
        "policy_name": POLICY_NAME,
        "single_run_promising": False,
        "policy_vs_best_baseline": dict(win_loss["policy_vs_best_baseline"]),
        "best_baseline_method_count": dict(method_gap["best_baseline_method_count"]),
        "dominant_failure_mode": DOMINANT_FAILURE_MODE,
        "primary_diagnosis": PRIMARY_DIAGNOSIS,
        "top_hypothesis_id": root_cause["top_hypothesis_id"],
        "f13_policy_equivalent_to_simple_consensus": bool(
            branch["f13_policy_equivalent_to_simple_consensus"]
        ),
        "f14_policy_equivalent_to_weighted_consensus": bool(
            branch["f14_policy_equivalent_to_weighted_consensus"]
        ),
        "full_25_run_panel_blocked": True,
        "policy_revision_allowed": False,
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "FE_total": int(ledger["FE_total"]),
        "inherited_stage8_14_FE_total": int(ledger["inherited_stage8_14_FE_total"]),
        "recommended_next_stage": "Stage 8.16",
        "recommended_next_work": "train_side_proposal_policy_alignment_repair",
        "stage8_14_smoke_fe_total": int(smoke_report["FE_total"]),
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


def _final_best_by_method(
    trace_rows: Sequence[Mapping[str, Any]], function_id: str
) -> dict[str, float]:
    methods = sorted(
        {
            str(row["method_name"])
            for row in trace_rows
            if str(row["function_id"]) == function_id
        }
    )
    return {
        method: float(
            [
                row
                for row in trace_rows
                if str(row["function_id"]) == function_id
                and str(row["method_name"]) == method
            ][-1]["best_objective_so_far"]
        )
        for method in methods
    }


def _same_final(left: float, right: float) -> bool:
    return abs(float(left) - float(right)) <= 1e-12 * max(abs(float(left)), abs(float(right)), 1.0)


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
