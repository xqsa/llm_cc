import json
from pathlib import Path


ROOT = Path("E:/llm_cc")
CONFIG = ROOT / "configs" / "stage8_15_cec2013_smoke_failure_diagnosis.yaml"
STAGE8_14_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_14"
OUTPUT_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_15"
DIAGNOSIS_REPORT = OUTPUT_DIR / "diagnosis_report.json"
METHOD_GAP = OUTPUT_DIR / "method_gap_report.json"
BRANCH_DIAGNOSTICS = OUTPUT_DIR / "branch_diagnostics.json"
ROOT_CAUSE = OUTPUT_DIR / "root_cause_hypotheses.json"
CLAIM_BOUNDARY = OUTPUT_DIR / "claim_boundary_report.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
NEXT_ROUTE = OUTPUT_DIR / "next_route_decision.json"
STAGE_DOC = ROOT / "docs" / "stage8" / "stage8_15_cec2013_smoke_failure_diagnosis.md"
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_15_self_check_report.md"
README = ROOT / "README.md"


def test_stage8_15_diagnoses_cec2013_smoke_failure_without_new_objective_work(tmp_path) -> None:
    from loco.coordination.cec2013_smoke_failure_diagnosis import (
        run_stage8_15_cec2013_smoke_failure_diagnosis,
    )

    report = run_stage8_15_cec2013_smoke_failure_diagnosis(
        stage8_14_smoke_report_path=STAGE8_14_DIR / "single_run_smoke_report.json",
        stage8_14_win_loss_path=STAGE8_14_DIR / "win_loss_report.json",
        stage8_14_method_summary_path=STAGE8_14_DIR / "method_summary.json",
        stage8_14_objective_trace_path=STAGE8_14_DIR / "objective_trace.jsonl",
        stage8_14_fe_ledger_path=STAGE8_14_DIR / "fe_ledger.json",
        stage8_14_runtime_boundary_path=STAGE8_14_DIR / "runtime_boundary.json",
        stage8_14_next_route_path=STAGE8_14_DIR / "next_route_decision.json",
        output_dir=tmp_path,
    )

    assert report["stage"] == "8.15"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "8.14"
    assert report["diagnosis_scope"] == "failure_honest_cec2013_smoke_diagnosis"
    assert report["stage8_14_result_interpreted"] is True
    assert report["single_run_promising"] is False
    assert report["policy_vs_best_baseline"] == {"win": 0, "tie": 0, "loss": 2}
    assert report["best_baseline_method_count"] == {"best_reward_select": 2}
    assert report["dominant_failure_mode"] == "best_reward_select_alignment_gap"
    assert report["primary_diagnosis"] == (
        "CEC2013 F13/F14 smoke favors direct best-reward proposal selection; "
        "the generalized policy branches to simple/weighted/zero-anchor safety "
        "instead of exploiting the best-reward proposal."
    )
    assert report["f13_policy_equivalent_to_simple_consensus"] is True
    assert report["f14_policy_equivalent_to_weighted_consensus"] is True
    assert report["full_25_run_panel_blocked"] is True
    assert report["policy_revision_allowed"] is False
    assert report["objective_loop_executed"] is False
    assert report["new_objective_evaluation_used"] is False
    assert report["FE_total"] == 0
    assert report["inherited_stage8_14_FE_total"] == 24010
    assert report["recommended_next_stage"] == "Stage 8.16"
    assert report["recommended_next_work"] == "train_side_proposal_policy_alignment_repair"

    for flag in [
        "llm_call_used",
        "new_candidate_generation_used",
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

    method_gap = json.loads((tmp_path / "method_gap_report.json").read_text())
    branch = json.loads((tmp_path / "branch_diagnostics.json").read_text())
    root_cause = json.loads((tmp_path / "root_cause_hypotheses.json").read_text())
    claim = json.loads((tmp_path / "claim_boundary_report.json").read_text())
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())

    assert method_gap["stage"] == "8.15"
    assert method_gap["case_count"] == 2
    assert method_gap["loss_count"] == 2
    assert method_gap["best_baseline_method_count"] == {"best_reward_select": 2}
    assert len(method_gap["case_rows"]) == 2
    assert all(row["policy_vs_best_baseline_result"] == "loss" for row in method_gap["case_rows"])
    assert all(row["relative_gap_vs_best_baseline"] > 0 for row in method_gap["case_rows"])

    assert branch["stage"] == "8.15"
    assert branch["policy_method_name"] == "stage8_11_generalized_policy"
    assert branch["branch_rows_by_function"]["F13"]["dominant_branch"] == "simple_safety"
    assert branch["branch_rows_by_function"]["F13"]["dominant_branch_count"] == 1200
    assert branch["branch_rows_by_function"]["F14"]["dominant_branch"] == "zero_anchor"
    assert branch["branch_rows_by_function"]["F14"]["dominant_branch_count"] == 1198
    assert branch["f13_policy_equivalent_to_simple_consensus"] is True
    assert branch["f14_policy_equivalent_to_weighted_consensus"] is True

    assert root_cause["stage"] == "8.15"
    assert root_cause["top_hypothesis_id"] == "H1_best_reward_alignment_gap"
    assert root_cause["hypothesis_count"] >= 4
    assert root_cause["do_not_run_25_until_diagnosed"] is True
    assert root_cause["policy_revision_from_smoke_forbidden"] is True

    assert claim["official_benchmark_claim_allowed"] is False
    assert claim["sota_claim_allowed"] is False
    assert claim["final_performance_claim_allowed"] is False
    assert claim["allowed_claim"] == (
        "The single-run F13/F14 CEC2013 smoke exposed a best-reward-selection "
        "alignment gap that should be diagnosed before any 25-run panel."
    )

    assert ledger["FE_total"] == 0
    assert ledger["inherited_stage8_14_FE_total"] == 24010
    assert ledger["new_objective_evaluation_used"] is False
    assert boundary["objective_loop_executed"] is False
    assert boundary["forbidden_behaviors"]["selected_operator_revision"] is False
    assert boundary["forbidden_behaviors"]["test_feedback"] is False
    assert route["next_stage"] == "Stage 8.16"
    assert route["run_full_25_run_panel_next"] is False
    assert route["allowed_next_work"] == "train_side_proposal_policy_alignment_repair"


def test_stage8_15_committed_artifacts_docs_and_readme_record_diagnosis() -> None:
    required = [
        CONFIG,
        DIAGNOSIS_REPORT,
        METHOD_GAP,
        BRANCH_DIAGNOSTICS,
        ROOT_CAUSE,
        CLAIM_BOUNDARY,
        FE_LEDGER,
        RUNTIME_BOUNDARY,
        NEXT_ROUTE,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(DIAGNOSIS_REPORT.read_text(encoding="utf-8"))
    method_gap = json.loads(METHOD_GAP.read_text(encoding="utf-8"))
    branch = json.loads(BRANCH_DIAGNOSTICS.read_text(encoding="utf-8"))
    root_cause = json.loads(ROOT_CAUSE.read_text(encoding="utf-8"))
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))
    route = json.loads(NEXT_ROUTE.read_text(encoding="utf-8"))

    assert report["stage"] == "8.15"
    assert report["status"] == "PASS"
    assert report["dominant_failure_mode"] == "best_reward_select_alignment_gap"
    assert method_gap["best_baseline_method_count"] == {"best_reward_select": 2}
    assert branch["f13_policy_equivalent_to_simple_consensus"] is True
    assert branch["f14_policy_equivalent_to_weighted_consensus"] is True
    assert root_cause["top_hypothesis_id"] == "H1_best_reward_alignment_gap"
    assert ledger["FE_total"] == 0
    assert route["next_stage"] == "Stage 8.16"

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Current repository state: `Stage 8.28 PASS`" in combined
    assert "Stage 8.15   failure-honest CEC2013 smoke diagnosis" in combined
    assert "best_reward_select_alignment_gap" in combined
    assert "FE_total = 0" in combined
    assert "inherited_stage8_14_FE_total = 24010" in combined
    assert "not a SOTA claim" in combined
    assert "not a final objective-value performance claim" in combined
