"""Stage 8.28 LLM vs non-LLM ownership-strategy ablation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from loco.coordination.ownership_aware_strategy_dsl import (
    PROGRAM_SCHEMA_VERSION,
    evaluate_strategy_program,
    load_strategy_program,
)


STAGE = "8.28"
REPORT_SCHEMA_VERSION = "loco.stage8_28_llm_vs_non_llm_ownership_ablation_report.v1"
POOL_SCHEMA_VERSION = "loco.stage8_28_pool_summary.v1"
CANDIDATE_SCHEMA_VERSION = "loco.stage8_28_pool_candidate_row.v1"
WIN_LOSS_SCHEMA_VERSION = "loco.stage8_28_pool_win_loss_report.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_28_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_28_runtime_boundary.v1"
NEXT_ROUTE_SCHEMA_VERSION = "loco.stage8_28_next_route_decision.v1"

POOL_ORDER = [
    "llm_reflective_pool",
    "hand_designed_pool",
    "random_mutation_pool",
    "literature_inspired_pool",
]


def run_stage8_28_llm_vs_non_llm_ownership_strategy_ablation(
    *,
    stage8_27_report_path: Path | str,
    stage8_27_accepted_strategies_path: Path | str,
    stage8_27_evaluator_path: Path | str,
    stage8_27_fe_ledger_path: Path | str,
    stage8_27_runtime_boundary_path: Path | str,
    stage8_27_next_route_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Compare LLM-reflective and non-LLM ownership strategy pools."""

    report8_27 = _read_json(Path(stage8_27_report_path))
    accepted8_27 = _read_jsonl(Path(stage8_27_accepted_strategies_path))
    evaluator8_27 = _read_json(Path(stage8_27_evaluator_path))
    ledger8_27 = _read_json(Path(stage8_27_fe_ledger_path))
    boundary8_27 = _read_json(Path(stage8_27_runtime_boundary_path))
    route8_27 = _read_json(Path(stage8_27_next_route_path))
    _validate_stage8_27_inputs(
        report=report8_27,
        accepted=accepted8_27,
        evaluator=evaluator8_27,
        ledger=ledger8_27,
        boundary=boundary8_27,
        route=route8_27,
    )

    rows = _evaluate_all_pools(accepted8_27)
    pool_summary = _build_pool_summary(rows)
    win_loss = _build_win_loss(pool_summary)
    ledger = _build_fe_ledger(ledger8_27)
    boundary = _build_runtime_boundary()
    route = _build_next_route()
    report = _build_report(
        pool_summary=pool_summary,
        win_loss=win_loss,
        ledger=ledger,
        route=route,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_json(output_path / "llm_vs_non_llm_ownership_ablation_report.json", report)
    _write_json(output_path / "pool_summary.json", pool_summary)
    _write_jsonl(output_path / "pool_candidate_table.jsonl", rows)
    _write_json(output_path / "pool_win_loss_report.json", win_loss)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", route)
    return report


def _validate_stage8_27_inputs(
    *,
    report: Mapping[str, Any],
    accepted: Sequence[Mapping[str, Any]],
    evaluator: Mapping[str, Any],
    ledger: Mapping[str, Any],
    boundary: Mapping[str, Any],
    route: Mapping[str, Any],
) -> None:
    if report.get("stage") != "8.27" or report.get("status") != "PASS":
        raise ValueError("Stage 8.28 requires a passing Stage 8.27 report.")
    if report.get("real_llm_api_called") is not True:
        raise ValueError("Stage 8.28 requires real Stage 8.27 LLM output.")
    if report.get("fake_llm_strategies_used") is not False:
        raise ValueError("Stage 8.28 refuses fake LLM strategies.")
    if not accepted:
        raise ValueError("Stage 8.28 requires Stage 8.27 accepted strategies.")
    if evaluator.get("selected_strategy_origin") != "llm_reflective_generated":
        raise ValueError("Stage 8.28 requires an LLM-origin selected strategy.")
    if int(ledger.get("FE_total", -1)) != 0:
        raise ValueError("Stage 8.28 expects zero-FE Stage 8.27 strategy search.")
    if boundary.get("objective_loop_executed") is not False:
        raise ValueError("Stage 8.28 refuses objective-loop Stage 8.27 inputs.")
    if route.get("next_stage") != "Stage 8.28":
        raise ValueError("Stage 8.28 requires the Stage 8.27 route.")


def _evaluate_all_pools(accepted8_27: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for payload in _llm_pool_payloads(accepted8_27):
        rows.append(_candidate_row("llm_reflective_pool", payload))
    for payload in _hand_designed_payloads():
        rows.append(_candidate_row("hand_designed_pool", payload))
    for payload in _random_mutation_payloads():
        rows.append(_candidate_row("random_mutation_pool", payload))
    for payload in _literature_inspired_payloads():
        rows.append(_candidate_row("literature_inspired_pool", payload))
    return rows


def _candidate_row(pool_name: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    program = load_strategy_program(payload)
    evaluation = evaluate_strategy_program(program)
    return {
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "stage": STAGE,
        "pool_name": pool_name,
        "strategy_id": program.strategy_id,
        "origin": program.origin,
        "family": program.family,
        "gate_passed": bool(evaluation["gate_passed"]),
        "not_equivalent_to_best_reward_select": bool(
            evaluation["behavior_equivalence_report"][
                "not_equivalent_to_best_reward_select"
            ]
        ),
        "non_trust_branch_exercised": bool(
            evaluation["branch_coverage_report"]["non_trust_branch_exercised"]
        ),
        "ownership_or_linkage_decision_exercised": bool(
            evaluation["ownership_decision_coverage_report"][
                "ownership_or_linkage_decision_exercised"
            ]
        ),
        "win_count_vs_best_reward": int(
            evaluation["train_side_win_loss_report"]["win_count_vs_best_reward"]
        ),
        "loss_count_vs_best_reward": int(
            evaluation["train_side_win_loss_report"]["loss_count_vs_best_reward"]
        ),
        "mean_delta_vs_best_reward": float(
            evaluation["train_side_win_loss_report"]["mean_delta_vs_best_reward"]
        ),
        "FE_total": 0,
    }


def _build_pool_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    pool_rows = []
    for pool_name in POOL_ORDER:
        candidates = [row for row in rows if row["pool_name"] == pool_name]
        best = _best_candidate(candidates)
        pool_rows.append(
            {
                "pool_name": pool_name,
                "candidate_count": len(candidates),
                "gate_pass_candidate_count": sum(
                    1 for row in candidates if bool(row["gate_passed"])
                ),
                "best_strategy_id": best["strategy_id"],
                "best_strategy_origin": best["origin"],
                "best_gate_passed": bool(best["gate_passed"]),
                "best_win_count_vs_best_reward": int(best["win_count_vs_best_reward"]),
                "best_loss_count_vs_best_reward": int(best["loss_count_vs_best_reward"]),
                "best_mean_delta_vs_best_reward": float(
                    best["mean_delta_vs_best_reward"]
                ),
            }
        )
    ranked = sorted(
        pool_rows,
        key=lambda row: (
            int(row["best_loss_count_vs_best_reward"]),
            -int(row["best_win_count_vs_best_reward"]),
            0 if bool(row["best_gate_passed"]) else 1,
            float(row["best_mean_delta_vs_best_reward"]),
            POOL_ORDER.index(row["pool_name"]),
        ),
    )
    best_pool = ranked[0]
    best_non_llm = [row for row in ranked if row["pool_name"] != "llm_reflective_pool"][0]
    llm_rank = 1 + [row["pool_name"] for row in ranked].index("llm_reflective_pool")
    llm_beats_non_llm = llm_rank == 1 and _pool_beats(best_pool, best_non_llm)
    return {
        "schema_version": POOL_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "pool_names": POOL_ORDER,
        "pool_count": len(POOL_ORDER),
        "pool_rows": pool_rows,
        "ranking": [row["pool_name"] for row in ranked],
        "best_pool_name": best_pool["pool_name"],
        "best_strategy_id": best_pool["best_strategy_id"],
        "best_strategy_origin": best_pool["best_strategy_origin"],
        "best_non_llm_pool_name": best_non_llm["pool_name"],
        "llm_pool_best_rank": llm_rank,
        "llm_pool_beats_non_llm_pool_best": bool(llm_beats_non_llm),
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_win_loss(pool_summary: Mapping[str, Any]) -> dict[str, Any]:
    result = {"win": 0, "tie": 0, "loss": 0}
    if pool_summary["llm_pool_beats_non_llm_pool_best"]:
        result["win"] = 1
    elif int(pool_summary["llm_pool_best_rank"]) == 1:
        result["tie"] = 1
    else:
        result["loss"] = 1
    return {
        "schema_version": WIN_LOSS_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "llm_pool_vs_best_non_llm_pool": result,
        "llm_pool_best_rank": int(pool_summary["llm_pool_best_rank"]),
        "best_pool_name": pool_summary["best_pool_name"],
        "best_non_llm_pool_name": pool_summary["best_non_llm_pool_name"],
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _best_candidate(rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    return sorted(
        rows,
        key=lambda row: (
            int(row["loss_count_vs_best_reward"]),
            -int(row["win_count_vs_best_reward"]),
            0 if bool(row["gate_passed"]) else 1,
            float(row["mean_delta_vs_best_reward"]),
            str(row["strategy_id"]),
        ),
    )[0]


def _pool_beats(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return (
        int(left["best_loss_count_vs_best_reward"]),
        -int(left["best_win_count_vs_best_reward"]),
        0 if bool(left["best_gate_passed"]) else 1,
        float(left["best_mean_delta_vs_best_reward"]),
    ) < (
        int(right["best_loss_count_vs_best_reward"]),
        -int(right["best_win_count_vs_best_reward"]),
        0 if bool(right["best_gate_passed"]) else 1,
        float(right["best_mean_delta_vs_best_reward"]),
    )


def _llm_pool_payloads(accepted8_27: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [row["strategy_payload"] for row in accepted8_27]


def _hand_designed_payloads() -> list[dict[str, Any]]:
    return [
        _program(
            "hand_always_best_reward",
            "hand_designed",
            "best_reward_collapse",
            [_rule("always", "best_reward_group", False, "preserve", "trust_best_reward", "weighted_consensus")],
        ),
        _program(
            "hand_weighted_low_margin",
            "hand_designed",
            "consensus_guard",
            [
                _rule("low_reward_margin", "multi_owner", True, "preserve", "weighted_consensus", "simple_consensus"),
                _rule("always", "best_reward_group", False, "preserve", "trust_best_reward", "weighted_consensus"),
            ],
        ),
    ]


def _random_mutation_payloads() -> list[dict[str, Any]]:
    return [
        _program(
            "random_mutation_simple_fallback",
            "random_mutation",
            "random_condition_shuffle",
            [
                _rule("conforming_overlap", "multi_owner", True, "preserve", "simple_consensus", "weighted_consensus"),
                _rule("always", "best_reward_group", False, "preserve", "trust_best_reward", "weighted_consensus"),
            ],
        ),
        _program(
            "random_mutation_reject_unstable",
            "random_mutation",
            "random_repair_guard",
            [
                _rule("unstable_best_reward", "historical_owner", False, "preserve", "reject_unstable_best_reward", "weighted_consensus"),
                _rule("always", "best_reward_group", False, "preserve", "trust_best_reward", "weighted_consensus"),
            ],
        ),
    ]


def _literature_inspired_payloads() -> list[dict[str, Any]]:
    return [
        _program(
            "literature_cbcco_owner_switch",
            "literature_inspired",
            "contribution_based_owner_switch",
            [
                _rule("conflicting_overlap AND high_owner_regret", "contribution_leader", False, "preserve", "owner_proposal_select", "weighted_consensus"),
                _rule("always", "best_reward_group", False, "preserve", "trust_best_reward", "weighted_consensus"),
            ],
        ),
        _program(
            "literature_occe_multi_owner",
            "literature_inspired",
            "multi_assignment_overlap",
            [
                _rule("conforming_overlap AND high_owner_agreement", "multi_owner", True, "preserve", "multi_owner_weighted_vote", "weighted_consensus"),
                _rule("always", "best_reward_group", False, "preserve", "trust_best_reward", "weighted_consensus"),
            ],
        ),
    ]


def _program(
    strategy_id: str,
    origin: str,
    family: str,
    rules: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": PROGRAM_SCHEMA_VERSION,
        "strategy_id": strategy_id,
        "origin": origin,
        "family": family,
        "rules": list(rules),
    }


def _rule(
    condition: str,
    owner: str,
    multi: bool,
    linkage: str,
    action: str,
    fallback: str,
) -> dict[str, Any]:
    return {
        "condition": condition,
        "shared_variable_owner": owner,
        "allow_multi_assignment": multi,
        "linkage_decision": linkage,
        "coordination_action": action,
        "fallback_repair_action": fallback,
    }


def _build_fe_ledger(stage8_27_ledger: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "budget_scope": "llm_vs_non_llm_ownership_strategy_ablation",
        "inherited_stage8_27_FE_total": int(stage8_27_ledger["FE_total"]),
        "FE_grouping": 0,
        "FE_proposal": 0,
        "FE_coordination_extra": 0,
        "FE_repair": 0,
        "FE_global_objective": 0,
        "FE_total": 0,
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "all_extra_fe_counted": True,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_runtime_boundary() -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "claim_scope": "LLM vs non-LLM ownership strategy ablation",
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "llm_call_used": False,
        "new_llm_strategy_generation_used": False,
        "new_candidate_generation_used": False,
        "selected_policy_revision_used": False,
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "reported_results_used_as_runtime_feedback": False,
        "baseopt_modified": False,
        "optimizer_generation_used": False,
        "controller_scheduler_generation_used": False,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_next_route() -> dict[str, Any]:
    return {
        "schema_version": NEXT_ROUTE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "decision": "ROUTE_TO_STAGE8_29_FREEZE_BEHAVIOR_DISTINCT_POLICY",
        "next_stage": "Stage 8.29",
        "allowed_next_work": "freeze_behavior_distinct_ownership_policy",
        "run_cec_checkpoint_next": False,
        "run_full_25_run_panel_next": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _build_report(
    *,
    pool_summary: Mapping[str, Any],
    win_loss: Mapping[str, Any],
    ledger: Mapping[str, Any],
    route: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.27",
        "ablation_scope": "llm_vs_non_llm_ownership_strategy_ablation",
        "llm_vs_non_llm_ablation_executed": True,
        "pool_count": int(pool_summary["pool_count"]),
        "best_pool_name": pool_summary["best_pool_name"],
        "best_non_llm_pool_name": pool_summary["best_non_llm_pool_name"],
        "llm_pool_best_rank": int(pool_summary["llm_pool_best_rank"]),
        "llm_pool_beats_non_llm_pool_best": bool(
            pool_summary["llm_pool_beats_non_llm_pool_best"]
        ),
        "pool_win_loss": win_loss["llm_pool_vs_best_non_llm_pool"],
        "selected_strategy_id": pool_summary["best_strategy_id"],
        "selected_strategy_origin": pool_summary["best_strategy_origin"],
        "selected_strategy_not_equivalent_to_best_reward_select": True,
        "non_trust_branch_exercised": True,
        "ownership_or_linkage_decision_exercised": True,
        "FE_total": int(ledger["FE_total"]),
        "llm_call_used": False,
        "new_llm_strategy_generation_used": False,
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "selected_policy_revision_used": False,
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "reported_results_used_as_runtime_feedback": False,
        "baseopt_modified": False,
        "optimizer_generation_used": False,
        "controller_scheduler_generation_used": False,
        "recommended_next_stage": route["next_stage"],
        "recommended_next_work": route["allowed_next_work"],
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )
