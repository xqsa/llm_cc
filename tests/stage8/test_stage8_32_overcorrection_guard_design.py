import json
from pathlib import Path


ROOT = Path("E:/llm_cc")
STAGE8_31_DIR = ROOT / "artifacts" / "analysis" / "stage8_31"
OUTPUT_DIR = ROOT / "artifacts" / "analysis" / "stage8_32"
CONFIG = ROOT / "configs" / "stage8_32_overcorrection_guard_design.yaml"
REPORT = OUTPUT_DIR / "repair_design_report.json"
POLICY = OUTPUT_DIR / "guarded_policy_payload.json"
GUARD_SPEC = OUTPUT_DIR / "overcorrection_guard_spec.json"
COVERAGE = OUTPUT_DIR / "static_guard_coverage_report.json"
CLAIM_BOUNDARY = OUTPUT_DIR / "claim_boundary_report.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
NEXT_ROUTE = OUTPUT_DIR / "next_route_decision.json"
STAGE_DOC = ROOT / "docs" / "stage8" / "stage8_32_overcorrection_guard_design.md"
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_32_self_check_report.md"
README = ROOT / "README.md"


def test_stage8_32_guarded_policy_covers_owner_trust_and_overcorrection_paths() -> None:
    from loco.coordination.overcorrection_guard_design import (
        GuardedOwnerTrustPolicy,
        guarded_static_fixtures,
    )

    policy = GuardedOwnerTrustPolicy()
    decisions = {
        fixture["fixture_id"]: policy.decide(fixture)
        for fixture in guarded_static_fixtures()
    }

    reliable = decisions["best_reward_reliable_preserve"]
    assert reliable["shared_variable_owner"] == "best_reward_group"
    assert reliable["linkage_decision"] == "preserve"
    assert reliable["coordination_action"] == "trust_best_reward"

    conflict = decisions["strong_owner_conflict_best_reward_misleading"]
    assert conflict["shared_variable_owner"] == "contribution_leader"
    assert conflict["linkage_decision"] == "break"
    assert conflict["coordination_action"] == "owner_proposal_select"

    unstable = decisions["unstable_or_uncertain_historical_shrinkage"]
    assert unstable["shared_variable_owner"] == "historical_owner"
    assert unstable["linkage_decision"] == "preserve"
    assert unstable["coordination_action"] == "shrinkage_repair"

    safe = decisions["default_preserve_weighted_safety"]
    assert safe["shared_variable_owner"] == "multi_owner"
    assert safe["linkage_decision"] == "preserve"
    assert safe["coordination_action"] == "weighted_consensus"


def test_stage8_32_designs_guarded_repair_without_objective_llm_or_cec(tmp_path) -> None:
    from loco.coordination.overcorrection_guard_design import (
        run_stage8_32_overcorrection_guard_design,
    )

    report = run_stage8_32_overcorrection_guard_design(
        stage8_31_failure_diagnosis_path=STAGE8_31_DIR
        / "failure_diagnosis_report.json",
        stage8_31_overcorrection_path=STAGE8_31_DIR
        / "overcorrection_diagnosis.json",
        stage8_31_branch_usage_path=STAGE8_31_DIR
        / "branch_usage_diagnosis.json",
        stage8_31_fe_ledger_path=STAGE8_31_DIR / "fe_ledger.json",
        stage8_31_runtime_boundary_path=STAGE8_31_DIR / "runtime_boundary.json",
        stage8_31_next_route_path=STAGE8_31_DIR / "next_route_decision.json",
        output_dir=tmp_path,
    )

    assert report["stage"] == "8.32"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "8.31"
    assert report["repair_scope"] == "overcorrection_guard_design_only"
    assert report["repair_policy_id"] == "stage8_32_guarded_owner_trust_repair_v1"
    assert report["overcorrection_guard_designed"] is True
    assert report["best_reward_reliable_path_preserved"] is True
    assert report["owner_conflict_break_path_guarded"] is True
    assert report["unstable_uncertain_preserve_path_defined"] is True
    assert report["default_preserve_safety_path_defined"] is True
    assert report["stage8_31_overcorrection_confirmed"] is True
    assert report["stage8_31_overcorrection_type"] == (
        "contribution_leader_break_overcorrection"
    )
    assert report["objective_loop_executed"] is False
    assert report["new_objective_evaluation_used"] is False
    assert report["cec_checkpoint_executed"] is False
    assert report["FE_total"] == 0
    assert report["inherited_stage8_31_FE_total"] == 0
    assert report["formal_25_run_recommended_now"] is False
    assert report["recommended_next_stage"] == "Stage 8.33"
    assert report["recommended_next_work"] == "static_guard_sanity_or_bounded_checkpoint_gate"

    for flag in [
        "llm_call_used",
        "new_candidate_generation_used",
        "new_llm_strategy_generation_used",
        "selected_policy_revision_used",
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

    policy = json.loads((tmp_path / "guarded_policy_payload.json").read_text())
    guard = json.loads((tmp_path / "overcorrection_guard_spec.json").read_text())
    coverage = json.loads((tmp_path / "static_guard_coverage_report.json").read_text())
    claim = json.loads((tmp_path / "claim_boundary_report.json").read_text())
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())

    assert policy["strategy_id"] == report["repair_policy_id"]
    assert policy["family"] == "conditional_owner_trust_overcorrection_guard"
    assert len(policy["rules"]) == 4
    assert policy["rules"][0]["condition"] == "best_reward_reliable"
    assert policy["rules"][0]["shared_variable_owner"] == "best_reward_group"
    assert policy["rules"][0]["linkage_decision"] == "preserve"
    assert policy["rules"][0]["coordination_action"] == "trust_best_reward"
    assert policy["rules"][1]["condition"] == (
        "strong_owner_conflict AND best_reward_misleading"
    )
    assert policy["rules"][1]["shared_variable_owner"] == "contribution_leader"
    assert policy["rules"][1]["linkage_decision"] == "break"
    assert policy["rules"][1]["coordination_action"] == "owner_proposal_select"

    assert guard["guarded_against_overcorrection"] is True
    assert guard["previous_failure_mode"] == "contribution_leader_break_overcorrection"
    assert guard["forbidden_degenerate_pattern"] == "always_contribution_leader_break"
    assert coverage["all_required_guard_paths_covered"] is True
    assert coverage["branch_counts"]["trust_best_reward"] >= 1
    assert coverage["branch_counts"]["owner_proposal_select"] >= 1
    assert coverage["branch_counts"]["shrinkage_repair"] >= 1
    assert coverage["branch_counts"]["weighted_consensus"] >= 1
    assert coverage["owner_counts"]["best_reward_group"] >= 1
    assert coverage["owner_counts"]["contribution_leader"] >= 1
    assert coverage["linkage_decision_counts"]["preserve"] >= 3
    assert coverage["linkage_decision_counts"]["break"] == 1
    assert claim["policy_repair_selected_for_objective_run"] is False
    assert claim["sota_claim_allowed"] is False
    assert ledger["FE_total"] == 0
    assert boundary["objective_loop_executed"] is False
    assert boundary["cec_checkpoint_executed"] is False
    assert boundary["forbidden_behaviors"]["llm_call"] is False
    assert route["next_stage"] == "Stage 8.33"
    assert route["run_full_25_run_panel_next"] is False
    assert route["run_cec_checkpoint_next"] is False


def test_stage8_32_committed_artifacts_docs_and_readme_record_guard_design() -> None:
    required = [
        CONFIG,
        REPORT,
        POLICY,
        GUARD_SPEC,
        COVERAGE,
        CLAIM_BOUNDARY,
        FE_LEDGER,
        RUNTIME_BOUNDARY,
        NEXT_ROUTE,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    guard = json.loads(GUARD_SPEC.read_text(encoding="utf-8"))
    coverage = json.loads(COVERAGE.read_text(encoding="utf-8"))
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))
    route = json.loads(NEXT_ROUTE.read_text(encoding="utf-8"))

    assert report["stage"] == "8.32"
    assert report["status"] == "PASS"
    assert report["overcorrection_guard_designed"] is True
    assert policy["strategy_id"] == "stage8_32_guarded_owner_trust_repair_v1"
    assert guard["guarded_against_overcorrection"] is True
    assert coverage["all_required_guard_paths_covered"] is True
    assert ledger["FE_total"] == 0
    assert route["next_stage"] == "Stage 8.33"

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Current repository state: `Stage 8.33 PASS`" in combined
    assert "Stage 8.32   overcorrection guard / conditional owner-trust repair" in combined
    assert "stage8_32_guarded_owner_trust_repair_v1" in combined
    assert "best_reward_reliable" in combined
    assert "strong_owner_conflict AND best_reward_misleading" in combined
    assert "trust_best_reward / preserve / best_reward_group" in combined
    assert "FE_total = 0" in combined
    assert "objective_loop_executed = false" in combined
    assert "cec_checkpoint_executed = false" in combined
    assert "not a final objective-value performance claim" in combined
    assert "not a SOTA claim" in combined
