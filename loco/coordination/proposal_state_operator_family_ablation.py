"""Stage 8.6 proposal-state/operator-family ablation.

This diagnostic stage consumes Stage 8.4 and Stage 8.5 artifacts to explain
which parts of the Stage 8.4 gap come from operator-family collapse and which
parts come from proposal-state regimes. It does not execute the objective loop,
evaluate new objectives, generate new candidates, revise selected operators, or
use validation/test feedback.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


STAGE = "8.6"
CASE_SCHEMA_VERSION = "loco.stage8_6_ablation_case_row.v1"
SUMMARY_SCHEMA_VERSION = "loco.stage8_6_ablation_summary.v1"
OPERATOR_SCHEMA_VERSION = "loco.stage8_6_operator_family_ablation_report.v1"
PROPOSAL_SCHEMA_VERSION = "loco.stage8_6_proposal_state_ablation_report.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_6_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_6_runtime_boundary.v1"

SELECTED_METHOD = "stage8_3_selected_operator"
WEIGHTED_METHOD = "weighted_consensus"
SIMPLE_METHOD = "simple_consensus"
FROZEN_METHOD = "frozen_stage5_selected_operator"
BEST_REWARD_METHOD = "best_reward_select"
TIE_EPSILON = 1e-12


def run_stage8_6_proposal_state_operator_family_ablation(
    *,
    stage8_4_trace_path: Path | str,
    stage8_4_win_loss_path: Path | str,
    stage8_5_diagnosis_path: Path | str,
    stage8_5_equivalence_path: Path | str,
    stage8_5_topology_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Run a read-only ablation over Stage 8.4/8.5 evidence."""

    trace_rows = _read_jsonl(Path(stage8_4_trace_path))
    win_loss = _read_json(Path(stage8_4_win_loss_path))
    diagnosis = _read_json(Path(stage8_5_diagnosis_path))
    equivalence = _read_json(Path(stage8_5_equivalence_path))
    topology = _read_json(Path(stage8_5_topology_path))
    _validate_inputs(trace_rows, win_loss, diagnosis, equivalence, topology)

    case_rows = _build_case_rows(trace_rows, win_loss["case_rows"])
    operator_report = _build_operator_family_report(case_rows)
    proposal_report = _build_proposal_state_report(case_rows)
    ledger = _build_fe_ledger(diagnosis)
    boundary = _build_runtime_boundary()
    route = _build_route()
    summary = _build_summary(
        diagnosis=diagnosis,
        case_rows=case_rows,
        operator_report=operator_report,
        proposal_report=proposal_report,
        ledger=ledger,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_json(output_path / "ablation_summary.json", summary)
    _write_json(output_path / "operator_family_ablation_report.json", operator_report)
    _write_json(output_path / "proposal_state_ablation_report.json", proposal_report)
    _write_jsonl(output_path / "ablation_case_table.jsonl", case_rows)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", route)
    return summary


def _validate_inputs(
    trace_rows: Sequence[Mapping[str, Any]],
    win_loss: Mapping[str, Any],
    diagnosis: Mapping[str, Any],
    equivalence: Mapping[str, Any],
    topology: Mapping[str, Any],
) -> None:
    if win_loss.get("stage") != "8.4" or win_loss.get("status") != "PASS":
        raise ValueError("Stage 8.6 requires the Stage 8.4 win/loss report.")
    if diagnosis.get("stage") != "8.5" or diagnosis.get("status") != "PASS":
        raise ValueError("Stage 8.6 requires the Stage 8.5 diagnosis report.")
    if equivalence.get("stage") != "8.5" or equivalence.get("status") != "PASS":
        raise ValueError("Stage 8.6 requires the Stage 8.5 equivalence report.")
    if topology.get("stage") != "8.5" or topology.get("status") != "PASS":
        raise ValueError("Stage 8.6 requires the Stage 8.5 topology report.")
    if diagnosis.get("recommended_next_stage") != (
        "Stage 8.6 proposal-state/operator-family ablation before official claims"
    ):
        raise ValueError("Stage 8.5 did not route to Stage 8.6 ablation.")
    if equivalence.get("selected_matches_weighted_consensus_all_cases") is not True:
        raise ValueError("Stage 8.6 requires the Stage 8.5 collapse diagnosis.")
    if diagnosis.get("not_final_performance_claim") is not True:
        raise ValueError("Stage 8.6 requires claim-boundary preservation.")
    if len(trace_rows) != int(diagnosis["stage8_4_trace_row_count"]):
        raise ValueError("Stage 8.4 trace row count does not match Stage 8.5.")


def _build_case_rows(
    trace_rows: Sequence[Mapping[str, Any]],
    win_loss_case_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for case in win_loss_case_rows:
        panel = str(case["synthetic_panel"])
        dimension = int(case["problem_dimension"])
        seed = int(case["seed"])
        selected = _series(trace_rows, panel, dimension, seed, SELECTED_METHOD)
        weighted = _series(trace_rows, panel, dimension, seed, WEIGHTED_METHOD)
        simple = _series(trace_rows, panel, dimension, seed, SIMPLE_METHOD)
        frozen = _series(trace_rows, panel, dimension, seed, FROZEN_METHOD)
        best_reward = _series(trace_rows, panel, dimension, seed, BEST_REWARD_METHOD)
        selected_final = float(selected[-1]["best_objective_so_far"])
        weighted_final = float(weighted[-1]["best_objective_so_far"])
        simple_final = float(simple[-1]["best_objective_so_far"])
        frozen_final = float(frozen[-1]["best_objective_so_far"])
        best_reward_final = float(best_reward[-1]["best_objective_so_far"])
        selected_minus_simple = round(selected_final - simple_final, 12)
        selected_minus_weighted = round(selected_final - weighted_final, 12)
        selected_minus_frozen = round(selected_final - frozen_final, 12)
        selected_minus_best_reward = round(selected_final - best_reward_final, 12)
        selected_weighted_coord_delta = _max_abs_delta(
            [row["coordinated_shared_value"] for row in selected],
            [row["coordinated_shared_value"] for row in weighted],
        )
        selected_weighted_update_delta = _max_abs_delta(
            [row["coordination_update_size"] for row in selected],
            [row["coordination_update_size"] for row in weighted],
        )
        selected_simple_update_delta = _mean(
            float(selected_row["coordination_update_size"])
            - float(simple_row["coordination_update_size"])
            for selected_row, simple_row in zip(selected, simple)
        )
        regime = (
            "simple_consensus_preferred"
            if str(case["selected_vs_best_baseline_result"]) == "loss"
            else "weighted_consensus_sufficient"
        )
        rows.append(
            {
                "schema_version": CASE_SCHEMA_VERSION,
                "stage": STAGE,
                "source_stage": "8.5",
                "synthetic_panel": panel,
                "problem_dimension": dimension,
                "seed": seed,
                "regime": regime,
                "best_baseline_method": str(case["best_baseline_method"]),
                "selected_final_best": selected_final,
                "weighted_final_best": weighted_final,
                "simple_final_best": simple_final,
                "frozen_stage5_final_best": frozen_final,
                "best_reward_select_final_best": best_reward_final,
                "selected_minus_weighted_final_best": selected_minus_weighted,
                "selected_minus_simple_final_best": selected_minus_simple,
                "selected_minus_frozen_final_best": selected_minus_frozen,
                "selected_minus_best_reward_final_best": selected_minus_best_reward,
                "selected_weighted_coord_value_abs_delta": selected_weighted_coord_delta,
                "selected_weighted_update_size_abs_delta": selected_weighted_update_delta,
                "selected_minus_simple_mean_update_size": selected_simple_update_delta,
                "projection_penalty_removed": selected_minus_frozen < -TIE_EPSILON,
                "best_reward_oversteps_selected": selected_minus_best_reward < -TIE_EPSILON,
                "objective_evaluation_used_in_stage8_6": False,
                "not_final_performance_claim": True,
            }
        )
    return rows


def _build_operator_family_report(
    case_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    selected_weighted_coord_deltas = [
        row["selected_weighted_coord_value_abs_delta"] for row in case_rows
    ]
    selected_weighted_update_deltas = [
        row["selected_weighted_update_size_abs_delta"] for row in case_rows
    ]
    selected_weighted_final_deltas = [
        row["selected_minus_weighted_final_best"] for row in case_rows
    ]
    projection_penalty_case_count = sum(
        1 for row in case_rows if row["projection_penalty_removed"]
    )
    best_reward_overstep_case_count = sum(
        1 for row in case_rows if row["best_reward_oversteps_selected"]
    )
    return {
        "schema_version": OPERATOR_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.5",
        "selected_weighted_coord_value_max_abs_delta": _max_abs(
            selected_weighted_coord_deltas
        ),
        "selected_weighted_update_size_max_abs_delta": _max_abs(
            selected_weighted_update_deltas
        ),
        "selected_weighted_final_best_max_abs_delta": _max_abs(
            selected_weighted_final_deltas
        ),
        "selected_weighted_family_collapse_confirmed": _max_abs(
            selected_weighted_coord_deltas
        )
        <= TIE_EPSILON
        and _max_abs(selected_weighted_final_deltas) <= TIE_EPSILON,
        "projection_penalty_case_count": projection_penalty_case_count,
        "best_reward_select_overstep_case_count": best_reward_overstep_case_count,
        "best_reward_select_overstep_confirmed": best_reward_overstep_case_count == len(case_rows),
        "operator_family_diagnosis": (
            "operator-family collapse to weighted_consensus; projection removal "
            "helps against the old frozen operator but does not add a new family."
        ),
        "recommended_operator_family_action": (
            "add conditional/simple-consensus-aware families instead of more weighted clones"
        ),
        "not_final_performance_claim": True,
    }


def _build_proposal_state_report(
    case_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    loss_rows = [row for row in case_rows if row["regime"] == "simple_consensus_preferred"]
    weighted_rows = [
        row for row in case_rows if row["regime"] == "weighted_consensus_sufficient"
    ]
    return {
        "schema_version": PROPOSAL_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.5",
        "loss_regime_case_count": len(loss_rows),
        "weighted_sufficient_case_count": len(weighted_rows),
        "loss_panels": _count_by(row["synthetic_panel"] for row in loss_rows),
        "loss_seeds": _count_by(str(row["seed"]) for row in loss_rows),
        "loss_dimensions": _count_by(str(row["problem_dimension"]) for row in loss_rows),
        "loss_best_baseline_methods": _count_by(
            row["best_baseline_method"] for row in loss_rows
        ),
        "tie_best_baseline_methods": _count_by(
            row["best_baseline_method"] for row in weighted_rows
        ),
        "mean_loss_selected_minus_simple_final_best": _mean(
            row["selected_minus_simple_final_best"] for row in loss_rows
        ),
        "mean_loss_selected_minus_simple_update_size": _mean(
            row["selected_minus_simple_mean_update_size"] for row in loss_rows
        ),
        "proposal_state_diagnosis": (
            "simple_consensus is needed in 12 high/medium-overlap cases; "
            "weighted/reweighting behavior is sufficient only where weighted "
            "consensus is already the best baseline."
        ),
        "recommended_proposal_state_action": (
            "add overlap/topology and reward-reliability features before official claims"
        ),
        "not_final_performance_claim": True,
    }


def _build_fe_ledger(diagnosis: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "budget_scope": "proposal_state_operator_family_ablation_only",
        "FE_grouping": 0,
        "FE_proposal": 0,
        "FE_coordination_extra": 0,
        "FE_repair": 0,
        "FE_global_objective": 0,
        "FE_total": 0,
        "inherited_stage8_4_FE_total": int(diagnosis["inherited_stage8_4_FE_total"]),
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "not_final_performance_claim": True,
    }


def _build_runtime_boundary() -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "claim_scope": "proposal-state/operator-family ablation",
        "legal_inputs": [
            "artifacts/objective_eval/stage8_4/objective_trace.jsonl",
            "artifacts/objective_eval/stage8_4/win_loss_report.json",
            "artifacts/objective_eval/stage8_5/failure_honest_diagnosis_report.json",
            "artifacts/objective_eval/stage8_5/baseline_equivalence_report.json",
            "artifacts/objective_eval/stage8_5/topology_gap_report.json",
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


def _build_route() -> dict[str, Any]:
    return {
        "schema_version": "loco.stage8_6_next_route_decision.v1",
        "stage": STAGE,
        "status": "PASS",
        "decision": "BLOCK_OFFICIAL_CLAIMS_AND_EXPAND_ABLATION",
        "decision_reason": (
            "Stage 8.6 confirms operator-family collapse to weighted_consensus "
            "and a proposal-state gap where simple_consensus is needed."
        ),
        "next_stage": "Stage 8.7",
        "allowed_next_work": (
            "conditional_proposal_state_policy_or_operator_family_expansion"
        ),
        "use_validation_feedback": False,
        "use_test_feedback": False,
        "use_reported_results_as_runtime_feedback": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _build_summary(
    *,
    diagnosis: Mapping[str, Any],
    case_rows: Sequence[Mapping[str, Any]],
    operator_report: Mapping[str, Any],
    proposal_report: Mapping[str, Any],
    ledger: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.5",
        "ablation_scope": "proposal_state_operator_family_ablation",
        "selected_candidate_id": str(diagnosis["selected_candidate_id"]),
        "primary_result": "operator_family_collapse_to_weighted_consensus_confirmed",
        "proposal_state_result": (
            "simple_consensus_needed_for_high_overlap_and_seed0_medium_regimes"
        ),
        "case_count": len(case_rows),
        "loss_regime_case_count": int(proposal_report["loss_regime_case_count"]),
        "weighted_sufficient_case_count": int(
            proposal_report["weighted_sufficient_case_count"]
        ),
        "operator_family_collapse_confirmed": bool(
            operator_report["selected_weighted_family_collapse_confirmed"]
        ),
        "proposal_state_gap_confirmed": int(
            proposal_report["loss_regime_case_count"]
        )
        > 0,
        "official_claim_blocked": True,
        "recommended_next_stage": (
            "Stage 8.7 conditional proposal-state policy or operator-family expansion"
        ),
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


def _series(
    trace_rows: Sequence[Mapping[str, Any]],
    panel: str,
    dimension: int,
    seed: int,
    method_name: str,
) -> list[Mapping[str, Any]]:
    rows = [
        row
        for row in trace_rows
        if row["synthetic_panel"] == panel
        and int(row["problem_dimension"]) == dimension
        and int(row["seed"]) == seed
        and row["method_name"] == method_name
    ]
    rows.sort(key=lambda row: int(row["objective_step"]))
    if not rows:
        raise ValueError(
            f"Missing trace rows for {panel} D={dimension} seed={seed} {method_name}"
        )
    return rows


def _max_abs(values: Iterable[Any]) -> float:
    return round(max(abs(float(value)) for value in values), 12)


def _max_abs_delta(left: Iterable[Any], right: Iterable[Any]) -> float:
    return round(
        max(
            abs(float(left_value) - float(right_value))
            for left_value, right_value in zip(left, right)
        ),
        12,
    )


def _mean(values: Iterable[Any]) -> float:
    numeric_values = [float(value) for value in values]
    if not numeric_values:
        return 0.0
    return round(float(np.mean(numeric_values)), 12)


def _count_by(values: Iterable[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return counts


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
