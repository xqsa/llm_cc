import json
from pathlib import Path


ROOT = Path("E:/llm_cc")
STAGE8_24_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_24"
OUTPUT_DIR = ROOT / "artifacts" / "analysis" / "stage8_25"
CONFIG = ROOT / "configs" / "stage8_25_literature_aligned_llm_role_redesign.yaml"
FAILURE_DIAGNOSIS = OUTPUT_DIR / "stage8_24_failure_diagnosis.json"
LITERATURE_MATRIX = OUTPUT_DIR / "literature_alignment_matrix.json"
ROLE_REDESIGN = OUTPUT_DIR / "llm_role_redesign.json"
DSL_CONTRACT = OUTPUT_DIR / "ownership_aware_strategy_dsl_contract.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
NEXT_ROUTE = OUTPUT_DIR / "next_route_decision.json"
REPORT = OUTPUT_DIR / "stage8_25_report.json"
STAGE_DOC = ROOT / "docs" / "stage8" / "stage8_25_literature_aligned_llm_role_redesign.md"
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_25_self_check_report.md"
README = ROOT / "README.md"


def test_stage8_25_reads_stage8_24_and_locks_literature_aligned_redesign(tmp_path) -> None:
    from loco.coordination.literature_aligned_llm_role_redesign import (
        run_stage8_25_literature_aligned_llm_role_redesign,
    )

    report = run_stage8_25_literature_aligned_llm_role_redesign(
        stage8_24_checkpoint_report_path=STAGE8_24_DIR / "checkpoint_pilot_report.json",
        stage8_24_win_loss_path=STAGE8_24_DIR / "win_loss_report.json",
        stage8_24_policy_branch_path=STAGE8_24_DIR / "policy_branch_report.json",
        stage8_24_fe_ledger_path=STAGE8_24_DIR / "fe_ledger.json",
        stage8_24_runtime_boundary_path=STAGE8_24_DIR / "runtime_boundary.json",
        stage8_24_next_route_path=STAGE8_24_DIR / "next_route_decision.json",
        output_dir=tmp_path,
    )

    assert report["stage"] == "8.25"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "8.24"
    assert report["analysis_scope"] == "literature_aligned_llm_role_redesign"
    assert report["stage8_24_failure_mode"] == "branch_collapse_to_best_reward_select"
    assert report["stage8_24_policy_behavior_equivalent_to_best_reward"] is True
    assert report["stage8_24_checkpoint_win_count_vs_best_reward"] == 0
    assert report["stage8_24_checkpoint_loss_count_vs_best_reward"] == 0
    assert report["stage8_24_non_trust_branch_exercised"] is False
    assert report["llm_role_redefined"] is True
    assert report["old_llm_role"] == "static_shared_variable_coordination_policy_generator"
    assert (
        report["new_llm_role"]
        == "reflective_decomposition_ownership_coordination_strategy_program_designer"
    )
    assert report["new_strategy_dsl_locked"] is True
    assert report["stage8_26_mvp_strategy_dsl_required"] is True
    assert report["recommended_next_stage"] == "Stage 8.26"
    assert report["recommended_next_work"] == "mvp_strategy_dsl_evaluator_behavior_equivalence_checker"
    assert report["FE_total"] == 0
    assert report["objective_loop_executed"] is False
    assert report["new_objective_evaluation_used"] is False
    assert report["llm_call_used"] is False
    assert report["new_candidate_generation_used"] is False

    failure = json.loads((tmp_path / "stage8_24_failure_diagnosis.json").read_text())
    literature = json.loads((tmp_path / "literature_alignment_matrix.json").read_text())
    redesign = json.loads((tmp_path / "llm_role_redesign.json").read_text())
    dsl = json.loads((tmp_path / "ownership_aware_strategy_dsl_contract.json").read_text())
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())

    assert failure["branch_collapse_detected"] is True
    assert failure["collapsed_branch"] == "trust_best_reward"
    assert failure["trust_best_reward_branch_count"] == 720000
    assert failure["non_trust_branch_count"] == 0
    assert failure["root_cause_hypothesis"] == "policy_features_do_not_trigger_ownership_or_repair_branches_on_cec_f13_f14"
    assert failure["formal_25_run_recommended_now"] is False

    assert literature["literature_count"] >= 6
    assert literature["alignment_summary"] == (
        "LSGO literature points to decomposition and shared-variable ownership; "
        "LLM-AAD literature points to evaluator-in-the-loop reflective program search."
    )
    assert {"OEDG", "RDG3", "FunSearch", "ReEvo"}.issubset(
        {item["short_name"] for item in literature["items"]}
    )

    assert redesign["rejected_role"] == "one_shot_or_static_coordination_action_generator"
    assert "shared_variable_owner" in redesign["new_program_outputs"]
    assert "linkage_break_or_preserve" in redesign["new_program_outputs"]
    assert "coordination_action" in redesign["new_program_outputs"]
    assert redesign["feedback_loop_required"] is True

    assert dsl["target_scope"] == "shared_variables_and_decomposition_consequences"
    assert dsl["stage8_26_mvp_required"] is True
    assert dsl["allowed_outputs"] == [
        "shared_variable_owner",
        "allow_multi_assignment",
        "linkage_break_or_preserve",
        "contribution_based_owner_switch",
        "coordination_action",
        "fallback_repair_action",
        "behavior_equivalence_guard",
    ]
    assert "generate_optimizer" in dsl["forbidden_capabilities"]
    assert "modify_baseopt" in dsl["forbidden_capabilities"]
    assert dsl["behavior_equivalence_guards"] == [
        "not_equivalent_to_best_reward_select",
        "non_trust_branch_exercised",
        "ownership_or_linkage_decision_exercised",
    ]

    assert ledger["FE_total"] == 0
    assert boundary["claim_scope"] == "Stage 8.25 read-only literature-aligned redesign"
    assert boundary["objective_loop_executed"] is False
    assert boundary["llm_call_used"] is False
    assert route["next_stage"] == "Stage 8.26"
    assert route["run_objective_next"] is False
    assert route["call_llm_next"] is False


def test_stage8_25_committed_artifacts_docs_and_readme_record_redesign() -> None:
    required = [
        CONFIG,
        FAILURE_DIAGNOSIS,
        LITERATURE_MATRIX,
        ROLE_REDESIGN,
        DSL_CONTRACT,
        FE_LEDGER,
        RUNTIME_BOUNDARY,
        NEXT_ROUTE,
        REPORT,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    failure = json.loads(FAILURE_DIAGNOSIS.read_text(encoding="utf-8"))
    literature = json.loads(LITERATURE_MATRIX.read_text(encoding="utf-8"))
    dsl = json.loads(DSL_CONTRACT.read_text(encoding="utf-8"))
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))
    route = json.loads(NEXT_ROUTE.read_text(encoding="utf-8"))

    assert report["stage"] == "8.25"
    assert report["status"] == "PASS"
    assert failure["branch_collapse_detected"] is True
    assert literature["literature_count"] >= 6
    assert dsl["stage8_26_mvp_required"] is True
    assert ledger["FE_total"] == 0
    assert route["next_stage"] == "Stage 8.26"

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Current repository state: `Stage 8.31 PASS`" in combined
    assert "Stage 8.25   literature-aligned LLM role redesign" in combined
    assert "branch_collapse_to_best_reward_select" in combined
    assert "ownership-aware strategy DSL" in combined
    assert "Stage 8.26" in combined
    assert "not a final objective-value performance claim" in combined
    assert "not a SOTA claim" in combined
