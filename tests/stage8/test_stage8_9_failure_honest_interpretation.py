import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage8_9_failure_honest_interpretation.yaml"
STAGE8_8_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_8"
STAGE8_8_PANEL_REPORT = STAGE8_8_DIR / "panel_report.json"
STAGE8_8_WIN_LOSS = STAGE8_8_DIR / "win_loss_report.json"
STAGE8_8_POLICY_RUNTIME = STAGE8_8_DIR / "conditional_policy_runtime_report.json"
STAGE8_8_FE_LEDGER = STAGE8_8_DIR / "fe_ledger.json"
STAGE8_8_RUNTIME_BOUNDARY = STAGE8_8_DIR / "runtime_boundary.json"
OUTPUT_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_9"
INTERPRETATION_REPORT = OUTPUT_DIR / "interpretation_report.json"
CLAIM_BOUNDARY = OUTPUT_DIR / "claim_boundary_report.json"
PAPER_READINESS = OUTPUT_DIR / "paper_claim_readiness_report.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
ROUTE = OUTPUT_DIR / "next_route_decision.json"
STAGE_DOC = ROOT / "docs" / "stage8" / "stage8_9_failure_honest_interpretation.md"
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_9_self_check_report.md"
README = ROOT / "README.md"


EXPECTED_STAGE8_8_WIN_LOSS = {
    "conditional_vs_stage8_3_selected_operator": {"win": 12, "tie": 24, "loss": 0},
    "conditional_vs_weighted_consensus": {"win": 12, "tie": 24, "loss": 0},
    "conditional_vs_simple_consensus": {"win": 24, "tie": 12, "loss": 0},
    "conditional_vs_best_baseline": {"win": 0, "tie": 36, "loss": 0},
}


def test_stage8_9_interprets_stage8_8_without_new_objective_work(tmp_path) -> None:
    from loco.coordination.failure_honest_interpretation import (
        run_stage8_9_failure_honest_interpretation,
    )

    report = run_stage8_9_failure_honest_interpretation(
        stage8_8_panel_report_path=STAGE8_8_PANEL_REPORT,
        stage8_8_win_loss_path=STAGE8_8_WIN_LOSS,
        stage8_8_policy_runtime_path=STAGE8_8_POLICY_RUNTIME,
        stage8_8_fe_ledger_path=STAGE8_8_FE_LEDGER,
        stage8_8_runtime_boundary_path=STAGE8_8_RUNTIME_BOUNDARY,
        output_dir=tmp_path,
    )

    assert report["stage"] == "8.9"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "8.8"
    assert report["interpretation_scope"] == "failure_honest_stage8_8_interpretation"
    assert report["stage8_8_result_interpreted"] is True
    assert report["positive_claim_is_bounded"] is True
    assert report["negative_boundary_is_explicit"] is True
    assert report["best_baseline_not_beaten_is_recorded"] is True
    assert report["conditional_policy_utility_is_recorded"] is True
    assert report["objective_loop_executed"] is False
    assert report["new_objective_evaluation_used"] is False
    assert report["FE_total"] == 0
    assert report["inherited_stage8_8_FE_total"] == 1512
    assert report["conditional_policy_name"] == "overlap_reward_reliability_switch_v1"
    assert report["method_name"] == "stage8_7_conditional_policy"
    assert report["primary_positive_claim"] == (
        "conditional proposal-state coordination fixes weighted-consensus collapse "
        "and recovers simple-preferred overlap regimes in objective-loop execution"
    )
    assert report["primary_negative_boundary"] == (
        "conditional policy matches but does not beat the best simple baseline; "
        "not final performance and not SOTA"
    )
    assert report["research_meaning"] == (
        "the useful object is an overlap/reward-reliability aware coordination "
        "policy over operator families, not another weighted-consensus clone"
    )

    for key, expected in EXPECTED_STAGE8_8_WIN_LOSS.items():
        assert report[key] == expected
    assert report["simple_preferred_case_recovery_count"] == 12
    assert report["weighted_sufficient_case_regression_count"] == 0

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

    claim_boundary = json.loads((tmp_path / "claim_boundary_report.json").read_text())
    readiness = json.loads((tmp_path / "paper_claim_readiness_report.json").read_text())
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())

    assert claim_boundary["stage"] == "8.9"
    assert claim_boundary["status"] == "PASS"
    assert claim_boundary["positive_claim_allowed"] is True
    assert claim_boundary["official_benchmark_claim_allowed"] is False
    assert claim_boundary["sota_claim_allowed"] is False
    assert claim_boundary["final_performance_claim_allowed"] is False
    assert (
        claim_boundary["blocked_claim_reason"]
        == "conditional policy ties but does not beat the best simple baseline"
    )

    assert readiness["method_claim_ready"] is True
    assert readiness["synthetic_panel_claim_ready"] is True
    assert readiness["paper_experiment_paragraph_ready"] is True
    assert readiness["official_benchmark_claim_ready"] is False
    assert readiness["sota_claim_ready"] is False
    assert readiness["final_performance_claim_ready"] is False

    assert ledger["stage"] == "8.9"
    assert ledger["FE_total"] == 0
    assert ledger["inherited_stage8_8_FE_total"] == 1512
    assert ledger["objective_loop_executed"] is False
    assert ledger["new_objective_evaluation_used"] is False

    assert boundary["stage"] == "8.9"
    assert boundary["objective_loop_executed"] is False
    assert boundary["new_objective_evaluation_used"] is False
    assert boundary["forbidden_behaviors"]["llm_call"] is False
    assert boundary["forbidden_behaviors"]["test_feedback"] is False
    assert boundary["not_sota_claim"] is True
    assert boundary["not_final_performance_claim"] is True

    assert route["stage"] == "8.9"
    assert route["status"] == "PASS"
    assert (
        route["decision"]
        == "READY_FOR_STAGE8_10_OFFICIAL_LIKE_PANEL_OR_POLICY_GENERALIZATION_DECISION"
    )
    assert route["next_stage"] == "Stage 8.10"
    assert (
        route["allowed_next_work"]
        == "official_like_panel_or_policy_generalization_decision"
    )
    assert route["use_validation_feedback"] is False
    assert route["use_test_feedback"] is False


def test_stage8_9_committed_artifacts_docs_and_readme_record_claim_boundary() -> None:
    required = [
        CONFIG,
        INTERPRETATION_REPORT,
        CLAIM_BOUNDARY,
        PAPER_READINESS,
        FE_LEDGER,
        RUNTIME_BOUNDARY,
        ROUTE,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(INTERPRETATION_REPORT.read_text(encoding="utf-8"))
    claim_boundary = json.loads(CLAIM_BOUNDARY.read_text(encoding="utf-8"))
    readiness = json.loads(PAPER_READINESS.read_text(encoding="utf-8"))
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))
    route = json.loads(ROUTE.read_text(encoding="utf-8"))

    assert report["stage"] == "8.9"
    assert report["status"] == "PASS"
    assert report["conditional_vs_best_baseline"] == {"win": 0, "tie": 36, "loss": 0}
    assert report["best_baseline_not_beaten_is_recorded"] is True
    assert claim_boundary["final_performance_claim_allowed"] is False
    assert readiness["official_benchmark_claim_ready"] is False
    assert ledger["FE_total"] == 0
    assert ledger["inherited_stage8_8_FE_total"] == 1512
    assert route["next_stage"] == "Stage 8.10"

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Current repository state: `Stage 8.22 PASS`" in combined
    assert (
        "Stage 8.9    failure-honest interpretation before official claims      PASS"
        in combined
    )
    assert (
        "Stage 8.10   official-like panel or policy-generalization decision      PASS"
        in combined
    )
    assert (
        "conditional policy matches but does not beat the best simple baseline"
        in combined
    )
    assert "not a final objective-value performance claim" in combined
    assert "not a SOTA claim" in combined
    assert "FE_total = 0" in combined
    assert "inherited_stage8_8_FE_total = 1512" in combined
