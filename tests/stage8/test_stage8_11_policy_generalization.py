import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage8_11_policy_generalization.yaml"
STAGE8_10_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_10"
STAGE8_3_DECISION = (
    ROOT
    / "artifacts"
    / "selection_audit"
    / "stage8_3"
    / "objective_utility_selection_decision.json"
)
SELECTED_OPERATOR = ROOT / "artifacts" / "selected" / "stage5_1" / "selected_operator.json"
SELECTED_AST = ROOT / "artifacts" / "selected" / "stage5_1" / "selected_operator_ast.json"
STAGE8_7_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_7"
STAGE8_7_POLICY_REPORT = STAGE8_7_DIR / "conditional_policy_report.json"
STAGE8_7_CASE_POLICY = STAGE8_7_DIR / "case_policy_table.jsonl"
OUTPUT_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_11"
OBJECTIVE_TRACE = OUTPUT_DIR / "objective_trace.jsonl"
METHOD_SUMMARY = OUTPUT_DIR / "method_summary.json"
PANEL_SUMMARY = OUTPUT_DIR / "panel_summary.json"
WIN_LOSS_REPORT = OUTPUT_DIR / "win_loss_report.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
ROUTE = OUTPUT_DIR / "next_route_decision.json"
PANEL_REPORT = OUTPUT_DIR / "panel_report.json"
POLICY_RUNTIME_REPORT = OUTPUT_DIR / "generalized_policy_runtime_report.json"
STAGE_DOC = ROOT / "docs" / "stage8" / "stage8_11_policy_generalization.md"
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_11_self_check_report.md"
README = ROOT / "README.md"


def test_stage8_11_generalized_policy_beats_best_simple_baseline(tmp_path) -> None:
    from loco.coordination.policy_generalization_objective_rerun import (
        run_stage8_11_policy_generalization,
    )

    report = run_stage8_11_policy_generalization(
        stage8_10_route_decision_path=STAGE8_10_DIR / "route_decision.json",
        stage8_10_requirements_path=STAGE8_10_DIR / "policy_generalization_requirements.json",
        stage8_3_selection_decision_path=STAGE8_3_DECISION,
        frozen_stage5_operator_path=SELECTED_OPERATOR,
        frozen_stage5_ast_path=SELECTED_AST,
        stage8_7_policy_report_path=STAGE8_7_POLICY_REPORT,
        stage8_7_case_policy_path=STAGE8_7_CASE_POLICY,
        output_dir=tmp_path,
    )

    assert report["stage"] == "8.11"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "8.10"
    assert report["policy_name"] == "regime_safe_adaptive_shrinkage_v1"
    assert report["policy_scope"] == "policy_generalization_beyond_best_simple_baseline"
    assert report["objective_loop_executed"] is True
    assert report["new_objective_evaluation_used"] is True
    assert report["best_baseline_beaten"] is True
    assert report["conditional_vs_best_baseline"] == {"win": 27, "tie": 9, "loss": 0}
    assert report["conditional_vs_stage8_3_selected_operator"] == {
        "win": 18,
        "tie": 18,
        "loss": 0,
    }
    assert report["conditional_vs_weighted_consensus"] == {"win": 18, "tie": 18, "loss": 0}
    assert report["conditional_vs_simple_consensus"] == {"win": 27, "tie": 9, "loss": 0}
    assert report["minimum_vs_best_baseline_win_count"] == 27
    assert report["maximum_vs_best_baseline_loss_count"] == 0
    assert report["objective_loop_executed"] is True
    assert report["new_objective_evaluation_used"] is True
    assert report["FE_total"] == 1512
    assert report["inherited_stage8_10_FE_total"] == 0
    assert report["policy_generalization_required"] is True
    assert report["official_like_panel_ready"] == "now_candidate"
    assert report["recommended_next_stage"] == "Stage 8.12"
    assert report["recommended_next_work"] == "official_like_panel_or_sota_facing_protocol"
    assert report["sota_claim_ready"] is False
    assert report["official_benchmark_claim_ready"] is False
    assert report["final_performance_claim_ready"] is False

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

    policy_runtime = json.loads((tmp_path / "generalized_policy_runtime_report.json").read_text())
    win_loss = json.loads((tmp_path / "win_loss_report.json").read_text())
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())

    assert policy_runtime["policy_name"] == "regime_safe_adaptive_shrinkage_v1"
    assert policy_runtime["policy_generalization_not_equivalent_to_weighted_consensus"] is True
    assert policy_runtime["weighted_safety_trace_row_count"] > 0
    assert policy_runtime["simple_safety_trace_row_count"] > 0
    assert policy_runtime["minabs_shrinkage_trace_row_count"] > 0
    assert win_loss["conditional_vs_best_baseline"] == {"win": 27, "tie": 9, "loss": 0}
    assert win_loss["best_baseline_mean_final_best"] > win_loss["conditional_policy_mean_final_best"]
    assert ledger["FE_total"] == 1512
    assert ledger["objective_loop_executed"] is True
    assert boundary["objective_loop_executed"] is True
    assert boundary["new_objective_evaluation_used"] is True
    assert route["decision"] == "READY_FOR_STAGE8_12_OFFICIAL_LIKE_PANEL"
    assert route["next_stage"] == "Stage 8.12"


def test_stage8_11_committed_artifacts_docs_and_readme_record_policy_generalization() -> None:
    required = [
        CONFIG,
        OBJECTIVE_TRACE,
        METHOD_SUMMARY,
        PANEL_SUMMARY,
        WIN_LOSS_REPORT,
        FE_LEDGER,
        RUNTIME_BOUNDARY,
        ROUTE,
        PANEL_REPORT,
        POLICY_RUNTIME_REPORT,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(PANEL_REPORT.read_text(encoding="utf-8"))
    win_loss = json.loads(WIN_LOSS_REPORT.read_text(encoding="utf-8"))
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))
    route = json.loads(ROUTE.read_text(encoding="utf-8"))

    assert report["stage"] == "8.11"
    assert report["status"] == "PASS"
    assert win_loss["conditional_vs_best_baseline"] == {"win": 27, "tie": 9, "loss": 0}
    assert ledger["FE_total"] == 1512
    assert route["next_stage"] == "Stage 8.12"

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Current repository state: `Stage 8.32 PASS`" in combined
    assert "Stage 8.11   policy generalization beyond best simple baseline          PASS" in combined
    assert "Stage 8.12   official-like / SOTA-facing evidence gate               PASS" in combined
    assert "regime_safe_adaptive_shrinkage_v1" in combined
    assert "27 win / 9 tie / 0 loss" in combined
    assert "FE_total = 1512" in combined
    assert "not a final objective-value performance claim" in combined
    assert "not a SOTA claim" in combined
