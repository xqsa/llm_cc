import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage8_12_official_like_sota_panel.yaml"
STAGE8_11_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_11"
STAGE7_5_DIR = ROOT / "artifacts" / "objective_eval" / "stage7_5"
STAGE7_6_DIR = ROOT / "artifacts" / "objective_eval" / "stage7_6"
OUTPUT_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_12"
OFFICIAL_LIKE_PANEL_REPORT = OUTPUT_DIR / "official_like_panel_report.json"
SOTA_GAP_REPORT = OUTPUT_DIR / "sota_gap_report.json"
STRONG_BASELINE_REPORT = OUTPUT_DIR / "strong_baseline_report.json"
SAME_BUDGET_REPORT = OUTPUT_DIR / "same_budget_report.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
NEXT_ROUTE = OUTPUT_DIR / "next_route_decision.json"
STAGE_DOC = ROOT / "docs" / "stage8" / "stage8_12_official_like_sota_panel.md"
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_12_self_check_report.md"
README = ROOT / "README.md"


def test_stage8_12_converts_stage8_11_into_sota_facing_evidence(tmp_path) -> None:
    from loco.coordination.official_like_sota_panel import (
        run_stage8_12_official_like_sota_panel,
    )

    report = run_stage8_12_official_like_sota_panel(
        stage8_11_panel_report_path=STAGE8_11_DIR / "panel_report.json",
        stage8_11_win_loss_path=STAGE8_11_DIR / "win_loss_report.json",
        stage8_11_method_summary_path=STAGE8_11_DIR / "method_summary.json",
        stage8_11_panel_summary_path=STAGE8_11_DIR / "panel_summary.json",
        stage8_11_fe_ledger_path=STAGE8_11_DIR / "fe_ledger.json",
        stage8_11_runtime_boundary_path=STAGE8_11_DIR / "runtime_boundary.json",
        stage8_11_next_route_path=STAGE8_11_DIR / "next_route_decision.json",
        stage7_5_sota_protocol_path=STAGE7_5_DIR / "sota_protocol_report.json",
        stage7_5_claim_contract_path=STAGE7_5_DIR / "benchmark_claim_contract.json",
        stage7_6_comparator_audit_path=STAGE7_6_DIR
        / "reported_results_comparator_audit_report.json",
        stage7_6_comparator_registry_path=STAGE7_6_DIR
        / "reported_results_comparator_registry.json",
        output_dir=tmp_path,
    )

    assert report["stage"] == "8.12"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "8.11"
    assert report["panel_scope"] == "official_like_sota_facing_panel"
    assert report["policy_name"] == "regime_safe_adaptive_shrinkage_v1"
    assert report["stage8_11_policy_executed"] is True
    assert report["official_like_panel_executed"] is True
    assert report["same_budget_comparison"] is True
    assert report["strong_baseline_comparison"] is True
    assert report["reported_results_direct_comparator_count"] == 1
    assert report["reported_results_used_as_runtime_feedback"] is False
    assert report["same_setting_comparator_contract_locked"] is True
    assert report["official_run_count_required"] == 25
    assert report["official_max_fe_required"] == 3000000
    assert report["official_function_count_required"] == 15
    assert report["synthetic_case_count"] == 36
    assert report["comparison_case_count"] == 36
    assert report["strong_baseline_count"] >= 4
    assert report["conditional_vs_best_baseline"] == {"win": 27, "tie": 9, "loss": 0}
    assert report["best_baseline_beaten"] is True
    assert report["best_baseline_loss_count"] == 0
    assert report["minimum_vs_best_baseline_win_count"] == 27
    assert report["mean_relative_gap_vs_best_baseline"] < 0
    assert report["sota_gap_report_written"] is True
    assert report["decision"] == "READY_FOR_STAGE8_13_FORMAL_SOTA_EXPERIMENT_DESIGN"
    assert report["recommended_next_stage"] == "Stage 8.13"
    assert (
        report["recommended_next_work"]
        == "formal_cec2013_sota_experiment_design_and_budget_lock"
    )
    assert report["sota_claim_ready"] is False
    assert report["official_benchmark_claim_ready"] is False
    assert report["final_performance_claim_ready"] is False
    assert report["not_sota_claim"] is True
    assert report["not_final_performance_claim"] is True

    for flag in [
        "llm_call_used",
        "new_candidate_generation_used",
        "selected_operator_revision_used",
        "evolution_search_used",
        "validation_feedback_used",
        "test_feedback_used",
        "baseopt_modified",
        "optimizer_generation_used",
        "controller_scheduler_generation_used",
    ]:
        assert report[flag] is False

    gap = json.loads((tmp_path / "sota_gap_report.json").read_text())
    strong = json.loads((tmp_path / "strong_baseline_report.json").read_text())
    budget = json.loads((tmp_path / "same_budget_report.json").read_text())
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())

    assert gap["stage"] == "8.12"
    assert gap["current_frontier"] == "beats_best_simple_baseline_on_locked_synthetic_panel"
    assert gap["formal_sota_gap"] == "official_cec2013_same_budget_panel_not_yet_run"
    assert gap["full_cec2013_sota_claim_allowed_now"] is False
    assert gap["ready_for_formal_sota_experiment_design"] is True
    assert gap["claim_tier_recommended"] == "T1_then_T2_or_T3_after_official_runs"

    assert strong["stage"] == "8.12"
    assert strong["strong_baseline_methods"] == [
        "identity_no_coord",
        "simple_consensus",
        "weighted_consensus",
        "best_reward_select",
        "frozen_stage5_selected_operator",
        "stage8_3_selected_operator",
    ]
    assert strong["stage8_11_generalized_policy_rank"] == 1
    assert strong["strictly_beats_best_simple_baseline"] is True
    assert strong["zero_losses_vs_best_baseline"] is True

    assert budget["same_budget_across_methods"] is True
    assert budget["stage8_11_FE_total"] == 1512
    assert budget["stage8_12_FE_total"] == 0
    assert budget["inherited_objective_evidence_FE_total"] == 1512
    assert budget["official_budget_match_ready"] is False
    assert budget["official_budget_match_next_stage_required"] is True

    assert ledger["FE_total"] == 0
    assert ledger["inherited_stage8_11_FE_total"] == 1512
    assert ledger["new_objective_evaluation_used"] is False
    assert boundary["objective_loop_executed"] is False
    assert boundary["official_cec2013_panel_run"] is False
    assert boundary["not_sota_claim"] is True
    assert route["next_stage"] == "Stage 8.13"
    assert route["run_formal_sota_experiment_design_next"] is True


def test_stage8_12_committed_artifacts_docs_and_readme_record_sota_facing_gate() -> None:
    required = [
        CONFIG,
        OFFICIAL_LIKE_PANEL_REPORT,
        SOTA_GAP_REPORT,
        STRONG_BASELINE_REPORT,
        SAME_BUDGET_REPORT,
        FE_LEDGER,
        RUNTIME_BOUNDARY,
        NEXT_ROUTE,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(OFFICIAL_LIKE_PANEL_REPORT.read_text(encoding="utf-8"))
    gap = json.loads(SOTA_GAP_REPORT.read_text(encoding="utf-8"))
    strong = json.loads(STRONG_BASELINE_REPORT.read_text(encoding="utf-8"))
    budget = json.loads(SAME_BUDGET_REPORT.read_text(encoding="utf-8"))
    route = json.loads(NEXT_ROUTE.read_text(encoding="utf-8"))

    assert report["stage"] == "8.12"
    assert report["status"] == "PASS"
    assert report["official_like_panel_executed"] is True
    assert report["same_budget_comparison"] is True
    assert report["strong_baseline_comparison"] is True
    assert gap["ready_for_formal_sota_experiment_design"] is True
    assert strong["stage8_11_generalized_policy_rank"] == 1
    assert budget["stage8_12_FE_total"] == 0
    assert route["next_stage"] == "Stage 8.13"

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Current repository state: `Stage 8.17 PASS`" in combined
    assert "Stage 8.11   policy generalization beyond best simple baseline          PASS" in combined
    assert "Stage 8.12   official-like / SOTA-facing evidence gate               PASS" in combined
    assert "Stage 8.13   formal CEC2013 SOTA experiment design and budget lock    PASS" in combined
    assert "regime_safe_adaptive_shrinkage_v1" in combined
    assert "27 win / 9 tie / 0 loss" in combined
    assert "official_cec2013_same_budget_panel_not_yet_run" in combined
    assert "not a final objective-value performance claim" in combined
    assert "not a SOTA claim" in combined
