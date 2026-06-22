import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = (
    ROOT / "configs" / "stage8_10_official_like_policy_generalization_decision.yaml"
)
STAGE8_9_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_9"
STAGE7_5_DIR = ROOT / "artifacts" / "objective_eval" / "stage7_5"
STAGE7_6_DIR = ROOT / "artifacts" / "objective_eval" / "stage7_6"
OUTPUT_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_10"
SOTA_GAP = OUTPUT_DIR / "sota_gap_report.json"
ROUTE_DECISION = OUTPUT_DIR / "route_decision.json"
POLICY_REQUIREMENTS = OUTPUT_DIR / "policy_generalization_requirements.json"
OFFICIAL_READINESS = OUTPUT_DIR / "official_like_panel_readiness.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
NEXT_ROUTE = OUTPUT_DIR / "next_route_decision.json"
STAGE_DOC = (
    ROOT
    / "docs"
    / "stage8"
    / "stage8_10_official_like_policy_generalization_decision.md"
)
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_10_self_check_report.md"
README = ROOT / "README.md"


def test_stage8_10_prioritizes_policy_generalization_without_new_objective_work(
    tmp_path,
) -> None:
    from loco.coordination.official_like_policy_generalization_decision import (
        run_stage8_10_official_like_policy_generalization_decision,
    )

    report = run_stage8_10_official_like_policy_generalization_decision(
        stage8_9_interpretation_path=STAGE8_9_DIR / "interpretation_report.json",
        stage8_9_claim_boundary_path=STAGE8_9_DIR / "claim_boundary_report.json",
        stage8_9_readiness_path=STAGE8_9_DIR / "paper_claim_readiness_report.json",
        stage8_9_fe_ledger_path=STAGE8_9_DIR / "fe_ledger.json",
        stage8_9_runtime_boundary_path=STAGE8_9_DIR / "runtime_boundary.json",
        stage7_5_sota_protocol_path=STAGE7_5_DIR / "sota_protocol_report.json",
        stage7_5_claim_contract_path=STAGE7_5_DIR / "benchmark_claim_contract.json",
        stage7_6_comparator_audit_path=STAGE7_6_DIR
        / "reported_results_comparator_audit_report.json",
        output_dir=tmp_path,
    )

    assert report["stage"] == "8.10"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "8.9"
    assert report["decision_scope"] == "official_like_panel_or_policy_generalization"
    assert (
        report["decision"]
        == "PRIORITIZE_POLICY_GENERALIZATION_BEFORE_OFFICIAL_SOTA_CLAIM"
    )
    assert report["decision_reason"] == (
        "Stage 8.9 shows bounded synthetic utility but no win over the best "
        "simple baseline, so official-like evaluation is not the best next "
        "SOTA-targeted move."
    )
    assert report["best_baseline_beaten"] is False
    assert report["conditional_vs_best_baseline"] == {"win": 0, "tie": 36, "loss": 0}
    assert report["simple_preferred_case_recovery_count"] == 12
    assert report["official_like_panel_ready"] == "partial"
    assert report["policy_generalization_required"] is True
    assert report["recommended_next_stage"] == "Stage 8.11"
    assert (
        report["recommended_next_work"]
        == "policy_generalization_beyond_best_simple_baseline"
    )
    assert report["objective_loop_executed"] is False
    assert report["new_objective_evaluation_used"] is False
    assert report["FE_total"] == 0
    assert report["inherited_stage8_9_FE_total"] == 0
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

    sota_gap = json.loads((tmp_path / "sota_gap_report.json").read_text())
    route = json.loads((tmp_path / "route_decision.json").read_text())
    requirements = json.loads(
        (tmp_path / "policy_generalization_requirements.json").read_text()
    )
    readiness = json.loads(
        (tmp_path / "official_like_panel_readiness.json").read_text()
    )
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    next_route = json.loads((tmp_path / "next_route_decision.json").read_text())

    assert sota_gap["stage"] == "8.10"
    assert sota_gap["status"] == "PASS"
    assert sota_gap["current_frontier"] == "matches_best_simple_baseline"
    assert sota_gap["sota_gap"] == "does_not_beat_best_simple_baseline"
    assert sota_gap["reported_results_direct_comparator_count"] == 1
    assert sota_gap["official_run_count"] == 25
    assert sota_gap["official_max_fe"] == 3000000
    assert sota_gap["full_cec2013_sota_claim_allowed_now"] is False

    assert route["decision"] == report["decision"]
    assert route["run_official_like_panel_now"] is False
    assert route["run_policy_generalization_next"] is True
    assert route["next_stage"] == "Stage 8.11"

    assert requirements["stage"] == "8.10"
    assert requirements["minimum_vs_best_baseline_win_count"] == 3
    assert requirements["maximum_vs_best_baseline_loss_count"] == 0
    assert requirements["must_exceed_switching_policy"] is True
    assert requirements["must_not_modify_baseopt"] is True
    assert "adaptive_robust_aggregation" in requirements["required_capabilities"]
    assert "conflict_aware_shrinkage" in requirements["required_capabilities"]
    assert (
        "topology_aware_shared_variable_update" in requirements["required_capabilities"]
    )

    assert readiness["official_like_panel_ready"] == "partial"
    assert readiness["blocking_reason"] == (
        "method has not beaten the best simple baseline on the locked synthetic panel"
    )
    assert readiness["allowed_later_claim_tier"] == "T1_or_T2_only_after_panel"
    assert readiness["full_sota_claim_ready"] is False

    assert ledger["FE_total"] == 0
    assert ledger["inherited_stage8_9_FE_total"] == 0
    assert ledger["objective_loop_executed"] is False
    assert ledger["new_objective_evaluation_used"] is False

    assert boundary["objective_loop_executed"] is False
    assert boundary["new_objective_evaluation_used"] is False
    assert boundary["forbidden_behaviors"]["llm_call"] is False
    assert boundary["forbidden_behaviors"]["test_feedback"] is False
    assert boundary["not_sota_claim"] is True

    assert next_route["decision"] == "READY_FOR_STAGE8_11_POLICY_GENERALIZATION"
    assert next_route["next_stage"] == "Stage 8.11"
    assert (
        next_route["allowed_next_work"]
        == "policy_generalization_beyond_best_simple_baseline"
    )


def test_stage8_10_committed_artifacts_docs_and_readme_record_route_decision() -> None:
    required = [
        CONFIG,
        SOTA_GAP,
        ROUTE_DECISION,
        POLICY_REQUIREMENTS,
        OFFICIAL_READINESS,
        FE_LEDGER,
        RUNTIME_BOUNDARY,
        NEXT_ROUTE,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(ROUTE_DECISION.read_text(encoding="utf-8"))
    gap = json.loads(SOTA_GAP.read_text(encoding="utf-8"))
    requirements = json.loads(POLICY_REQUIREMENTS.read_text(encoding="utf-8"))
    readiness = json.loads(OFFICIAL_READINESS.read_text(encoding="utf-8"))
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))

    assert report["stage"] == "8.10"
    assert report["status"] == "PASS"
    assert report["decision"] == (
        "PRIORITIZE_POLICY_GENERALIZATION_BEFORE_OFFICIAL_SOTA_CLAIM"
    )
    assert gap["sota_gap"] == "does_not_beat_best_simple_baseline"
    assert requirements["minimum_vs_best_baseline_win_count"] == 3
    assert readiness["full_sota_claim_ready"] is False
    assert ledger["FE_total"] == 0

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Current repository state: `Stage 8.14 PASS`" in combined
    assert (
        "Stage 8.10   official-like panel or policy-generalization decision      PASS"
        in combined
    )
    assert (
        "Stage 8.11   policy generalization beyond best simple baseline          PASS"
        in combined
    )
    assert "PRIORITIZE_POLICY_GENERALIZATION_BEFORE_OFFICIAL_SOTA_CLAIM" in combined
    assert "policy generalization beyond best simple baseline" in combined
    assert "official_like_panel_ready = partial" in combined
    assert "best_baseline_beaten = false" in combined
    assert "FE_total = 0" in combined
    assert "not a final objective-value performance claim" in combined
    assert "not a SOTA claim" in combined
