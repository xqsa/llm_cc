import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage7_3_objective_result_polish.yaml"
SOURCE_DIR = ROOT / "artifacts" / "objective_eval" / "stage7_2"
OUTPUT_DIR = ROOT / "artifacts" / "objective_eval" / "stage7_3"
PAPER_OBJECTIVE_TABLE = OUTPUT_DIR / "paper_objective_table.csv"
OBJECTIVE_CURVE_TABLE = OUTPUT_DIR / "objective_curve_table.csv"
METHOD_RANKING = OUTPUT_DIR / "method_ranking.json"
CLAIM_BOUNDARY = OUTPUT_DIR / "claim_boundary.json"
PAPER_TABLES_REPORT = OUTPUT_DIR / "paper_tables_report.json"
STAGE_DOC = ROOT / "docs" / "stage7" / "stage7_3_objective_result_polish.md"
SELF_CHECK = ROOT / "docs" / "stage7" / "stage7_3_self_check_report.md"
README = ROOT / "README.md"


EXPECTED_PANELS = {
    "synthetic_no_overlap_panel",
    "synthetic_low_overlap_panel",
    "synthetic_conflicting_overlap_panel",
    "synthetic_high_overlap_panel",
}
EXPECTED_METHODS = {
    "identity_no_coord",
    "simple_consensus",
    "weighted_consensus",
    "best_reward_select",
    "selected_loco_operator",
}


def test_stage7_3_builds_paper_ready_tables_from_stage7_2_only(tmp_path) -> None:
    from loco.coordination.objective_result_polish import (
        run_stage7_3_objective_result_polish,
    )

    report = run_stage7_3_objective_result_polish(
        source_dir=SOURCE_DIR,
        output_dir=tmp_path,
    )

    assert report["stage"] == "7.3"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "7.2"
    assert report["polish_scope"] == "paper_ready_objective_tables"
    assert report["source_trace_row_count"] == 120
    assert report["paper_objective_row_count"] == 40
    assert report["objective_curve_row_count"] == 120
    assert report["method_count"] == 5
    assert report["panel_count"] == 4
    assert report["dimension_count"] == 2
    assert report["new_objective_evaluation_used"] is False
    assert report["stage7_2_artifacts_modified"] is False
    assert report["not_final_performance_claim"] is True
    assert report["not_sota_claim"] is True
    assert report["next_status"] == "READY_FOR_OPTIONAL_CEC2013_OR_PAPER_DRAFT"

    objective_rows = _read_csv(tmp_path / "paper_objective_table.csv")
    curve_rows = _read_csv(tmp_path / "objective_curve_table.csv")
    ranking = json.loads((tmp_path / "method_ranking.json").read_text())
    boundary = json.loads((tmp_path / "claim_boundary.json").read_text())

    assert len(objective_rows) == 40
    assert len(curve_rows) == 120
    assert {row["synthetic_panel"] for row in objective_rows} == EXPECTED_PANELS
    assert {row["method_name"] for row in objective_rows} == EXPECTED_METHODS
    assert {int(row["problem_dimension"]) for row in objective_rows} == {500, 1000}
    assert all(row["source_stage"] == "7.2" for row in objective_rows)
    assert all(row["stage"] == "7.3" for row in objective_rows)
    assert all(row["objective_name"] == "synthetic_sphere" for row in objective_rows)
    assert all(row["lower_is_better"] == "true" for row in objective_rows)
    assert all(row["same_budget_across_methods"] == "true" for row in objective_rows)
    assert all(row["FE_global_objective"] == "3" for row in objective_rows)
    assert all(row["FE_total"] == "6" for row in objective_rows)
    assert all(
        row["new_objective_evaluation_used"] == "false" for row in objective_rows
    )
    assert all(row["not_final_performance_claim"] == "true" for row in objective_rows)

    assert all(row["objective_step"] in {"1", "2", "3"} for row in curve_rows)
    assert all(row["best_objective_so_far"] for row in curve_rows)
    assert all(
        row["FE_global_objective_cumulative"] in {"1", "2", "3"} for row in curve_rows
    )
    assert all(row["FE_total_cumulative"] in {"2", "4", "6"} for row in curve_rows)

    no_overlap_rows = [
        row
        for row in objective_rows
        if row["synthetic_panel"] == "synthetic_no_overlap_panel"
    ]
    assert len(no_overlap_rows) == 10
    assert all(float(row["delta_vs_identity"]) == 0.0 for row in no_overlap_rows)
    assert all(row["rank_in_panel_dimension"] == "1" for row in no_overlap_rows)

    assert ranking["stage"] == "7.3"
    assert ranking["status"] == "PASS"
    assert ranking["best_overall_method"] == "simple_consensus"
    assert ranking["selected_loco_operator_rank_overall"] == 4
    assert ranking["selected_loco_operator_best_panel_dimension_count"] == 2
    assert ranking["same_budget_across_methods"] is True
    assert ranking["ranking_metric"] == "mean_final_best_objective"

    assert boundary["stage"] == "7.3"
    assert boundary["status"] == "PASS"
    assert boundary["allowed_claims"] == [
        "Stage 7.3 converts Stage 7.2 synthetic objective-loop traces into paper-ready tables and curve data.",
        "The Stage 7.2 synthetic panel ran under the same FE budget across locked methods.",
        "Current synthetic evidence is mixed and does not support a final performance or SOTA claim.",
    ]
    assert (
        "final objective-value performance superiority" in boundary["forbidden_claims"]
    )
    assert "SOTA improvement" in boundary["forbidden_claims"]
    assert boundary["selected_loco_not_best_overall"] is True
    assert boundary["requires_optional_cec2013_decision"] is True
    assert boundary["new_objective_evaluation_used"] is False
    assert boundary["test_feedback_tuning_used"] is False


def test_stage7_3_committed_artifacts_docs_and_readme_record_claim_boundary() -> None:
    required = [
        CONFIG,
        PAPER_OBJECTIVE_TABLE,
        OBJECTIVE_CURVE_TABLE,
        METHOD_RANKING,
        CLAIM_BOUNDARY,
        PAPER_TABLES_REPORT,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(PAPER_TABLES_REPORT.read_text(encoding="utf-8"))
    ranking = json.loads(METHOD_RANKING.read_text(encoding="utf-8"))
    boundary = json.loads(CLAIM_BOUNDARY.read_text(encoding="utf-8"))
    objective_rows = _read_csv(PAPER_OBJECTIVE_TABLE)
    curve_rows = _read_csv(OBJECTIVE_CURVE_TABLE)

    assert report["status"] == "PASS"
    assert report["stage"] == "7.3"
    assert report["paper_objective_row_count"] == 40
    assert report["objective_curve_row_count"] == 120
    assert ranking["selected_loco_operator_rank_overall"] == 4
    assert boundary["selected_loco_not_best_overall"] is True
    assert len(objective_rows) == 40
    assert len(curve_rows) == 120

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Current repository state: `Stage 7.3 PASS`" in combined
    assert (
        "Stage 7.3    objective result polish and paper-ready tables         PASS"
        in combined
    )
    assert "Stage 7.4" in combined
    assert "paper_objective_table.csv" in combined
    assert "objective_curve_table.csv" in combined
    assert "method_ranking.json" in combined
    assert "claim_boundary.json" in combined
    assert "selected_loco_operator_rank_overall = 4" in combined
    assert "not a final objective-value performance claim" in combined
    assert "not a SOTA claim" in combined
    assert "no new objective evaluation" in combined


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))
