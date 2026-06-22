import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage8_7_conditional_policy_ablation.yaml"
STAGE8_6_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_6"
STAGE8_6_CASE_TABLE = STAGE8_6_DIR / "ablation_case_table.jsonl"
STAGE8_6_SUMMARY = STAGE8_6_DIR / "ablation_summary.json"
STAGE8_6_OPERATOR = STAGE8_6_DIR / "operator_family_ablation_report.json"
STAGE8_6_PROPOSAL = STAGE8_6_DIR / "proposal_state_ablation_report.json"
OUTPUT_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_7"
SUMMARY = OUTPUT_DIR / "conditional_policy_summary.json"
CONDITIONAL_POLICY = OUTPUT_DIR / "conditional_policy_report.json"
FEATURE_REPORT = OUTPUT_DIR / "proposal_state_feature_report.json"
CASE_TABLE = OUTPUT_DIR / "case_policy_table.jsonl"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
ROUTE = OUTPUT_DIR / "next_route_decision.json"
STAGE_DOC = ROOT / "docs" / "stage8" / "stage8_7_conditional_policy_ablation.md"
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_7_self_check_report.md"
README = ROOT / "README.md"


def test_stage8_7_recovers_simple_regimes_without_weighted_collapse(tmp_path) -> None:
    from loco.coordination.conditional_proposal_state_policy import (
        run_stage8_7_conditional_policy_ablation,
    )

    summary = run_stage8_7_conditional_policy_ablation(
        stage8_6_case_table_path=STAGE8_6_CASE_TABLE,
        stage8_6_summary_path=STAGE8_6_SUMMARY,
        stage8_6_operator_report_path=STAGE8_6_OPERATOR,
        stage8_6_proposal_report_path=STAGE8_6_PROPOSAL,
        output_dir=tmp_path,
    )

    assert summary["stage"] == "8.7"
    assert summary["status"] == "PASS"
    assert summary["source_stage"] == "8.6"
    assert summary["policy_scope"] == "conditional_proposal_state_policy_ablation"
    assert summary["selected_candidate_id"] == "stage3_5_batch_1_reweighting_repair"
    assert summary["case_count"] == 36
    assert summary["simple_preferred_regime_count"] == 12
    assert summary["weighted_sufficient_regime_count"] == 24
    assert summary["simple_preferred_regime_recovery_count"] == 12
    assert summary["weighted_sufficient_regression_count"] == 0
    assert summary["conditional_policy_not_equivalent_to_weighted_consensus"] is True
    assert summary["family_collapse_gate_passed"] is True
    assert summary["official_claim_blocked"] is True
    assert summary["recommended_next_stage"] == (
        "Stage 8.8 objective-loop rerun for conditional policy"
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

    policy = json.loads((tmp_path / "conditional_policy_report.json").read_text())
    features = json.loads((tmp_path / "proposal_state_feature_report.json").read_text())
    case_rows = _read_jsonl(tmp_path / "case_policy_table.jsonl")
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())

    assert policy["stage"] == "8.7"
    assert policy["status"] == "PASS"
    assert policy["policy_name"] == "overlap_reward_reliability_switch_v1"
    assert policy["switch_to_simple_count"] == 12
    assert policy["keep_weighted_count"] == 24
    assert policy["simple_preferred_regime_recovery_count"] == 12
    assert policy["weighted_sufficient_regression_count"] == 0
    assert policy["conditional_policy_not_equivalent_to_weighted_consensus"] is True
    assert policy["conditional_policy_not_equivalent_to_simple_consensus"] is True
    assert policy["family_collapse_gate_passed"] is True
    assert policy["policy_rule"] == (
        "use simple_consensus when overlap is medium/high and reward-weighted "
        "behavior is unreliable; otherwise keep weighted_consensus"
    )

    assert features["stage"] == "8.7"
    assert features["status"] == "PASS"
    assert features["feature_schema_version"] == "loco.stage8_7_proposal_features.v1"
    assert features["feature_names"] == [
        "overlap_degree",
        "reward_reliability",
        "weighted_vs_simple_final_best_delta",
        "selected_minus_simple_mean_update_size",
    ]
    assert features["high_overlap_case_count"] == 9
    assert features["medium_overlap_case_count"] == 9
    assert features["low_overlap_case_count"] == 9
    assert features["conflicting_overlap_case_count"] == 9
    assert features["unreliable_reward_case_count"] == 12

    assert len(case_rows) == 36
    assert all(row["stage"] == "8.7" for row in case_rows)
    assert sum(row["policy_action"] == "use_simple_consensus" for row in case_rows) == 12
    assert sum(row["policy_action"] == "keep_weighted_consensus" for row in case_rows) == 24
    assert all(
        row["policy_action"] == "use_simple_consensus"
        for row in case_rows
        if row["source_regime"] == "simple_consensus_preferred"
    )
    assert all(
        row["policy_action"] == "keep_weighted_consensus"
        for row in case_rows
        if row["source_regime"] == "weighted_consensus_sufficient"
    )
    assert all(row["objective_evaluation_used_in_stage8_7"] is False for row in case_rows)

    assert ledger["stage"] == "8.7"
    assert ledger["status"] == "PASS"
    assert ledger["FE_total"] == 0
    assert ledger["objective_loop_executed"] is False
    assert ledger["new_objective_evaluation_used"] is False

    assert boundary["stage"] == "8.7"
    assert boundary["status"] == "PASS"
    assert boundary["claim_scope"] == "conditional proposal-state policy ablation"
    assert boundary["forbidden_behaviors"]["new_objective_evaluation"] is False
    assert boundary["forbidden_behaviors"]["selected_operator_revision"] is False
    assert boundary["forbidden_behaviors"]["test_feedback"] is False

    assert route["stage"] == "8.7"
    assert route["status"] == "PASS"
    assert route["decision"] == "READY_FOR_STAGE8_8_OBJECTIVE_LOOP_RERUN"
    assert route["next_stage"] == "Stage 8.8"
    assert route["use_test_feedback"] is False


def test_stage8_7_committed_artifacts_docs_and_readme_record_policy_boundary() -> None:
    required = [
        CONFIG,
        SUMMARY,
        CONDITIONAL_POLICY,
        FEATURE_REPORT,
        CASE_TABLE,
        FE_LEDGER,
        RUNTIME_BOUNDARY,
        ROUTE,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    policy = json.loads(CONDITIONAL_POLICY.read_text(encoding="utf-8"))
    features = json.loads(FEATURE_REPORT.read_text(encoding="utf-8"))
    case_rows = _read_jsonl(CASE_TABLE)
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))

    assert summary["status"] == "PASS"
    assert summary["conditional_policy_not_equivalent_to_weighted_consensus"] is True
    assert summary["simple_preferred_regime_recovery_count"] == 12
    assert summary["weighted_sufficient_regression_count"] == 0
    assert policy["family_collapse_gate_passed"] is True
    assert features["unreliable_reward_case_count"] == 12
    assert len(case_rows) == 36
    assert ledger["FE_total"] == 0

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Stage 8.7" in combined
    assert "Stage 8.7    conditional proposal-state policy ablation                PASS" in combined
    assert "overlap/reward-reliability aware conditional policy" in combined
    assert "simple_preferred_regime_recovery_count = 12" in combined
    assert "weighted_sufficient_regression_count = 0" in combined
    assert "conditional_policy_not_equivalent_to_weighted_consensus = true" in combined
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
