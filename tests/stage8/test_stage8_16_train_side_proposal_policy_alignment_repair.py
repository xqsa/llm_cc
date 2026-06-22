import json
from pathlib import Path


ROOT = Path("E:/llm_cc")
CONFIG = ROOT / "configs" / "stage8_16_train_side_proposal_policy_alignment_repair.yaml"
STAGE8_15_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_15"
OUTPUT_DIR = ROOT / "artifacts" / "objective_eval" / "stage8_16"
ALIGNMENT_REPORT = OUTPUT_DIR / "alignment_repair_report.json"
FEATURE_REPORT = OUTPUT_DIR / "reward_reliability_feature_report.json"
BRANCH_REPORT = OUTPUT_DIR / "policy_branch_alignment_report.json"
CLAIM_BOUNDARY = OUTPUT_DIR / "claim_boundary_report.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
NEXT_ROUTE = OUTPUT_DIR / "next_route_decision.json"
STAGE_DOC = ROOT / "docs" / "stage8" / "stage8_16_train_side_proposal_policy_alignment_repair.md"
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_16_self_check_report.md"
README = ROOT / "README.md"


def test_reward_trust_gate_prefers_best_reward_only_when_reliable() -> None:
    from loco.conflict.conflict_state import GroupProposal, SharedVariableConflictState
    from loco.coordination.train_side_proposal_policy_alignment_repair import (
        RewardTrustGatedCoordination,
        compute_reward_reliability_features,
    )

    reliable_state = SharedVariableConflictState.from_group_proposals(
        variable_id=7,
        current_value=10.0,
        bounds=(-100.0, 100.0),
        proposals=[
            GroupProposal(1, 7, 6.0, 0.95),
            GroupProposal(2, 7, 8.0, 0.54),
            GroupProposal(3, 7, 9.0, 0.50),
        ],
        diagnostics={"panel": "train_side_reward_reliable_fixture"},
    )
    unreliable_state = SharedVariableConflictState.from_group_proposals(
        variable_id=7,
        current_value=10.0,
        bounds=(-100.0, 100.0),
        proposals=[
            GroupProposal(1, 7, -95.0, 0.91),
            GroupProposal(2, 7, 8.5, 0.88),
            GroupProposal(3, 7, 9.0, 0.86),
        ],
        diagnostics={"panel": "train_side_reward_unreliable_fixture"},
    )

    reliable_features = compute_reward_reliability_features(reliable_state)
    unreliable_features = compute_reward_reliability_features(unreliable_state)
    policy = RewardTrustGatedCoordination()

    reliable_result = policy.coordinate(reliable_state)
    unreliable_result = policy.coordinate(unreliable_state)

    assert reliable_features["reward_top_margin"] >= 0.25
    assert reliable_features["best_reward_value_outlier_score"] <= 0.5
    assert reliable_features["best_reward_direction_agreement"] >= 2 / 3
    assert reliable_features["best_reward_trustworthy"] is True
    assert reliable_result.coordinated_value == 6.0
    assert reliable_result.diagnostics["policy_branch"] == "trust_best_reward"
    assert reliable_result.diagnostics["fallback_operator"] is None

    assert unreliable_features["best_reward_trustworthy"] is False
    assert unreliable_result.coordinated_value != -95.0
    assert unreliable_result.diagnostics["policy_branch"] in {
        "weighted_safety",
        "simple_safety",
        "shrinkage_repair",
    }
    assert unreliable_result.diagnostics["fallback_operator"] is not None


def test_stage8_16_builds_train_side_alignment_repair_without_official_feedback(tmp_path) -> None:
    from loco.coordination.train_side_proposal_policy_alignment_repair import (
        run_stage8_16_train_side_proposal_policy_alignment_repair,
    )

    report = run_stage8_16_train_side_proposal_policy_alignment_repair(
        stage8_15_diagnosis_report_path=STAGE8_15_DIR / "diagnosis_report.json",
        stage8_15_method_gap_path=STAGE8_15_DIR / "method_gap_report.json",
        stage8_15_branch_diagnostics_path=STAGE8_15_DIR / "branch_diagnostics.json",
        stage8_15_root_cause_path=STAGE8_15_DIR / "root_cause_hypotheses.json",
        stage8_15_fe_ledger_path=STAGE8_15_DIR / "fe_ledger.json",
        stage8_15_runtime_boundary_path=STAGE8_15_DIR / "runtime_boundary.json",
        stage8_15_next_route_path=STAGE8_15_DIR / "next_route_decision.json",
        output_dir=tmp_path,
    )

    assert report["stage"] == "8.16"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "8.15"
    assert report["repair_scope"] == "train_side_proposal_policy_alignment_repair"
    assert report["dominant_failure_mode_addressed"] == "best_reward_select_alignment_gap"
    assert report["repair_policy_name"] == "reward_trust_gated_coordination_v1"
    assert report["train_side_repair_candidate_created"] is True
    assert report["official_cec2013_feedback_used_for_tuning"] is False
    assert report["stage8_14_smoke_used_as_direct_tuning_feedback"] is False
    assert report["reward_reliability_features_added"] is True
    assert report["policy_alignment_gate_added"] is True
    assert report["trust_best_reward_fixture_passed"] is True
    assert report["unsafe_best_reward_fallback_fixture_passed"] is True
    assert report["full_25_run_panel_blocked"] is True
    assert report["recommended_next_stage"] == "Stage 8.17"
    assert report["recommended_next_work"] == "bounded_train_side_repaired_policy_objective_check"
    assert report["FE_total"] == 0
    assert report["objective_loop_executed"] is False
    assert report["new_objective_evaluation_used"] is False

    for flag in [
        "llm_call_used",
        "new_llm_candidate_generation_used",
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

    feature_report = json.loads((tmp_path / "reward_reliability_feature_report.json").read_text())
    branch_report = json.loads((tmp_path / "policy_branch_alignment_report.json").read_text())
    claim = json.loads((tmp_path / "claim_boundary_report.json").read_text())
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())

    assert feature_report["feature_names"] == [
        "reward_top_margin",
        "reward_concentration",
        "best_reward_direction_agreement",
        "best_reward_value_outlier_score",
        "best_reward_update_fraction",
    ]
    assert feature_report["fixture_count"] == 5
    assert feature_report["trustworthy_fixture_count"] >= 1
    assert feature_report["untrustworthy_fixture_count"] >= 1
    assert feature_report["FE_total"] == 0

    assert branch_report["policy_branches"] == [
        "trust_best_reward",
        "weighted_safety",
        "simple_safety",
        "shrinkage_repair",
    ]
    assert branch_report["trust_best_reward_case_count"] >= 1
    assert branch_report["fallback_case_count"] >= 1
    assert branch_report["branch_counts"]["shrinkage_repair"] >= 1
    assert branch_report["best_reward_alignment_gap_addressed"] is True

    assert claim["official_benchmark_claim_allowed"] is False
    assert claim["sota_claim_allowed"] is False
    assert claim["final_performance_claim_allowed"] is False
    assert claim["policy_selected_for_official_panel"] is False
    assert claim["allowed_claim"] == (
        "Stage 8.16 adds a train-side reward-reliability alignment gate and "
        "a repair candidate for later bounded objective checking."
    )

    assert ledger["FE_total"] == 0
    assert ledger["inherited_stage8_15_FE_total"] == 0
    assert ledger["inherited_stage8_14_FE_total"] == 24010
    assert ledger["objective_loop_executed"] is False
    assert boundary["forbidden_behaviors"]["stage8_14_direct_tuning_feedback"] is False
    assert boundary["forbidden_behaviors"]["selected_operator_revision"] is False
    assert route["next_stage"] == "Stage 8.17"
    assert route["run_full_25_run_panel_next"] is False
    assert route["allowed_next_work"] == "bounded_train_side_repaired_policy_objective_check"


def test_stage8_16_committed_artifacts_docs_and_readme_record_repair() -> None:
    required = [
        CONFIG,
        ALIGNMENT_REPORT,
        FEATURE_REPORT,
        BRANCH_REPORT,
        CLAIM_BOUNDARY,
        FE_LEDGER,
        RUNTIME_BOUNDARY,
        NEXT_ROUTE,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(ALIGNMENT_REPORT.read_text(encoding="utf-8"))
    feature_report = json.loads(FEATURE_REPORT.read_text(encoding="utf-8"))
    branch_report = json.loads(BRANCH_REPORT.read_text(encoding="utf-8"))
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))
    route = json.loads(NEXT_ROUTE.read_text(encoding="utf-8"))

    assert report["stage"] == "8.16"
    assert report["status"] == "PASS"
    assert report["repair_policy_name"] == "reward_trust_gated_coordination_v1"
    assert report["dominant_failure_mode_addressed"] == "best_reward_select_alignment_gap"
    assert feature_report["best_reward_trust_gate_defined"] is True
    assert branch_report["best_reward_alignment_gap_addressed"] is True
    assert ledger["FE_total"] == 0
    assert route["next_stage"] == "Stage 8.17"

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Current repository state: `Stage 8.17 PASS`" in combined
    assert "Stage 8.16   train-side proposal/policy alignment repair" in combined
    assert "reward_trust_gated_coordination_v1" in combined
    assert "best_reward_select_alignment_gap" in combined
    assert "FE_total = 0" in combined
    assert "not a SOTA claim" in combined
    assert "not a final objective-value performance claim" in combined
