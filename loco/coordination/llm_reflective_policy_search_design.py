"""Stage 8.19 LLM-reflective coordination policy search design lock.

This stage redirects the post-Stage-8.18 path away from static one-shot LLM
candidate expansion. It locks a future LLM-reflective design loop where LLMs
generate shared-variable coordination policy programs under evaluator feedback.
It does not execute that loop, call an LLM, evaluate objectives, or make SOTA
claims.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


STAGE = "8.19"
DESIGN_SCHEMA_VERSION = "loco.stage8_19_llm_reflective_policy_search_design.v1"
PROMPT_SCHEMA_VERSION = "loco.stage8_19_reflection_prompt_contract.v1"
DSL_SCHEMA_VERSION = "loco.stage8_19_coordination_policy_dsl_contract.v1"
ABLATION_SCHEMA_VERSION = "loco.stage8_19_llm_contribution_ablation_plan.v1"
GATE_SCHEMA_VERSION = "loco.stage8_19_beat_best_reward_gate.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_19_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_19_runtime_boundary.v1"
NEXT_ROUTE_SCHEMA_VERSION = "loco.stage8_19_next_route_decision.v1"

NEXT_STAGE = "Stage 8.20"
NEXT_WORK = "execute_llm_reflective_coordination_policy_search"
IMPLEMENTATION_STATUS = "DESIGN_LOCK_ONLY"

FAILURE_PATTERNS = [
    "best_reward_short_horizon_regret",
    "shared_variable_oscillation",
    "low_reward_margin_unreliability",
    "direction_flip_under_conflicting_overlap",
    "stage8_18_always_trust_best_reward_degeneracy",
]

ALLOWED_FEATURES = [
    "reward_margin",
    "reward_concentration",
    "conflict_intensity",
    "proposal_dispersion",
    "direction_consistency",
    "shared_variable_oscillation",
    "recent_best_reward_regret",
]

ALLOWED_ACTIONS = [
    "trust_best_reward",
    "damp_best_reward",
    "weighted_consensus",
    "simple_consensus",
    "shrinkage_repair",
    "reject_unstable_best_reward",
]

COMPARISON_POOLS = [
    "llm_reflective_pool",
    "hand_designed_pool",
    "random_mutation_pool",
    "literature_inspired_pool",
    "stage8_16_human_repair_policy",
]


def run_stage8_19_llm_reflective_policy_search_design(
    *,
    stage8_18_resmoke_report_path: Path | str,
    stage8_18_win_loss_path: Path | str,
    stage8_18_policy_branch_path: Path | str,
    stage8_18_fe_ledger_path: Path | str,
    stage8_18_runtime_boundary_path: Path | str,
    stage8_18_next_route_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Write Stage 8.19 design-lock artifacts."""

    resmoke = _read_json(Path(stage8_18_resmoke_report_path))
    win_loss = _read_json(Path(stage8_18_win_loss_path))
    branch = _read_json(Path(stage8_18_policy_branch_path))
    ledger_input = _read_json(Path(stage8_18_fe_ledger_path))
    boundary_input = _read_json(Path(stage8_18_runtime_boundary_path))
    route_input = _read_json(Path(stage8_18_next_route_path))
    _validate_inputs(
        resmoke=resmoke,
        win_loss=win_loss,
        branch=branch,
        ledger=ledger_input,
        boundary=boundary_input,
        route=route_input,
    )

    stage8_18_equivalent = _stage8_18_equivalent_to_best_reward(
        win_loss=win_loss, branch=branch
    )
    non_trust_exercised = _non_trust_branch_exercised(branch)
    prompt = _build_prompt_contract()
    dsl = _build_dsl_contract()
    ablation = _build_contribution_ablation_plan()
    gate = _build_beat_best_reward_gate()
    ledger = _build_fe_ledger(ledger_input)
    boundary = _build_runtime_boundary()
    route = _build_next_route()
    report = _build_design_report(
        resmoke=resmoke,
        stage8_18_equivalent=stage8_18_equivalent,
        non_trust_exercised=non_trust_exercised,
        ledger=ledger,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_json(output_path / "llm_reflective_policy_search_design.json", report)
    _write_json(output_path / "reflection_prompt_contract.json", prompt)
    _write_json(output_path / "coordination_policy_dsl_contract.json", dsl)
    _write_json(output_path / "llm_contribution_ablation_plan.json", ablation)
    _write_json(output_path / "beat_best_reward_gate.json", gate)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", route)
    return report


def _validate_inputs(
    *,
    resmoke: Mapping[str, Any],
    win_loss: Mapping[str, Any],
    branch: Mapping[str, Any],
    ledger: Mapping[str, Any],
    boundary: Mapping[str, Any],
    route: Mapping[str, Any],
) -> None:
    if resmoke.get("stage") != "8.18" or resmoke.get("status") != "PASS":
        raise ValueError("Stage 8.19 requires a passing Stage 8.18 resmoke report.")
    if resmoke.get("repaired_policy_resmoke_promising") is not True:
        raise ValueError("Stage 8.19 requires promising Stage 8.18 resmoke evidence.")
    if win_loss.get("stage") != "8.18" or win_loss.get("status") != "PASS":
        raise ValueError("Stage 8.19 requires the Stage 8.18 win/loss report.")
    if int(win_loss["repaired_vs_best_reward_select"]["loss"]) != 0:
        raise ValueError("Stage 8.19 requires no Stage 8.18 loss vs best_reward_select.")
    if branch.get("stage") != "8.18" or branch.get("status") != "PASS":
        raise ValueError("Stage 8.19 requires the Stage 8.18 branch report.")
    if int(branch["branch_counts"]["trust_best_reward"]) <= 0:
        raise ValueError("Stage 8.19 requires Stage 8.18 trust-best-reward evidence.")
    if ledger.get("objective_loop_executed") is not True:
        raise ValueError("Stage 8.19 requires Stage 8.18 objective-loop evidence.")
    if boundary.get("not_sota_claim") is not True:
        raise ValueError("Stage 8.19 requires Stage 8.18 no-SOTA boundary.")
    if route.get("next_stage") != "Stage 8.19":
        raise ValueError("Stage 8.19 requires the Stage 8.18 route.")
    _validate_forbidden_stage8_18_flags(resmoke)


def _validate_forbidden_stage8_18_flags(report: Mapping[str, Any]) -> None:
    for key in [
        "selected_operator_revision_used",
        "evolution_search_used",
        "validation_feedback_used",
        "test_feedback_used",
        "reported_results_used_as_runtime_feedback",
        "baseopt_modified",
        "optimizer_generation_used",
        "controller_scheduler_generation_used",
    ]:
        if report.get(key) is not False:
            raise ValueError(f"Stage 8.19 rejects forbidden input behavior: {key}")


def _stage8_18_equivalent_to_best_reward(
    *, win_loss: Mapping[str, Any], branch: Mapping[str, Any]
) -> bool:
    repaired_vs_best_reward = win_loss["repaired_vs_best_reward_select"]
    branch_counts = branch["branch_counts"]
    return (
        int(repaired_vs_best_reward["win"]) == 0
        and int(repaired_vs_best_reward["tie"]) == int(win_loss["comparison_case_count"])
        and int(repaired_vs_best_reward["loss"]) == 0
        and int(branch_counts["trust_best_reward"]) == int(branch["policy_trace_row_count"])
        and not _non_trust_branch_exercised(branch)
    )


def _non_trust_branch_exercised(branch: Mapping[str, Any]) -> bool:
    counts = branch["branch_counts"]
    return any(
        int(counts[name]) > 0
        for name in ["weighted_safety", "simple_safety", "shrinkage_repair"]
    )


def _build_prompt_contract() -> dict[str, Any]:
    return {
        "schema_version": PROMPT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "prompt_scope": "llm_reflective_shared_variable_coordination_policy_search",
        "failure_patterns_used": FAILURE_PATTERNS,
        "reflection_loop": [
            "mine_best_reward_failure_and_degeneracy_patterns",
            "prompt_llm_for_shared_variable_coordination_policy_programs",
            "audit_candidates_against_dsl_and_boundary",
            "evaluate_on_train_side_objective_cases",
            "feed_top_candidates_and_failure_summaries_back_to_llm",
            "generate_mutated_or_repaired_policy_programs",
        ],
        "minimum_reflection_round_count": 2,
        "minimum_raw_llm_candidate_count": 24,
        "minimum_quality_pass_candidate_count": 8,
        "minimum_coordination_family_count": 4,
        "real_llm_api_required_for_execution": True,
        "fake_llm_candidates_forbidden": True,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_dsl_contract() -> dict[str, Any]:
    return {
        "schema_version": DSL_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "target_scope": "shared_variables_only",
        "program_unit": "coordination_policy_program",
        "allowed_features": ALLOWED_FEATURES,
        "allowed_actions": ALLOWED_ACTIONS,
        "allowed_memory": [
            "recent_best_reward_regret",
            "recent_shared_variable_direction",
            "recent_policy_branch_outcomes",
        ],
        "forbidden_capabilities": [
            "optimizer_generation",
            "baseopt_modification",
            "controller_scheduler_generation",
            "benchmark_objective_rewrite",
            "validation_feedback_access",
            "test_feedback_access",
            "reported_results_runtime_feedback",
        ],
        "output_format": "json_policy_program",
        "static_audit_required": True,
        "not_sota_claim": True,
    }


def _build_contribution_ablation_plan() -> dict[str, Any]:
    return {
        "schema_version": ABLATION_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "llm_vs_non_llm_ablation_required": True,
        "comparison_pools": COMPARISON_POOLS,
        "metrics": [
            "quality_pass_rate",
            "family_diversity",
            "non_degenerate_candidate_count",
            "train_objective_win_count_vs_best_reward",
            "train_objective_loss_count_vs_best_reward",
            "candidate_pool_best_rank",
            "candidate_pool_median_rank",
        ],
        "llm_pool_beats_non_llm_pool_required_for_pass": True,
        "stage8_16_human_repair_policy_is_baseline_not_llm_success": True,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_beat_best_reward_gate() -> dict[str, Any]:
    return {
        "schema_version": GATE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "selected_candidate_origin_required": "llm_reflective_generated",
        "selected_candidate_not_equivalent_to_best_reward_required": True,
        "non_trust_best_reward_branch_exercised_required": True,
        "win_count_vs_best_reward_select_min": 1,
        "loss_count_vs_best_reward_select_max": 0,
        "llm_contribution_evidence_required": True,
        "pass_condition_is_not_no_loss": True,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_fe_ledger(stage8_18_ledger: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "budget_scope": "llm_reflective_policy_search_design_lock_only",
        "implementation_status": IMPLEMENTATION_STATUS,
        "FE_grouping": 0,
        "FE_proposal": 0,
        "FE_coordination_extra": 0,
        "FE_repair": 0,
        "FE_global_objective": 0,
        "FE_total": 0,
        "inherited_stage8_18_FE_total": int(stage8_18_ledger["FE_total"]),
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "llm_call_used": False,
        "new_llm_candidate_generation_used": False,
        "not_final_performance_claim": True,
    }


def _build_runtime_boundary() -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "claim_scope": "Stage 8.19 design lock only",
        "implementation_status": IMPLEMENTATION_STATUS,
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "llm_call_used": False,
        "new_llm_candidate_generation_used": False,
        "forbidden_behaviors": {
            "fake_llm_candidate_generation": True,
            "baseopt_modification": False,
            "optimizer_generation": False,
            "controller_scheduler_generation": False,
            "validation_feedback": False,
            "test_feedback": False,
            "reported_results_runtime_feedback": False,
        },
        "required_future_behaviors": {
            "real_llm_api_call_for_execution": True,
            "objective_evaluator_feedback_loop": True,
            "llm_vs_non_llm_ablation": True,
            "beat_best_reward_select_gate": True,
        },
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_next_route() -> dict[str, Any]:
    return {
        "schema_version": NEXT_ROUTE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "decision": "ROUTE_TO_EXECUTE_LLM_REFLECTIVE_POLICY_SEARCH",
        "decision_reason": (
            "Stage 8.19 rejects static one-shot candidate generation and locks "
            "an LLM-reflective shared-variable coordination policy search loop."
        ),
        "next_stage": NEXT_STAGE,
        "allowed_next_work": NEXT_WORK,
        "run_llm_reflective_search_next": True,
        "run_full_25_run_panel_next": False,
        "use_validation_feedback": False,
        "use_test_feedback": False,
        "use_reported_results_as_runtime_feedback": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _build_design_report(
    *,
    resmoke: Mapping[str, Any],
    stage8_18_equivalent: bool,
    non_trust_exercised: bool,
    ledger: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": DESIGN_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.18",
        "design_scope": "llm_reflective_coordination_policy_search_design",
        "llm_reflective_design_loop_locked": True,
        "static_one_shot_llm_candidate_generation_rejected": True,
        "objective_evaluator_feedback_required": True,
        "llm_contribution_ablation_required": True,
        "beat_best_reward_required": True,
        "stage8_18_policy_equivalent_to_best_reward": bool(stage8_18_equivalent),
        "non_trust_best_reward_branch_exercised_on_stage8_18": bool(
            non_trust_exercised
        ),
        "implementation_status": IMPLEMENTATION_STATUS,
        "required_future_llm_call": True,
        "fake_llm_candidates_forbidden": True,
        "recommended_next_stage": NEXT_STAGE,
        "recommended_next_work": NEXT_WORK,
        "FE_total": int(ledger["FE_total"]),
        "inherited_stage8_18_FE_total": int(resmoke["FE_total"]),
        "llm_call_used": False,
        "new_llm_candidate_generation_used": False,
        "selected_operator_revision_used": False,
        "evolution_search_used": False,
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
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


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
