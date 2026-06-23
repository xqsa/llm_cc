"""Stage 8.21 LLM vs non-LLM contribution ablation.

This stage does not generate new LLM candidates. It reuses the Stage 8.20
accepted LLM-reflective pool and compares it against deterministic non-LLM
policy pools under the same train-side evaluator.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from loco.coordination.llm_reflective_policy_search_execution import (
    _evaluate_policies,
    _load_policy_program,
    _write_json,
    _write_jsonl,
)


STAGE = "8.21"
PASS_STATUS = "PASS"
REPORT_SCHEMA_VERSION = "loco.stage8_21_llm_contribution_ablation_report.v1"
POOL_SUMMARY_SCHEMA_VERSION = "loco.stage8_21_pool_summary.v1"
POOL_CANDIDATE_SCHEMA_VERSION = "loco.stage8_21_pool_candidate_row.v1"
WIN_LOSS_SCHEMA_VERSION = "loco.stage8_21_win_loss_report.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_21_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_21_runtime_boundary.v1"
NEXT_ROUTE_SCHEMA_VERSION = "loco.stage8_21_next_route_decision.v1"
POLICY_SCHEMA_VERSION = "loco.stage8_20_coordination_policy_program.v1"


def run_stage8_21_llm_contribution_ablation(
    *,
    stage8_20_report_path: Path | str,
    stage8_20_accepted_candidates_path: Path | str,
    stage8_20_evaluator_report_path: Path | str,
    stage8_20_fe_ledger_path: Path | str,
    stage8_20_runtime_boundary_path: Path | str,
    stage8_20_next_route_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Run the Stage 8.21 contribution ablation and write artifacts."""

    stage8_20_report = _read_json(Path(stage8_20_report_path))
    stage8_20_evaluator = _read_json(Path(stage8_20_evaluator_report_path))
    stage8_20_fe_ledger = _read_json(Path(stage8_20_fe_ledger_path))
    stage8_20_boundary = _read_json(Path(stage8_20_runtime_boundary_path))
    stage8_20_route = _read_json(Path(stage8_20_next_route_path))
    accepted_rows = _read_jsonl(Path(stage8_20_accepted_candidates_path))
    _validate_stage8_20_inputs(
        report=stage8_20_report,
        evaluator=stage8_20_evaluator,
        fe_ledger=stage8_20_fe_ledger,
        runtime_boundary=stage8_20_boundary,
        next_route=stage8_20_route,
        accepted_rows=accepted_rows,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    pools = _build_pools(accepted_rows)
    pool_rows, candidate_rows, all_trace_rows = _evaluate_pools(pools)
    ranked_pool_rows = sorted(
        pool_rows,
        key=lambda row: (
            int(row["best_loss_count_vs_best_reward"]),
            -int(row["best_win_count_vs_best_reward"]),
            float(row["best_mean_delta_vs_best_reward"]),
            str(row["pool_id"]),
        ),
    )
    for index, row in enumerate(ranked_pool_rows, start=1):
        row["pool_rank"] = index

    llm_pool = _pool_by_id(ranked_pool_rows, "llm_reflective_pool")
    non_llm_best = next(
        row for row in ranked_pool_rows if row["pool_id"] != "llm_reflective_pool"
    )
    win_loss = _build_win_loss_report(llm_pool=llm_pool, non_llm_best=non_llm_best)
    ledger = _build_fe_ledger(
        trace_rows=all_trace_rows,
        inherited_stage8_20_fe_total=int(stage8_20_fe_ledger["FE_total"]),
    )
    boundary = _build_runtime_boundary()
    route = _build_next_route()
    pool_summary = _build_pool_summary(ranked_pool_rows)
    report = _build_report(
        pool_rows=ranked_pool_rows,
        llm_pool=llm_pool,
        non_llm_best=non_llm_best,
        candidate_rows=candidate_rows,
        ledger=ledger,
        stage8_20_selected_candidate_id=str(stage8_20_report["selected_candidate_id"]),
        route=route,
    )

    _write_json(output_path / "llm_contribution_ablation_report.json", report)
    _write_json(output_path / "pool_summary.json", pool_summary)
    _write_jsonl(output_path / "pool_candidate_table.jsonl", candidate_rows)
    _write_json(output_path / "win_loss_report.json", win_loss)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", route)
    return report


def _validate_stage8_20_inputs(
    *,
    report: Mapping[str, Any],
    evaluator: Mapping[str, Any],
    fe_ledger: Mapping[str, Any],
    runtime_boundary: Mapping[str, Any],
    next_route: Mapping[str, Any],
    accepted_rows: Sequence[Mapping[str, Any]],
) -> None:
    if report.get("stage") != "8.20" or report.get("status") != "PASS":
        raise ValueError("Stage 8.21 requires a passing Stage 8.20 report.")
    if report.get("selected_candidate_origin") != "llm_reflective_generated":
        raise ValueError("Stage 8.21 requires a Stage 8.20 LLM-origin selection.")
    if evaluator.get("selected_candidate_id") != report.get("selected_candidate_id"):
        raise ValueError("Stage 8.20 report/evaluator selected candidate mismatch.")
    if fe_ledger.get("stage") != "8.20" or int(fe_ledger.get("FE_total", -1)) <= 0:
        raise ValueError("Stage 8.21 requires the Stage 8.20 FE ledger.")
    if runtime_boundary.get("real_llm_api_called") is not True:
        raise ValueError("Stage 8.21 requires real Stage 8.20 LLM evidence.")
    if next_route.get("next_stage") != "Stage 8.21":
        raise ValueError("Stage 8.21 requires the Stage 8.20 next-route decision.")
    if not accepted_rows:
        raise ValueError("Stage 8.21 requires Stage 8.20 accepted candidates.")


def _build_pools(
    accepted_rows: Sequence[Mapping[str, Any]],
) -> dict[str, list[Mapping[str, Any]]]:
    llm_payloads = [dict(row["policy_payload"]) for row in accepted_rows]
    return {
        "llm_reflective_pool": llm_payloads,
        "hand_designed_pool": _hand_designed_pool(),
        "random_mutation_pool": _random_mutation_pool(),
        "literature_inspired_pool": _literature_inspired_pool(),
        "stage8_16_human_repair_policy": _stage8_16_human_repair_pool(),
    }


def _evaluate_pools(
    pools: Mapping[str, Sequence[Mapping[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    pool_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    trace_rows: list[dict[str, Any]] = []
    for pool_id, payloads in pools.items():
        policies = [_load_policy_program(payload) for payload in payloads]
        evaluator = _evaluate_policies(policies)
        rows = [
            _candidate_row(pool_id=pool_id, row=row)
            for row in evaluator["candidate_rows"]
        ]
        ranked = sorted(
            rows,
            key=lambda row: (
                int(row["loss_count_vs_best_reward"]),
                -int(row["win_count_vs_best_reward"]),
                float(row["mean_delta_vs_best_reward"]),
                str(row["candidate_id"]),
            ),
        )
        best = ranked[0]
        pool_rows.append(
            {
                "schema_version": POOL_SUMMARY_SCHEMA_VERSION,
                "stage": STAGE,
                "pool_id": pool_id,
                "candidate_count": len(rows),
                "best_candidate_id": best["candidate_id"],
                "best_origin": best["origin"],
                "best_family": best["family"],
                "best_win_count_vs_best_reward": int(
                    best["win_count_vs_best_reward"]
                ),
                "best_tie_count_vs_best_reward": int(
                    best["tie_count_vs_best_reward"]
                ),
                "best_loss_count_vs_best_reward": int(
                    best["loss_count_vs_best_reward"]
                ),
                "best_mean_delta_vs_best_reward": float(
                    best["mean_delta_vs_best_reward"]
                ),
                "non_degenerate_candidate_count": sum(
                    int(row["non_trust_best_reward_branch_exercised"])
                    for row in rows
                ),
                "zero_loss_candidate_count": sum(
                    int(row["loss_count_vs_best_reward"] == 0) for row in rows
                ),
                "same_train_side_evaluator_used": True,
                "not_sota_claim": True,
                "not_final_performance_claim": True,
            }
        )
        candidate_rows.extend(rows)
        trace_rows.extend(
            [
                dict(row)
                | {
                    "stage": STAGE,
                    "source_stage": "8.20",
                    "pool_id": pool_id,
                    "same_train_side_evaluator_used": True,
                }
                for row in evaluator["evaluation_trace_rows"]
            ]
        )
    return pool_rows, candidate_rows, trace_rows


def _candidate_row(*, pool_id: str, row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": POOL_CANDIDATE_SCHEMA_VERSION,
        "stage": STAGE,
        "pool_id": pool_id,
        "candidate_id": row["candidate_id"],
        "origin": row["origin"],
        "family": row["family"],
        "win_count_vs_best_reward": int(row["win_count_vs_best_reward"]),
        "tie_count_vs_best_reward": int(row["tie_count_vs_best_reward"]),
        "loss_count_vs_best_reward": int(row["loss_count_vs_best_reward"]),
        "mean_delta_vs_best_reward": float(row["mean_delta_vs_best_reward"]),
        "branch_counts": dict(row["branch_counts"]),
        "non_trust_best_reward_branch_exercised": bool(
            row["non_trust_best_reward_branch_exercised"]
        ),
        "same_train_side_evaluator_used": True,
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "reported_results_used_as_runtime_feedback": False,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_win_loss_report(
    *, llm_pool: Mapping[str, Any], non_llm_best: Mapping[str, Any]
) -> dict[str, Any]:
    comparison = _compare_pool_rows(llm_pool, non_llm_best)
    return {
        "schema_version": WIN_LOSS_SCHEMA_VERSION,
        "stage": STAGE,
        "status": PASS_STATUS,
        "comparison_scope": "llm_reflective_pool_vs_best_non_llm_pool",
        "llm_reflective_pool": {
            "best_candidate_id": llm_pool["best_candidate_id"],
            "wins_vs_non_llm_pool_best": int(comparison == "win"),
            "ties_vs_non_llm_pool_best": int(comparison == "tie"),
            "losses_vs_non_llm_pool_best": int(comparison == "loss"),
            "best_win_count_vs_best_reward": int(
                llm_pool["best_win_count_vs_best_reward"]
            ),
            "best_loss_count_vs_best_reward": int(
                llm_pool["best_loss_count_vs_best_reward"]
            ),
            "best_mean_delta_vs_best_reward": float(
                llm_pool["best_mean_delta_vs_best_reward"]
            ),
        },
        "best_non_llm_pool": {
            "pool_id": non_llm_best["pool_id"],
            "best_candidate_id": non_llm_best["best_candidate_id"],
            "best_win_count_vs_best_reward": int(
                non_llm_best["best_win_count_vs_best_reward"]
            ),
            "best_loss_count_vs_best_reward": int(
                non_llm_best["best_loss_count_vs_best_reward"]
            ),
            "best_mean_delta_vs_best_reward": float(
                non_llm_best["best_mean_delta_vs_best_reward"]
            ),
        },
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _compare_pool_rows(left: Mapping[str, Any], right: Mapping[str, Any]) -> str:
    left_key = (
        int(left["best_loss_count_vs_best_reward"]),
        -int(left["best_win_count_vs_best_reward"]),
        float(left["best_mean_delta_vs_best_reward"]),
    )
    right_key = (
        int(right["best_loss_count_vs_best_reward"]),
        -int(right["best_win_count_vs_best_reward"]),
        float(right["best_mean_delta_vs_best_reward"]),
    )
    if left_key < right_key:
        return "win"
    if left_key > right_key:
        return "loss"
    return "tie"


def _build_report(
    *,
    pool_rows: Sequence[Mapping[str, Any]],
    llm_pool: Mapping[str, Any],
    non_llm_best: Mapping[str, Any],
    candidate_rows: Sequence[Mapping[str, Any]],
    ledger: Mapping[str, Any],
    stage8_20_selected_candidate_id: str,
    route: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": PASS_STATUS,
        "source_stage": "8.20",
        "ablation_scope": "llm_vs_non_llm_contribution_ablation",
        "stage8_20_selected_candidate_id": stage8_20_selected_candidate_id,
        "llm_reflective_pool_evaluated": True,
        "non_llm_pools_evaluated": True,
        "same_train_side_evaluator_used": True,
        "pool_count": len(pool_rows),
        "candidate_count": len(candidate_rows),
        "llm_pool_best_rank": int(llm_pool["pool_rank"]),
        "llm_pool_beats_non_llm_pool_best": _compare_pool_rows(
            llm_pool, non_llm_best
        )
        == "win",
        "llm_pool_non_degenerate_candidate_count": int(
            llm_pool["non_degenerate_candidate_count"]
        ),
        "llm_pool_train_objective_win_count_vs_best_reward": int(
            llm_pool["best_win_count_vs_best_reward"]
        ),
        "llm_pool_train_objective_loss_count_vs_best_reward": int(
            llm_pool["best_loss_count_vs_best_reward"]
        ),
        "best_non_llm_pool_id": non_llm_best["pool_id"],
        "best_non_llm_candidate_id": non_llm_best["best_candidate_id"],
        "FE_total": int(ledger["FE_total"]),
        "llm_call_used": False,
        "new_llm_candidate_generation_used": False,
        "fake_llm_candidates_used": False,
        "objective_loop_executed": True,
        "new_objective_evaluation_used": True,
        "selected_operator_revision_used": False,
        "evolution_search_used": False,
        "validation_feedback_used": False,
        "test_feedback_used": False,
        "reported_results_used_as_runtime_feedback": False,
        "baseopt_modified": False,
        "optimizer_generation_used": False,
        "controller_scheduler_generation_used": False,
        "next_stage": route["next_stage"],
        "recommended_next_work": route["allowed_next_work"],
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_pool_summary(pool_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": POOL_SUMMARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": PASS_STATUS,
        "pool_rows": list(pool_rows),
        "same_train_side_evaluator_used": True,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_fe_ledger(
    *, trace_rows: Sequence[Mapping[str, Any]], inherited_stage8_20_fe_total: int
) -> dict[str, Any]:
    totals = {
        key: sum(int(row.get(key, 0)) for row in trace_rows)
        for key in [
            "FE_grouping",
            "FE_proposal",
            "FE_coordination_extra",
            "FE_repair",
            "FE_global_objective",
            "FE_total",
        ]
    }
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": PASS_STATUS,
        "budget_scope": "llm_vs_non_llm_contribution_ablation",
        "inherited_stage8_20_FE_total": inherited_stage8_20_fe_total,
        **totals,
        "all_extra_fe_counted": True,
        "objective_loop_executed": True,
        "new_objective_evaluation_used": True,
        "llm_call_used": False,
        "new_llm_candidate_generation_used": False,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_runtime_boundary() -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": PASS_STATUS,
        "claim_scope": "LLM contribution ablation under train-side evaluator",
        "objective_loop_executed": True,
        "new_objective_evaluation_used": True,
        "llm_call_used": False,
        "new_llm_candidate_generation_used": False,
        "fake_llm_candidates_used": False,
        "forbidden_behaviors": {
            "new_llm_candidate_generation": False,
            "fake_llm_candidate_generation": False,
            "selected_operator_revision": False,
            "evolution_search": False,
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
        "status": PASS_STATUS,
        "decision": "ROUTE_TO_FREEZE_LLM_ORIGIN_BEAT_BEST_REWARD_POLICY",
        "next_stage": "Stage 8.22",
        "allowed_next_work": "freeze_llm_origin_beat_best_reward_policy",
        "next_route": "freeze_llm_origin_beat_best_reward_policy",
        "run_full_25_run_panel_next": False,
        "use_validation_feedback": False,
        "use_test_feedback": False,
        "use_reported_results_as_runtime_feedback": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _policy(
    *,
    policy_id: str,
    origin: str,
    family: str,
    rules: Sequence[Mapping[str, str]],
    features: Sequence[str] | None = None,
    memory: Sequence[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": POLICY_SCHEMA_VERSION,
        "policy_id": policy_id,
        "origin": origin,
        "family": family,
        "target_scope": "shared_variables_only",
        "features": list(
            features
            or [
                "reward_margin",
                "reward_concentration",
                "conflict_intensity",
                "proposal_dispersion",
                "direction_consistency",
                "shared_variable_oscillation",
                "recent_best_reward_regret",
            ]
        ),
        "memory": list(memory or ["recent_best_reward_regret"]),
        "rules": [dict(rule) for rule in rules],
        "forbidden_capabilities_used": [],
    }


def _hand_designed_pool() -> list[dict[str, Any]]:
    return [
        _policy(
            policy_id="stage8_21_hand_simple_consensus",
            origin="hand_designed",
            family="AlwaysSimpleConsensus",
            rules=[{"condition": "always", "action": "simple_consensus"}],
        ),
        _policy(
            policy_id="stage8_21_hand_weighted_consensus",
            origin="hand_designed",
            family="AlwaysWeightedConsensus",
            rules=[{"condition": "always", "action": "weighted_consensus"}],
        ),
        _policy(
            policy_id="stage8_21_hand_trust_then_weighted",
            origin="hand_designed",
            family="TrustThenWeighted",
            rules=[
                {
                    "condition": "high reward_concentration",
                    "action": "trust_best_reward",
                },
                {"condition": "always", "action": "weighted_consensus"},
            ],
        ),
    ]


def _random_mutation_pool() -> list[dict[str, Any]]:
    return [
        _policy(
            policy_id="stage8_21_random_mutation_a",
            origin="random_mutation",
            family="RandomConditionOrderA",
            rules=[
                {"condition": "low direction_consistency", "action": "weighted_consensus"},
                {"condition": "always", "action": "trust_best_reward"},
            ],
        ),
        _policy(
            policy_id="stage8_21_random_mutation_b",
            origin="random_mutation",
            family="RandomConditionOrderB",
            rules=[
                {"condition": "high proposal_dispersion", "action": "simple_consensus"},
                {"condition": "always", "action": "damp_best_reward"},
            ],
        ),
        _policy(
            policy_id="stage8_21_random_mutation_c",
            origin="random_mutation",
            family="RandomConditionOrderC",
            rules=[
                {"condition": "reward_margin > 0.1", "action": "trust_best_reward"},
                {"condition": "always", "action": "simple_consensus"},
            ],
        ),
    ]


def _literature_inspired_pool() -> list[dict[str, Any]]:
    return [
        _policy(
            policy_id="stage8_21_literature_weighted_consensus",
            origin="literature_inspired",
            family="RewardWeightedConsensus",
            rules=[
                {"condition": "low reward_margin", "action": "weighted_consensus"},
                {"condition": "always", "action": "trust_best_reward"},
            ],
        ),
        _policy(
            policy_id="stage8_21_literature_dispersion_average",
            origin="literature_inspired",
            family="DispersionAverage",
            rules=[
                {"condition": "high proposal_dispersion", "action": "simple_consensus"},
                {"condition": "always", "action": "weighted_consensus"},
            ],
        ),
        _policy(
            policy_id="stage8_21_literature_regret_damping",
            origin="literature_inspired",
            family="RegretDamping",
            rules=[
                {"condition": "high recent_best_reward_regret", "action": "damp_best_reward"},
                {"condition": "always", "action": "weighted_consensus"},
            ],
        ),
    ]


def _stage8_16_human_repair_pool() -> list[dict[str, Any]]:
    return [
        _policy(
            policy_id="stage8_21_stage8_16_human_repair",
            origin="stage8_16_human_repair",
            family="HumanRepairTrustGate",
            rules=[
                {
                    "condition": "high reward_margin AND high direction_consistency",
                    "action": "trust_best_reward",
                },
                {"condition": "always", "action": "damp_best_reward"},
            ],
        )
    ]


def _pool_by_id(
    pool_rows: Sequence[Mapping[str, Any]], pool_id: str
) -> Mapping[str, Any]:
    for row in pool_rows:
        if row["pool_id"] == pool_id:
            return row
    raise ValueError(f"missing pool: {pool_id}")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
