import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage8_5_failure_honest_analysis.yaml"
STAGE8_4_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_4"
STAGE8_4_TRACE = STAGE8_4_DIR / "objective_trace.jsonl"
STAGE8_4_WIN_LOSS = STAGE8_4_DIR / "win_loss_report.json"
STAGE8_4_METHOD_SUMMARY = STAGE8_4_DIR / "method_summary.json"
STAGE8_4_PANEL_REPORT = STAGE8_4_DIR / "panel_report.json"
OUTPUT_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_5"
DIAGNOSIS_REPORT = OUTPUT_DIR / "failure_honest_diagnosis_report.json"
BASELINE_EQUIVALENCE = OUTPUT_DIR / "baseline_equivalence_report.json"
TOPOLOGY_GAP = OUTPUT_DIR / "topology_gap_report.json"
CASE_DIAGNOSIS = OUTPUT_DIR / "case_diagnosis_table.jsonl"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
ROUTE = OUTPUT_DIR / "next_route_decision.json"
STAGE_DOC = ROOT / "docs" / "stage8" / "stage8_5_failure_honest_analysis.md"
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_5_self_check_report.md"
README = ROOT / "README.md"


def test_stage8_5_analyzes_why_selected_operator_does_not_beat_best_baseline(
    tmp_path,
) -> None:
    from loco.coordination.failure_honest_analysis import (
        run_stage8_5_failure_honest_analysis,
    )

    report = run_stage8_5_failure_honest_analysis(
        stage8_4_trace_path=STAGE8_4_TRACE,
        stage8_4_win_loss_path=STAGE8_4_WIN_LOSS,
        stage8_4_method_summary_path=STAGE8_4_METHOD_SUMMARY,
        stage8_4_panel_report_path=STAGE8_4_PANEL_REPORT,
        output_dir=tmp_path,
    )

    assert report["stage"] == "8.5"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "8.4"
    assert report["analysis_scope"] == "failure_honest_stage8_4_analysis"
    assert report["selected_candidate_id"] == "stage3_5_batch_1_reweighting_repair"
    assert report["previous_frozen_candidate_id"] == (
        "stage3_5_batch_1_weighted_consensus_projection"
    )
    assert report["stage8_4_trace_row_count"] == 648
    assert report["comparison_case_count"] == 36
    assert report["vs_frozen_stage5"] == {"win": 36, "tie": 0, "loss": 0}
    assert report["vs_best_baseline"] == {"win": 0, "tie": 24, "loss": 12}
    assert report["primary_diagnosis"] == (
        "selected_operator_equivalent_to_weighted_consensus_baseline"
    )
    assert report["secondary_diagnosis"] == (
        "simple_consensus_beats_selected_operator_on_high_and_seed0_medium_cases"
    )
    assert report["why_win_old_frozen"] == (
        "stage8_3_selected_operator removes the frozen Stage 5.1 projection penalty"
    )
    assert report["why_not_beat_best_baseline"] == (
        "stage8_3_selected_operator behavior is numerically identical to weighted_consensus"
    )
    assert report["recommended_next_stage"] == (
        "Stage 8.6 proposal-state/operator-family ablation before official claims"
    )
    assert report["objective_loop_executed"] is False
    assert report["new_objective_evaluation_used"] is False
    assert report["FE_total"] == 0

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

    equivalence = json.loads(
        (tmp_path / "baseline_equivalence_report.json").read_text()
    )
    topology = json.loads((tmp_path / "topology_gap_report.json").read_text())
    case_rows = _read_jsonl(tmp_path / "case_diagnosis_table.jsonl")
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())

    assert equivalence["stage"] == "8.5"
    assert equivalence["status"] == "PASS"
    assert equivalence["selected_vs_weighted_max_abs_final_best_delta"] == 0.0
    assert equivalence["selected_vs_weighted_max_abs_update_size_delta"] == 0.0
    assert equivalence["selected_matches_weighted_consensus_all_cases"] is True
    assert equivalence["selected_matches_weighted_consensus_all_steps"] is True
    assert equivalence["weighted_consensus_best_baseline_case_count"] == 24
    assert equivalence["simple_consensus_best_baseline_case_count"] == 12
    assert equivalence["projection_penalty_vs_selected_case_count"] == 36
    assert equivalence["mean_selected_minus_frozen_final_best_delta"] < 0.0

    assert topology["stage"] == "8.5"
    assert topology["status"] == "PASS"
    assert topology["selected_loss_to_best_baseline_case_count"] == 12
    assert topology["loss_panels"] == {
        "synthetic_high_overlap_panel": 9,
        "synthetic_medium_overlap_panel": 3,
    }
    assert topology["loss_best_baseline_methods"] == {"simple_consensus": 12}
    assert topology["tie_best_baseline_methods"] == {"weighted_consensus": 24}

    assert len(case_rows) == 36
    assert all(row["stage"] == "8.5" for row in case_rows)
    assert all(row["diagnosis"] in {
        "selected_ties_weighted_consensus_best_baseline",
        "simple_consensus_beats_selected_operator",
    } for row in case_rows)
    assert sum(
        1 for row in case_rows if row["diagnosis"] == "simple_consensus_beats_selected_operator"
    ) == 12
    assert all(row["objective_evaluation_used_in_stage8_5"] is False for row in case_rows)

    assert ledger["stage"] == "8.5"
    assert ledger["status"] == "PASS"
    assert ledger["FE_total"] == 0
    assert ledger["inherited_stage8_4_FE_total"] == 1296
    assert ledger["objective_loop_executed"] is False

    assert boundary["stage"] == "8.5"
    assert boundary["status"] == "PASS"
    assert boundary["claim_scope"] == "failure-honest Stage 8.4 analysis"
    assert boundary["forbidden_behaviors"]["new_objective_evaluation"] is False
    assert boundary["forbidden_behaviors"]["test_feedback"] is False
    assert boundary["forbidden_behaviors"]["selected_operator_revision"] is False

    assert route["stage"] == "8.5"
    assert route["status"] == "PASS"
    assert route["decision"] == "DO_NOT_MAKE_OFFICIAL_OR_SOTA_CLAIM_YET"
    assert route["next_stage"] == "Stage 8.6"
    assert route["use_test_feedback"] is False


def test_stage8_5_committed_artifacts_docs_and_readme_record_failure_honesty() -> None:
    required = [
        CONFIG,
        DIAGNOSIS_REPORT,
        BASELINE_EQUIVALENCE,
        TOPOLOGY_GAP,
        CASE_DIAGNOSIS,
        RUNTIME_BOUNDARY,
        FE_LEDGER,
        ROUTE,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(DIAGNOSIS_REPORT.read_text(encoding="utf-8"))
    equivalence = json.loads(BASELINE_EQUIVALENCE.read_text(encoding="utf-8"))
    topology = json.loads(TOPOLOGY_GAP.read_text(encoding="utf-8"))
    case_rows = _read_jsonl(CASE_DIAGNOSIS)
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))

    assert report["status"] == "PASS"
    assert report["primary_diagnosis"] == (
        "selected_operator_equivalent_to_weighted_consensus_baseline"
    )
    assert equivalence["selected_matches_weighted_consensus_all_cases"] is True
    assert topology["selected_loss_to_best_baseline_case_count"] == 12
    assert len(case_rows) == 36
    assert ledger["FE_total"] == 0

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Stage 8.5" in combined
    assert "Current repository state: `Stage 8.5 PASS`" in combined
    assert "selected operator is numerically equivalent to weighted_consensus" in combined
    assert "simple_consensus beats it on 12 cases" in combined
    assert "wins the old frozen operator by removing the projection penalty" in combined
    assert "FE_total = 0" in combined
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
