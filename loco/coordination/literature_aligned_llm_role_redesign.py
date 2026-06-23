"""Stage 8.25 read-only failure diagnosis and LLM role redesign."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


STAGE = "8.25"
REPORT_SCHEMA_VERSION = "loco.stage8_25_literature_aligned_redesign_report.v1"
FAILURE_SCHEMA_VERSION = "loco.stage8_25_failure_diagnosis.v1"
LITERATURE_SCHEMA_VERSION = "loco.stage8_25_literature_alignment_matrix.v1"
ROLE_SCHEMA_VERSION = "loco.stage8_25_llm_role_redesign.v1"
DSL_SCHEMA_VERSION = "loco.stage8_25_ownership_aware_strategy_dsl_contract.v1"
FE_LEDGER_SCHEMA_VERSION = "loco.stage8_25_fe_ledger.v1"
BOUNDARY_SCHEMA_VERSION = "loco.stage8_25_runtime_boundary.v1"
NEXT_ROUTE_SCHEMA_VERSION = "loco.stage8_25_next_route_decision.v1"


def run_stage8_25_literature_aligned_llm_role_redesign(
    *,
    stage8_24_checkpoint_report_path: Path | str,
    stage8_24_win_loss_path: Path | str,
    stage8_24_policy_branch_path: Path | str,
    stage8_24_fe_ledger_path: Path | str,
    stage8_24_runtime_boundary_path: Path | str,
    stage8_24_next_route_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Read Stage 8.24 evidence and lock the Stage 8.26 redesign contract."""

    checkpoint_report = _read_json(Path(stage8_24_checkpoint_report_path))
    win_loss = _read_json(Path(stage8_24_win_loss_path))
    branch = _read_json(Path(stage8_24_policy_branch_path))
    ledger8_24 = _read_json(Path(stage8_24_fe_ledger_path))
    boundary8_24 = _read_json(Path(stage8_24_runtime_boundary_path))
    route8_24 = _read_json(Path(stage8_24_next_route_path))
    _validate_inputs(
        checkpoint_report=checkpoint_report,
        win_loss=win_loss,
        branch=branch,
        ledger8_24=ledger8_24,
        boundary8_24=boundary8_24,
        route8_24=route8_24,
    )

    failure = _build_failure_diagnosis(checkpoint_report, win_loss, branch)
    literature = _build_literature_alignment_matrix()
    role = _build_llm_role_redesign()
    dsl = _build_strategy_dsl_contract()
    ledger = _build_fe_ledger(ledger8_24)
    boundary = _build_runtime_boundary()
    route = _build_next_route()
    report = _build_report(
        checkpoint_report=checkpoint_report,
        win_loss=win_loss,
        failure=failure,
        role=role,
        dsl=dsl,
        route=route,
    )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    _write_json(output_path / "stage8_24_failure_diagnosis.json", failure)
    _write_json(output_path / "literature_alignment_matrix.json", literature)
    _write_json(output_path / "llm_role_redesign.json", role)
    _write_json(output_path / "ownership_aware_strategy_dsl_contract.json", dsl)
    _write_json(output_path / "fe_ledger.json", ledger)
    _write_json(output_path / "runtime_boundary.json", boundary)
    _write_json(output_path / "next_route_decision.json", route)
    _write_json(output_path / "stage8_25_report.json", report)
    return report


def _validate_inputs(
    *,
    checkpoint_report: Mapping[str, Any],
    win_loss: Mapping[str, Any],
    branch: Mapping[str, Any],
    ledger8_24: Mapping[str, Any],
    boundary8_24: Mapping[str, Any],
    route8_24: Mapping[str, Any],
) -> None:
    if checkpoint_report.get("stage") != "8.24" or checkpoint_report.get("status") != "PASS":
        raise ValueError("Stage 8.25 requires a passing Stage 8.24 checkpoint report.")
    if checkpoint_report.get("checkpoint_budget_pilot_executed") is not True:
        raise ValueError("Stage 8.24 checkpoint pilot evidence is required.")
    if win_loss.get("stage") != "8.24":
        raise ValueError("Stage 8.25 requires the Stage 8.24 win/loss report.")
    if branch.get("stage") != "8.24":
        raise ValueError("Stage 8.25 requires the Stage 8.24 policy branch report.")
    if int(ledger8_24.get("FE_total", 0)) <= 0:
        raise ValueError("Stage 8.24 must have counted objective FE.")
    if boundary8_24.get("full_objective_trace_written") is not False:
        raise ValueError("Stage 8.25 expects compact Stage 8.24 checkpoint artifacts.")
    if route8_24.get("next_stage") != "Stage 8.25":
        raise ValueError("Stage 8.25 requires the Stage 8.24 route.")


def _build_failure_diagnosis(
    checkpoint_report: Mapping[str, Any],
    win_loss: Mapping[str, Any],
    branch: Mapping[str, Any],
) -> dict[str, Any]:
    branch_counts = dict(branch["branch_counts"])
    trust_count = int(branch_counts.get("trust_best_reward", 0))
    non_trust_count = sum(
        int(count) for name, count in branch_counts.items() if name != "trust_best_reward"
    )
    win_counts = dict(win_loss["frozen_policy_vs_best_reward_select"])
    behavior_equivalent = (
        int(win_counts["win"]) == 0
        and int(win_counts["loss"]) == 0
        and int(non_trust_count) == 0
    )
    return {
        "schema_version": FAILURE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.24",
        "selected_candidate_id": str(checkpoint_report["selected_candidate_id"]),
        "failure_mode": "branch_collapse_to_best_reward_select",
        "branch_collapse_detected": True,
        "collapsed_branch": "trust_best_reward",
        "trust_best_reward_branch_count": trust_count,
        "non_trust_branch_count": int(non_trust_count),
        "stage8_24_policy_behavior_equivalent_to_best_reward": behavior_equivalent,
        "stage8_24_checkpoint_win_count_vs_best_reward": int(win_counts["win"]),
        "stage8_24_checkpoint_loss_count_vs_best_reward": int(win_counts["loss"]),
        "stage8_24_checkpoint_tie_count_vs_best_reward": int(win_counts["tie"]),
        "root_cause_hypothesis": (
            "policy_features_do_not_trigger_ownership_or_repair_branches_on_cec_f13_f14"
        ),
        "why_not_formal_25_run_now": (
            "The 120000-FE checkpoint did not show superiority and the frozen policy "
            "is behavior-equivalent to best_reward_select on all policy steps."
        ),
        "formal_25_run_recommended_now": False,
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_literature_alignment_matrix() -> dict[str, Any]:
    items = [
        {
            "short_name": "DG",
            "topic": "variable interaction decomposition for LSGO",
            "relevance": "decomposition quality drives cooperative coevolution performance",
            "url": "https://eprints.whiterose.ac.uk/id/eprint/156228/1/PID2794611.pdf",
        },
        {
            "short_name": "RDG3",
            "topic": "overlapping component decomposition",
            "relevance": "overlap handling requires linkage break/preserve decisions, not only final-value consensus",
            "url": "https://phoenixwilliams.github.io/PersonalWebsite/LargeScaleEA/Decomposition_for_Large-scale_Optimization_Problems_with_Overlapping_Components.pdf",
        },
        {
            "short_name": "OEDG",
            "topic": "enhanced differential grouping for large-scale overlapping problems",
            "relevance": "explicitly separates subcomponent and shared-variable identification/refinement",
            "url": "https://arxiv.org/html/2404.10515v1",
        },
        {
            "short_name": "FEA",
            "topic": "overlapping factor decomposition",
            "relevance": "allows variables to belong to multiple factors and compete through global solution updates",
            "url": "https://www.cs.montana.edu/sheppard/pubs/ssci-sis-2021b.pdf",
        },
        {
            "short_name": "FunSearch",
            "topic": "LLM program search with evaluator feedback",
            "relevance": "LLM should participate in an evaluator-in-the-loop program design process",
            "url": "https://www.nature.com/articles/s41586-023-06924-6",
        },
        {
            "short_name": "EoH",
            "topic": "evolution of heuristics with LLMs",
            "relevance": "automatic algorithm design uses iterative generation and selection, not one-shot prompts",
            "url": "https://arxiv.org/abs/2401.02051",
        },
        {
            "short_name": "ReEvo",
            "topic": "reflective evolution for LLM hyper-heuristics",
            "relevance": "failure feedback can become verbal gradients for the next strategy generation round",
            "url": "https://openreview.net/forum?id=483IPG0HWL",
        },
        {
            "short_name": "LLaMEA",
            "topic": "LLM evolutionary algorithm for generating metaheuristics",
            "relevance": "continuous optimization LLM design loops need benchmark feedback and archive pressure",
            "url": "https://arxiv.org/html/2405.20132v3",
        },
    ]
    return {
        "schema_version": LITERATURE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "literature_count": len(items),
        "items": items,
        "alignment_summary": (
            "LSGO literature points to decomposition and shared-variable ownership; "
            "LLM-AAD literature points to evaluator-in-the-loop reflective program search."
        ),
        "design_consequence": (
            "Stage 8.26 must move from static action selection to an ownership-aware "
            "decomposition/coordination strategy DSL with behavior-equivalence guards."
        ),
    }


def _build_llm_role_redesign() -> dict[str, Any]:
    return {
        "schema_version": ROLE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "rejected_role": "one_shot_or_static_coordination_action_generator",
        "old_llm_role": "static_shared_variable_coordination_policy_generator",
        "new_llm_role": (
            "reflective_decomposition_ownership_coordination_strategy_program_designer"
        ),
        "new_program_outputs": [
            "shared_variable_owner",
            "allow_multi_assignment",
            "linkage_break_or_preserve",
            "coordination_action",
            "fallback_repair_action",
            "behavior_equivalence_guard",
        ],
        "feedback_loop_required": True,
        "failure_feedback_to_include": [
            "branch_collapse_to_best_reward_select",
            "behavior_equivalent_to_best_reward_select",
            "non_trust_branch_not_exercised",
            "ownership_or_linkage_decision_missing",
        ],
        "not_optimizer_generation": True,
        "not_scheduler_controller_generation": True,
    }


def _build_strategy_dsl_contract() -> dict[str, Any]:
    return {
        "schema_version": DSL_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "target_scope": "shared_variables_and_decomposition_consequences",
        "stage8_26_mvp_required": True,
        "allowed_outputs": [
            "shared_variable_owner",
            "allow_multi_assignment",
            "linkage_break_or_preserve",
            "contribution_based_owner_switch",
            "coordination_action",
            "fallback_repair_action",
            "behavior_equivalence_guard",
        ],
        "allowed_coordination_actions": [
            "trust_best_reward",
            "damp_best_reward",
            "weighted_consensus",
            "simple_consensus",
            "shrinkage_repair",
            "reject_unstable_best_reward",
            "owner_proposal_select",
            "multi_owner_weighted_vote",
        ],
        "behavior_equivalence_guards": [
            "not_equivalent_to_best_reward_select",
            "non_trust_branch_exercised",
            "ownership_or_linkage_decision_exercised",
        ],
        "required_evaluator_reports": [
            "behavior_equivalence_report",
            "branch_coverage_report",
            "ownership_decision_coverage_report",
            "train_side_win_loss_report",
        ],
        "forbidden_capabilities": [
            "generate_optimizer",
            "modify_baseopt",
            "rewrite_benchmark_objective",
            "generate_scheduler_or_controller",
            "use_validation_feedback",
            "use_test_feedback",
            "use_reported_sota_as_runtime_feedback",
        ],
        "not_sota_claim": True,
        "not_final_performance_claim": True,
    }


def _build_fe_ledger(stage8_24_ledger: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": FE_LEDGER_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "scope": "read_only_stage8_24_failure_diagnosis_and_design_lock",
        "inherited_stage8_24_FE_total": int(stage8_24_ledger["FE_total"]),
        "FE_grouping": 0,
        "FE_proposal": 0,
        "FE_coordination_extra": 0,
        "FE_repair": 0,
        "FE_global_objective": 0,
        "FE_total": 0,
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "all_extra_fe_counted": True,
    }


def _build_runtime_boundary() -> dict[str, Any]:
    return {
        "schema_version": BOUNDARY_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "claim_scope": "Stage 8.25 read-only literature-aligned redesign",
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "llm_call_used": False,
        "new_candidate_generation_used": False,
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


def _build_next_route() -> dict[str, Any]:
    return {
        "schema_version": NEXT_ROUTE_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "decision": "ROUTE_TO_STAGE8_26_MVP_STRATEGY_DSL",
        "next_stage": "Stage 8.26",
        "allowed_next_work": "mvp_strategy_dsl_evaluator_behavior_equivalence_checker",
        "run_objective_next": False,
        "call_llm_next": False,
        "run_full_25_run_panel_next": False,
        "use_validation_feedback": False,
        "use_test_feedback": False,
        "use_reported_results_as_runtime_feedback": False,
        "sota_claim_made": False,
        "not_performance_claim": True,
    }


def _build_report(
    *,
    checkpoint_report: Mapping[str, Any],
    win_loss: Mapping[str, Any],
    failure: Mapping[str, Any],
    role: Mapping[str, Any],
    dsl: Mapping[str, Any],
    route: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "stage": STAGE,
        "status": "PASS",
        "source_stage": "8.24",
        "analysis_scope": "literature_aligned_llm_role_redesign",
        "selected_candidate_id": str(checkpoint_report["selected_candidate_id"]),
        "stage8_24_failure_mode": str(failure["failure_mode"]),
        "stage8_24_policy_behavior_equivalent_to_best_reward": bool(
            failure["stage8_24_policy_behavior_equivalent_to_best_reward"]
        ),
        "stage8_24_checkpoint_win_count_vs_best_reward": int(
            win_loss["frozen_policy_vs_best_reward_select"]["win"]
        ),
        "stage8_24_checkpoint_loss_count_vs_best_reward": int(
            win_loss["frozen_policy_vs_best_reward_select"]["loss"]
        ),
        "stage8_24_non_trust_branch_exercised": False,
        "llm_role_redefined": True,
        "old_llm_role": str(role["old_llm_role"]),
        "new_llm_role": str(role["new_llm_role"]),
        "new_strategy_dsl_locked": True,
        "stage8_26_mvp_strategy_dsl_required": bool(dsl["stage8_26_mvp_required"]),
        "recommended_next_stage": route["next_stage"],
        "recommended_next_work": route["allowed_next_work"],
        "FE_total": 0,
        "objective_loop_executed": False,
        "new_objective_evaluation_used": False,
        "llm_call_used": False,
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


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
