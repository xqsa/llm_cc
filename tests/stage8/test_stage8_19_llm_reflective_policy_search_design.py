import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage8_19_llm_reflective_policy_search_design.yaml"
STAGE8_18_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_18"
OUTPUT_DIR = ROOT / "artifacts" / "selection_audit" / "stage8_19"
DESIGN_REPORT = OUTPUT_DIR / "llm_reflective_policy_search_design.json"
PROMPT_CONTRACT = OUTPUT_DIR / "reflection_prompt_contract.json"
DSL_CONTRACT = OUTPUT_DIR / "coordination_policy_dsl_contract.json"
CONTRIBUTION_ABLATION = OUTPUT_DIR / "llm_contribution_ablation_plan.json"
BEAT_BASELINE_GATE = OUTPUT_DIR / "beat_best_reward_gate.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
NEXT_ROUTE = OUTPUT_DIR / "next_route_decision.json"
STAGE_DOC = ROOT / "docs" / "stage8" / "stage8_19_llm_reflective_policy_search_design.md"
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_19_self_check_report.md"
README = ROOT / "README.md"


def test_stage8_19_locks_llm_reflective_policy_search_design(tmp_path) -> None:
    from loco.coordination.llm_reflective_policy_search_design import (
        run_stage8_19_llm_reflective_policy_search_design,
    )

    report = run_stage8_19_llm_reflective_policy_search_design(
        stage8_18_resmoke_report_path=STAGE8_18_DIR
        / "repaired_policy_resmoke_report.json",
        stage8_18_win_loss_path=STAGE8_18_DIR / "win_loss_report.json",
        stage8_18_policy_branch_path=STAGE8_18_DIR / "policy_branch_report.json",
        stage8_18_fe_ledger_path=STAGE8_18_DIR / "fe_ledger.json",
        stage8_18_runtime_boundary_path=STAGE8_18_DIR / "runtime_boundary.json",
        stage8_18_next_route_path=STAGE8_18_DIR / "next_route_decision.json",
        output_dir=tmp_path,
    )

    assert report["stage"] == "8.19"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "8.18"
    assert report["design_scope"] == "llm_reflective_coordination_policy_search_design"
    assert report["llm_reflective_design_loop_locked"] is True
    assert report["static_one_shot_llm_candidate_generation_rejected"] is True
    assert report["objective_evaluator_feedback_required"] is True
    assert report["llm_contribution_ablation_required"] is True
    assert report["beat_best_reward_required"] is True
    assert report["stage8_18_policy_equivalent_to_best_reward"] is True
    assert report["non_trust_best_reward_branch_exercised_on_stage8_18"] is False
    assert report["implementation_status"] == "DESIGN_LOCK_ONLY"
    assert report["llm_call_used"] is False
    assert report["new_llm_candidate_generation_used"] is False
    assert report["objective_loop_executed"] is False
    assert report["new_objective_evaluation_used"] is False
    assert report["FE_total"] == 0
    assert report["required_future_llm_call"] is True
    assert report["fake_llm_candidates_forbidden"] is True
    assert report["recommended_next_stage"] == "Stage 8.20"
    assert (
        report["recommended_next_work"]
        == "execute_llm_reflective_coordination_policy_search"
    )

    for flag in [
        "selected_operator_revision_used",
        "evolution_search_used",
        "validation_feedback_used",
        "test_feedback_used",
        "reported_results_used_as_runtime_feedback",
        "baseopt_modified",
        "optimizer_generation_used",
        "controller_scheduler_generation_used",
    ]:
        assert report[flag] is False
    assert report["not_sota_claim"] is True
    assert report["not_final_performance_claim"] is True

    prompt = json.loads((tmp_path / "reflection_prompt_contract.json").read_text())
    dsl = json.loads((tmp_path / "coordination_policy_dsl_contract.json").read_text())
    ablation = json.loads(
        (tmp_path / "llm_contribution_ablation_plan.json").read_text()
    )
    gate = json.loads((tmp_path / "beat_best_reward_gate.json").read_text())
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())

    assert prompt["failure_patterns_used"] == [
        "best_reward_short_horizon_regret",
        "shared_variable_oscillation",
        "low_reward_margin_unreliability",
        "direction_flip_under_conflicting_overlap",
        "stage8_18_always_trust_best_reward_degeneracy",
    ]
    assert prompt["minimum_reflection_round_count"] == 2
    assert prompt["minimum_raw_llm_candidate_count"] == 24
    assert prompt["real_llm_api_required_for_execution"] is True

    assert dsl["target_scope"] == "shared_variables_only"
    assert dsl["allowed_actions"] == [
        "trust_best_reward",
        "damp_best_reward",
        "weighted_consensus",
        "simple_consensus",
        "shrinkage_repair",
        "reject_unstable_best_reward",
    ]
    assert "optimizer_generation" in dsl["forbidden_capabilities"]
    assert "controller_scheduler_generation" in dsl["forbidden_capabilities"]

    assert ablation["llm_vs_non_llm_ablation_required"] is True
    assert ablation["comparison_pools"] == [
        "llm_reflective_pool",
        "hand_designed_pool",
        "random_mutation_pool",
        "literature_inspired_pool",
        "stage8_16_human_repair_policy",
    ]
    assert ablation["llm_pool_beats_non_llm_pool_required_for_pass"] is True

    assert gate["selected_candidate_origin_required"] == "llm_reflective_generated"
    assert gate["selected_candidate_not_equivalent_to_best_reward_required"] is True
    assert gate["non_trust_best_reward_branch_exercised_required"] is True
    assert gate["win_count_vs_best_reward_select_min"] == 1
    assert gate["loss_count_vs_best_reward_select_max"] == 0

    assert ledger["FE_total"] == 0
    assert ledger["implementation_status"] == "DESIGN_LOCK_ONLY"
    assert boundary["claim_scope"] == "Stage 8.19 design lock only"
    assert boundary["forbidden_behaviors"]["fake_llm_candidate_generation"] is True
    assert route["next_stage"] == "Stage 8.20"
    assert route["run_llm_reflective_search_next"] is True


def test_stage8_19_committed_artifacts_docs_and_readme_record_design_lock() -> None:
    required = [
        CONFIG,
        DESIGN_REPORT,
        PROMPT_CONTRACT,
        DSL_CONTRACT,
        CONTRIBUTION_ABLATION,
        BEAT_BASELINE_GATE,
        FE_LEDGER,
        RUNTIME_BOUNDARY,
        NEXT_ROUTE,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(DESIGN_REPORT.read_text(encoding="utf-8"))
    prompt = json.loads(PROMPT_CONTRACT.read_text(encoding="utf-8"))
    ablation = json.loads(CONTRIBUTION_ABLATION.read_text(encoding="utf-8"))
    gate = json.loads(BEAT_BASELINE_GATE.read_text(encoding="utf-8"))
    route = json.loads(NEXT_ROUTE.read_text(encoding="utf-8"))

    assert report["stage"] == "8.19"
    assert report["status"] == "PASS"
    assert report["llm_reflective_design_loop_locked"] is True
    assert prompt["real_llm_api_required_for_execution"] is True
    assert ablation["llm_vs_non_llm_ablation_required"] is True
    assert gate["win_count_vs_best_reward_select_min"] == 1
    assert route["next_stage"] == "Stage 8.20"

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Current repository state: `Stage 8.35 PASS`" in combined
    assert "Stage 8.19   LLM-reflective coordination policy search design lock     PASS" in combined
    assert "Stage 8.20   LLM-reflective coordination policy search execution       PASS" in combined
    assert "LLM-reflective shared-variable coordination policy search" in combined
    assert "static one-shot LLM candidate generation is rejected" in combined
    assert "fake LLM candidates are forbidden" in combined
    assert "not a final objective-value performance claim" in combined
    assert "not a SOTA claim" in combined
