import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage8_6_proposal_state_operator_family_ablation.yaml"
STAGE8_4_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_4"
STAGE8_5_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_5"
STAGE8_4_TRACE = STAGE8_4_DIR / "objective_trace.jsonl"
STAGE8_4_WIN_LOSS = STAGE8_4_DIR / "win_loss_report.json"
STAGE8_5_DIAGNOSIS = STAGE8_5_DIR / "failure_honest_diagnosis_report.json"
STAGE8_5_EQUIVALENCE = STAGE8_5_DIR / "baseline_equivalence_report.json"
STAGE8_5_TOPOLOGY = STAGE8_5_DIR / "topology_gap_report.json"
OUTPUT_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_6"
ABLATION_SUMMARY = OUTPUT_DIR / "ablation_summary.json"
OPERATOR_FAMILY_REPORT = OUTPUT_DIR / "operator_family_ablation_report.json"
PROPOSAL_STATE_REPORT = OUTPUT_DIR / "proposal_state_ablation_report.json"
CASE_TABLE = OUTPUT_DIR / "ablation_case_table.jsonl"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
ROUTE = OUTPUT_DIR / "next_route_decision.json"
STAGE_DOC = (
    ROOT / "docs" / "stage8" / "stage8_6_proposal_state_operator_family_ablation.md"
)
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_6_self_check_report.md"
README = ROOT / "README.md"


def test_stage8_6_runs_proposal_state_operator_family_ablation(tmp_path) -> None:
    from loco.coordination.proposal_state_operator_family_ablation import (
        run_stage8_6_proposal_state_operator_family_ablation,
    )

    summary = run_stage8_6_proposal_state_operator_family_ablation(
        stage8_4_trace_path=STAGE8_4_TRACE,
        stage8_4_win_loss_path=STAGE8_4_WIN_LOSS,
        stage8_5_diagnosis_path=STAGE8_5_DIAGNOSIS,
        stage8_5_equivalence_path=STAGE8_5_EQUIVALENCE,
        stage8_5_topology_path=STAGE8_5_TOPOLOGY,
        output_dir=tmp_path,
    )

    assert summary["stage"] == "8.6"
    assert summary["status"] == "PASS"
    assert summary["source_stage"] == "8.5"
    assert summary["ablation_scope"] == "proposal_state_operator_family_ablation"
    assert summary["selected_candidate_id"] == "stage3_5_batch_1_reweighting_repair"
    assert summary["primary_result"] == (
        "operator_family_collapse_to_weighted_consensus_confirmed"
    )
    assert summary["proposal_state_result"] == (
        "simple_consensus_needed_for_high_overlap_and_seed0_medium_regimes"
    )
    assert summary["case_count"] == 36
    assert summary["loss_regime_case_count"] == 12
    assert summary["weighted_sufficient_case_count"] == 24
    assert summary["operator_family_collapse_confirmed"] is True
    assert summary["proposal_state_gap_confirmed"] is True
    assert summary["official_claim_blocked"] is True
    assert summary["recommended_next_stage"] == (
        "Stage 8.7 conditional proposal-state policy or operator-family expansion"
    )
    assert summary["objective_loop_executed"] is False
    assert summary["new_objective_evaluation_used"] is False
    assert summary["FE_total"] == 0

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
        assert summary[flag] is False
    assert summary["not_sota_claim"] is True
    assert summary["not_final_performance_claim"] is True

    operator_family = json.loads(
        (tmp_path / "operator_family_ablation_report.json").read_text()
    )
    proposal_state = json.loads(
        (tmp_path / "proposal_state_ablation_report.json").read_text()
    )
    case_rows = _read_jsonl(tmp_path / "ablation_case_table.jsonl")
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())

    assert operator_family["stage"] == "8.6"
    assert operator_family["status"] == "PASS"
    assert operator_family["selected_weighted_coord_value_max_abs_delta"] == 0.0
    assert operator_family["selected_weighted_update_size_max_abs_delta"] == 0.0
    assert operator_family["selected_weighted_final_best_max_abs_delta"] == 0.0
    assert operator_family["selected_weighted_family_collapse_confirmed"] is True
    assert operator_family["projection_penalty_case_count"] == 36
    assert operator_family["best_reward_select_overstep_confirmed"] is True
    assert operator_family["recommended_operator_family_action"] == (
        "add conditional/simple-consensus-aware families instead of more weighted clones"
    )

    assert proposal_state["stage"] == "8.6"
    assert proposal_state["status"] == "PASS"
    assert proposal_state["loss_regime_case_count"] == 12
    assert proposal_state["weighted_sufficient_case_count"] == 24
    assert proposal_state["loss_panels"] == {
        "synthetic_high_overlap_panel": 9,
        "synthetic_medium_overlap_panel": 3,
    }
    assert proposal_state["loss_best_baseline_methods"] == {"simple_consensus": 12}
    assert proposal_state["tie_best_baseline_methods"] == {"weighted_consensus": 24}
    assert proposal_state["mean_loss_selected_minus_simple_update_size"] > 0.0
    assert proposal_state["recommended_proposal_state_action"] == (
        "add overlap/topology and reward-reliability features before official claims"
    )

    assert len(case_rows) == 36
    assert all(row["stage"] == "8.6" for row in case_rows)
    assert sum(row["regime"] == "simple_consensus_preferred" for row in case_rows) == 12
    assert (
        sum(row["regime"] == "weighted_consensus_sufficient" for row in case_rows) == 24
    )
    assert all(
        row["objective_evaluation_used_in_stage8_6"] is False for row in case_rows
    )
    assert all(
        row["selected_weighted_coord_value_abs_delta"] == 0.0 for row in case_rows
    )

    assert ledger["stage"] == "8.6"
    assert ledger["status"] == "PASS"
    assert ledger["FE_total"] == 0
    assert ledger["inherited_stage8_4_FE_total"] == 1296
    assert ledger["objective_loop_executed"] is False
    assert ledger["new_objective_evaluation_used"] is False

    assert boundary["stage"] == "8.6"
    assert boundary["status"] == "PASS"
    assert boundary["claim_scope"] == "proposal-state/operator-family ablation"
    assert boundary["forbidden_behaviors"]["new_objective_evaluation"] is False
    assert boundary["forbidden_behaviors"]["selected_operator_revision"] is False
    assert boundary["forbidden_behaviors"]["test_feedback"] is False

    assert route["stage"] == "8.6"
    assert route["status"] == "PASS"
    assert route["decision"] == "BLOCK_OFFICIAL_CLAIMS_AND_EXPAND_ABLATION"
    assert route["next_stage"] == "Stage 8.7"
    assert route["use_test_feedback"] is False


def test_stage8_6_committed_artifacts_docs_and_readme_record_ablation_boundary() -> (
    None
):
    required = [
        CONFIG,
        ABLATION_SUMMARY,
        OPERATOR_FAMILY_REPORT,
        PROPOSAL_STATE_REPORT,
        CASE_TABLE,
        FE_LEDGER,
        RUNTIME_BOUNDARY,
        ROUTE,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    summary = json.loads(ABLATION_SUMMARY.read_text(encoding="utf-8"))
    operator_family = json.loads(OPERATOR_FAMILY_REPORT.read_text(encoding="utf-8"))
    proposal_state = json.loads(PROPOSAL_STATE_REPORT.read_text(encoding="utf-8"))
    case_rows = _read_jsonl(CASE_TABLE)
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))

    assert summary["status"] == "PASS"
    assert summary["official_claim_blocked"] is True
    assert operator_family["selected_weighted_family_collapse_confirmed"] is True
    assert proposal_state["loss_regime_case_count"] == 12
    assert len(case_rows) == 36
    assert ledger["FE_total"] == 0

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Stage 8.6" in combined
    assert (
        "Stage 8.6    proposal-state/operator-family ablation                  PASS"
        in combined
    )
    assert "operator-family collapse to weighted_consensus" in combined
    assert "simple_consensus is needed in 12 high/medium-overlap cases" in combined
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
