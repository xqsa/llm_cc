import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage8_3_objective_level_utility_selection.yaml"
STAGE8_1_DECISION = (
    ROOT / "artifacts" / "selection_audit" / "stage8_1" / "selection_decision.json"
)
STAGE8_2_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_2"
PILOT_REPORT = STAGE8_2_DIR / "pilot_report.json"
UTILITY_REPORT = STAGE8_2_DIR / "utility_report.json"
UTILITY_TRACE = STAGE8_2_DIR / "utility_trace.jsonl"
STAGE8_2_FE_LEDGER = STAGE8_2_DIR / "fe_ledger.json"
OUTPUT_DIR = ROOT / "artifacts" / "selection_audit" / "stage8_3"
EVIDENCE_TABLE = OUTPUT_DIR / "objective_utility_evidence_table.jsonl"
SELECTION_DECISION = OUTPUT_DIR / "objective_utility_selection_decision.json"
SELECTION_REPORT = OUTPUT_DIR / "objective_utility_selection_report.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
ROUTE = OUTPUT_DIR / "next_route_decision.json"
STAGE_DOC = ROOT / "docs" / "stage8" / "stage8_3_objective_level_utility_selection.md"
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_3_self_check_report.md"
README = ROOT / "README.md"


def test_stage8_3_selects_over_objective_level_utility_evidence(tmp_path) -> None:
    from loco.coordination.objective_level_utility_selection import (
        run_stage8_3_objective_level_utility_selection,
    )

    report = run_stage8_3_objective_level_utility_selection(
        stage8_1_selection_decision_path=STAGE8_1_DECISION,
        stage8_2_pilot_report_path=PILOT_REPORT,
        stage8_2_utility_report_path=UTILITY_REPORT,
        stage8_2_fe_ledger_path=STAGE8_2_FE_LEDGER,
        output_dir=tmp_path,
    )

    assert report["stage"] == "8.3"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "8.2"
    assert report["selection_scope"] == "objective_level_utility_evidence_selection"
    assert report["objective_level_utility_evidence_used"] is True
    assert report["objective_loop_executed"] is False
    assert report["objective_evaluation_used"] is False
    assert report["new_candidate_generation_used"] is False
    assert report["evolution_search_used"] is False
    assert report["validation_feedback_used"] is False
    assert report["test_feedback_used"] is False
    assert report["baseopt_modified"] is False
    assert report["optimizer_generation_used"] is False
    assert report["controller_scheduler_generation_used"] is False
    assert report["not_sota_claim"] is True
    assert report["not_final_performance_claim"] is True
    assert report["selected_candidate_id"] == "stage3_5_batch_1_reweighting_repair"
    assert report["previous_frozen_candidate_id"] == (
        "stage3_5_batch_1_weighted_consensus_projection"
    )
    assert (
        report["selected_candidate_final_best"]
        < report["previous_frozen_candidate_final_best"]
    )
    assert report["objective_utility_delta_vs_previous_frozen"] < 0.0
    assert report["selection_decision"] == "SELECT_STAGE8_OBJECTIVE_UTILITY_CANDIDATE"
    assert report["next_status"] == "READY_FOR_STAGE8_4_LARGE_SCALE_OBJECTIVE_PANEL"

    evidence_rows = _read_jsonl(tmp_path / "objective_utility_evidence_table.jsonl")
    decision = json.loads(
        (tmp_path / "objective_utility_selection_decision.json").read_text()
    )
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())

    assert len(evidence_rows) == 2
    assert [row["method_name"] for row in evidence_rows] == [
        "selection_ready_stage8_operator",
        "frozen_stage5_selected_operator",
    ]
    assert evidence_rows[0]["candidate_id"] == "stage3_5_batch_1_reweighting_repair"
    assert evidence_rows[0]["rank"] == 1
    assert evidence_rows[0]["selected_by_stage8_3"] is True
    assert evidence_rows[1]["rank"] == 2
    assert evidence_rows[1]["selected_by_stage8_3"] is False
    assert all(row["target_scope"] == "shared_variables_only" for row in evidence_rows)
    assert all(
        row["objective_loop_executed_in_stage8_3"] is False for row in evidence_rows
    )
    assert all(row["not_final_performance_claim"] is True for row in evidence_rows)

    assert decision["stage"] == "8.3"
    assert decision["status"] == "PASS"
    assert decision["selected_candidate_id"] == "stage3_5_batch_1_reweighting_repair"
    assert decision["selected_operator_status"] == (
        "OBJECTIVE_UTILITY_SELECTED_NOT_FINAL_NOT_FROZEN_FOR_TEST"
    )
    assert decision["allowed_next_use"] == (
        "large-scale objective panel evaluation under locked protocol"
    )
    assert decision["selection_reason"] == (
        "lowest objective_final_best among Stage 8.2 LOCO candidates"
    )
    assert decision["stage8_1_selection_ready_member"] is True
    assert decision["validation_feedback_used"] is False
    assert decision["test_feedback_used"] is False
    assert decision["not_final_performance_claim"] is True

    assert ledger["stage"] == "8.3"
    assert ledger["status"] == "PASS"
    assert ledger["FE_total"] == 0
    assert ledger["inherited_stage8_2_FE_total"] == 36
    assert ledger["objective_evaluation_used"] is False

    assert boundary["stage"] == "8.3"
    assert boundary["status"] == "PASS"
    assert boundary["forbidden_behaviors"]["llm_call"] is False
    assert boundary["forbidden_behaviors"]["objective_loop_execution"] is False
    assert boundary["forbidden_behaviors"]["test_feedback_tuning"] is False
    assert boundary["forbidden_claims"] == [
        "SOTA improvement",
        "final objective-value performance improvement",
        "large-scale benchmark success",
    ]

    assert route["stage"] == "8.3"
    assert route["status"] == "PASS"
    assert route["next_stage"] == "Stage 8.4"
    assert route["allowed_next_work"] == "large_scale_objective_panel_evaluation"
    assert route["use_test_feedback"] is False


def test_stage8_3_committed_artifacts_and_docs_record_selection_boundary() -> None:
    required = [
        CONFIG,
        EVIDENCE_TABLE,
        SELECTION_DECISION,
        SELECTION_REPORT,
        FE_LEDGER,
        RUNTIME_BOUNDARY,
        ROUTE,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(SELECTION_REPORT.read_text(encoding="utf-8"))
    decision = json.loads(SELECTION_DECISION.read_text(encoding="utf-8"))
    evidence_rows = _read_jsonl(EVIDENCE_TABLE)
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))
    boundary = json.loads(RUNTIME_BOUNDARY.read_text(encoding="utf-8"))

    assert report["status"] == "PASS"
    assert report["selected_candidate_id"] == "stage3_5_batch_1_reweighting_repair"
    assert decision["selected_operator_status"] == (
        "OBJECTIVE_UTILITY_SELECTED_NOT_FINAL_NOT_FROZEN_FOR_TEST"
    )
    assert len(evidence_rows) == 2
    assert evidence_rows[0]["selected_by_stage8_3"] is True
    assert ledger["FE_total"] == 0
    assert boundary["claim_scope"] == "objective-level utility selection"

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Stage 8.3" in combined
    assert "objective-level utility evidence selection" in combined
    assert "stage3_5_batch_1_reweighting_repair" in combined
    assert "Stage 8.2 utility_report.json" in combined
    assert "no new objective evaluation" in combined
    assert "no validation feedback" in combined
    assert "no test feedback" in combined
    assert "not a final objective-value performance claim" in combined


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
