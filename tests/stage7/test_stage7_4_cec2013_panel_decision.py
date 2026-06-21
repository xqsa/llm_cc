import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage7_4_cec2013_panel_decision.yaml"
SOURCE_REPORT = (
    ROOT / "artifacts" / "objective_eval" / "stage7_3" / "paper_tables_report.json"
)
SOURCE_RANKING = (
    ROOT / "artifacts" / "objective_eval" / "stage7_3" / "method_ranking.json"
)
SOURCE_BOUNDARY = (
    ROOT / "artifacts" / "objective_eval" / "stage7_3" / "claim_boundary.json"
)
METABOX_SMOKE = ROOT / "docs" / "stage1" / "metabox_real_smoke_latest.json"
OUTPUT_DIR = ROOT / "artifacts" / "objective_eval" / "stage7_4"
DECISION = OUTPUT_DIR / "cec2013_panel_decision.json"
PROTOCOL = OUTPUT_DIR / "cec2013_optional_panel_protocol.json"
READINESS = OUTPUT_DIR / "cec2013_readiness_summary.json"
CLAIM_BOUNDARY = OUTPUT_DIR / "claim_boundary.json"
DECISION_REPORT = OUTPUT_DIR / "decision_report.json"
STAGE_DOC = ROOT / "docs" / "stage7" / "stage7_4_cec2013_panel_decision.md"
SELF_CHECK = ROOT / "docs" / "stage7" / "stage7_4_self_check_report.md"
README = ROOT / "README.md"


def test_stage7_4_decides_optional_cec2013_panel_without_running_it(tmp_path) -> None:
    from loco.coordination.cec2013_panel_decision import (
        run_stage7_4_cec2013_panel_decision,
    )

    report = run_stage7_4_cec2013_panel_decision(
        stage7_3_report_path=SOURCE_REPORT,
        stage7_3_ranking_path=SOURCE_RANKING,
        stage7_3_claim_boundary_path=SOURCE_BOUNDARY,
        metabox_smoke_path=METABOX_SMOKE,
        output_dir=tmp_path,
    )

    assert report["stage"] == "7.4"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "7.3"
    assert (
        report["decision_scope"] == "optional_cec2013_f13_f14_objective_panel_decision"
    )
    assert report["decision"] == "RUN_OPTIONAL_CEC2013_F13_F14_PANEL"
    assert (
        report["decision_reason"]
        == "stage7_3_mixed_synthetic_evidence_needs_real_overlap_panel"
    )
    assert report["cec2013_panel_run"] is False
    assert report["new_objective_evaluation_used"] is False
    assert report["selected_operator_revision_used"] is False
    assert (
        report["next_status"]
        == "READY_FOR_STAGE7_5_OPTIONAL_CEC2013_PANEL_PROTOCOL_OR_PAPER_DRAFT"
    )

    decision = json.loads((tmp_path / "cec2013_panel_decision.json").read_text())
    protocol = json.loads(
        (tmp_path / "cec2013_optional_panel_protocol.json").read_text()
    )
    readiness = json.loads((tmp_path / "cec2013_readiness_summary.json").read_text())
    boundary = json.loads((tmp_path / "claim_boundary.json").read_text())

    assert decision["stage"] == "7.4"
    assert decision["status"] == "PASS"
    assert decision["decision"] == "RUN_OPTIONAL_CEC2013_F13_F14_PANEL"
    assert decision["selected_loco_operator_rank_overall"] == 4
    assert decision["best_overall_method"] == "simple_consensus"
    assert decision["requires_real_overlap_panel"] is True
    assert decision["paper_draft_without_cec2013_allowed"] is True
    assert decision["not_final_performance_claim"] is True

    assert protocol["stage"] == "7.4"
    assert protocol["status"] == "PREPARED_NOT_EXECUTED"
    assert protocol["target_functions"] == ["F13", "F14"]
    assert (
        protocol["function_semantics"]["F13"]["overlap_semantics"]
        == "conforming_overlap"
    )
    assert protocol["function_semantics"]["F13"]["D_formula"] == 905
    assert protocol["function_semantics"]["F13"]["D_api"] == 1000
    assert (
        protocol["function_semantics"]["F13"]["adapter_mode"]
        == "implementation_api_adapter"
    )
    assert (
        protocol["function_semantics"]["F14"]["overlap_semantics"]
        == "conflicting_overlap"
    )
    assert protocol["function_semantics"]["F14"]["D_formula"] == 905
    assert protocol["function_semantics"]["F14"]["D_api"] == 1000
    assert (
        protocol["function_semantics"]["F14"]["adapter_mode"]
        == "direct_metabox_dimension"
    )
    assert protocol["locked_methods"] == [
        "identity_no_coord",
        "simple_consensus",
        "weighted_consensus",
        "best_reward_select",
        "selected_loco_operator",
    ]
    assert protocol["same_budget_across_methods"] is True
    assert protocol["all_extra_fe_counted"] is True
    assert protocol["oracle_and_detected_grouping_reported_separately"] is True
    assert protocol["selected_operator_policy"] == "frozen_no_revision"
    assert protocol["execution_status"] == "NOT_RUN_IN_STAGE7_4"

    assert readiness["stage"] == "7.4"
    assert readiness["metabox_smoke_status"] == "PASS"
    assert readiness["f13_ready"] is True
    assert readiness["f14_ready"] is True
    assert readiness["f13_shared_variable_count"] == 95
    assert readiness["f14_shared_variable_count"] == 95
    assert readiness["overlap_ratio"] == 95 / 905

    assert boundary["stage"] == "7.4"
    assert boundary["status"] == "PASS"
    assert "official CEC2013 performance claim" in boundary["forbidden_claims"]
    assert "SOTA improvement" in boundary["forbidden_claims"]
    assert boundary["cec2013_panel_run"] is False
    assert boundary["new_objective_evaluation_used"] is False
    assert boundary["not_final_performance_claim"] is True


def test_stage7_4_committed_artifacts_docs_and_readme_record_decision() -> None:
    required = [
        CONFIG,
        DECISION,
        PROTOCOL,
        READINESS,
        CLAIM_BOUNDARY,
        DECISION_REPORT,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    readiness = json.loads(READINESS.read_text(encoding="utf-8"))
    boundary = json.loads(CLAIM_BOUNDARY.read_text(encoding="utf-8"))
    report = json.loads(DECISION_REPORT.read_text(encoding="utf-8"))

    assert report["status"] == "PASS"
    assert report["stage"] == "7.4"
    assert decision["decision"] == "RUN_OPTIONAL_CEC2013_F13_F14_PANEL"
    assert protocol["execution_status"] == "NOT_RUN_IN_STAGE7_4"
    assert readiness["metabox_smoke_status"] == "PASS"
    assert boundary["cec2013_panel_run"] is False

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Current repository state: `Stage 7.4 PASS`" in combined
    assert (
        "Stage 7.4    optional CEC2013 F13/F14 objective panel decision      PASS"
        in combined
    )
    assert "Stage 7.5" in combined
    assert "RUN_OPTIONAL_CEC2013_F13_F14_PANEL" in combined
    assert "cec2013_optional_panel_protocol.json" in combined
    assert "F13" in combined
    assert "F14" in combined
    assert "D_formula = 905" in combined
    assert "shared_variable_count = 95" in combined
    assert "not run in Stage 7.4" in combined
    assert "no new objective evaluation" in combined
    assert "not a final objective-value performance claim" in combined
