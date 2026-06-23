import json
from pathlib import Path


ROOT = Path("E:/llm_cc")
STAGE8_25_DIR = ROOT / "artifacts" / "analysis" / "stage8_25"
OUTPUT_DIR = ROOT / "artifacts" / "analysis" / "stage8_26"
CONFIG = ROOT / "configs" / "stage8_26_mvp_strategy_dsl.yaml"
REPORT = OUTPUT_DIR / "stage8_26_report.json"
DSL_MANIFEST = OUTPUT_DIR / "strategy_dsl_manifest.json"
BEHAVIOR_EQUIVALENCE = OUTPUT_DIR / "behavior_equivalence_report.json"
BRANCH_COVERAGE = OUTPUT_DIR / "branch_coverage_report.json"
OWNERSHIP_COVERAGE = OUTPUT_DIR / "ownership_decision_coverage_report.json"
TRAIN_WIN_LOSS = OUTPUT_DIR / "train_side_win_loss_report.json"
SEARCH_TRACE = OUTPUT_DIR / "synthetic_search_trace.jsonl"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
NEXT_ROUTE = OUTPUT_DIR / "next_route_decision.json"
STAGE_DOC = ROOT / "docs" / "stage8" / "stage8_26_mvp_strategy_dsl.md"
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_26_self_check_report.md"
README = ROOT / "README.md"


def _best_reward_equivalent_strategy() -> dict:
    return {
        "schema_version": "loco.stage8_26_ownership_aware_strategy_program.v1",
        "strategy_id": "always_trust_best_reward",
        "origin": "unit_test",
        "family": "best_reward_collapse",
        "rules": [
            {
                "condition": "always",
                "shared_variable_owner": "best_reward_group",
                "allow_multi_assignment": False,
                "linkage_decision": "preserve",
                "coordination_action": "trust_best_reward",
                "fallback_repair_action": "weighted_consensus",
            }
        ],
    }


def _ownership_aware_strategy() -> dict:
    return {
        "schema_version": "loco.stage8_26_ownership_aware_strategy_program.v1",
        "strategy_id": "ownership_conflict_guard_v1",
        "origin": "unit_test",
        "family": "ownership_aware_conflict_guard",
        "rules": [
            {
                "condition": "conflicting_overlap AND high_owner_regret",
                "shared_variable_owner": "contribution_leader",
                "allow_multi_assignment": False,
                "linkage_decision": "break",
                "coordination_action": "owner_proposal_select",
                "fallback_repair_action": "shrinkage_repair",
            },
            {
                "condition": "conforming_overlap AND high_owner_agreement",
                "shared_variable_owner": "multi_owner",
                "allow_multi_assignment": True,
                "linkage_decision": "preserve",
                "coordination_action": "multi_owner_weighted_vote",
                "fallback_repair_action": "weighted_consensus",
            },
            {
                "condition": "unstable_best_reward",
                "shared_variable_owner": "historical_owner",
                "allow_multi_assignment": False,
                "linkage_decision": "preserve",
                "coordination_action": "reject_unstable_best_reward",
                "fallback_repair_action": "simple_consensus",
            },
            {
                "condition": "always",
                "shared_variable_owner": "best_reward_group",
                "allow_multi_assignment": False,
                "linkage_decision": "preserve",
                "coordination_action": "trust_best_reward",
                "fallback_repair_action": "weighted_consensus",
            },
        ],
    }


def test_stage8_26_loads_dsl_and_rejects_best_reward_equivalent_strategy() -> None:
    from loco.coordination.ownership_aware_strategy_dsl import (
        evaluate_strategy_program,
        load_strategy_program,
    )

    collapsed = load_strategy_program(_best_reward_equivalent_strategy())
    ownership_aware = load_strategy_program(_ownership_aware_strategy())

    collapsed_report = evaluate_strategy_program(collapsed)
    ownership_report = evaluate_strategy_program(ownership_aware)

    assert collapsed_report["behavior_equivalence_report"][
        "equivalent_to_best_reward_select"
    ] is True
    assert collapsed_report["behavior_equivalence_report"][
        "not_equivalent_to_best_reward_select"
    ] is False
    assert collapsed_report["branch_coverage_report"]["non_trust_branch_exercised"] is False
    assert collapsed_report["ownership_decision_coverage_report"][
        "ownership_or_linkage_decision_exercised"
    ] is False

    assert ownership_report["behavior_equivalence_report"][
        "not_equivalent_to_best_reward_select"
    ] is True
    assert ownership_report["branch_coverage_report"]["non_trust_branch_exercised"] is True
    assert ownership_report["ownership_decision_coverage_report"][
        "ownership_or_linkage_decision_exercised"
    ] is True
    assert ownership_report["gate_passed"] is True
    assert ownership_report["train_side_win_loss_report"]["win_count_vs_best_reward"] >= 1
    assert ownership_report["train_side_win_loss_report"]["loss_count_vs_best_reward"] == 0
    assert ownership_report["FE_total"] == 0


def test_stage8_26_runs_small_synthetic_search_and_writes_contract_artifacts(tmp_path) -> None:
    from loco.coordination.ownership_aware_strategy_dsl import (
        run_stage8_26_mvp_strategy_dsl,
    )

    report = run_stage8_26_mvp_strategy_dsl(
        stage8_25_report_path=STAGE8_25_DIR / "stage8_25_report.json",
        stage8_25_dsl_contract_path=STAGE8_25_DIR
        / "ownership_aware_strategy_dsl_contract.json",
        stage8_25_fe_ledger_path=STAGE8_25_DIR / "fe_ledger.json",
        stage8_25_runtime_boundary_path=STAGE8_25_DIR / "runtime_boundary.json",
        stage8_25_next_route_path=STAGE8_25_DIR / "next_route_decision.json",
        output_dir=tmp_path,
    )

    assert report["stage"] == "8.26"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "8.25"
    assert report["mvp_strategy_dsl_implemented"] is True
    assert report["behavior_equivalence_checker_implemented"] is True
    assert report["synthetic_conflict_regime_search_executed"] is True
    assert report["selected_strategy_id"] == "ownership_conflict_guard_v1"
    assert report["selected_strategy_not_equivalent_to_best_reward_select"] is True
    assert report["non_trust_branch_exercised"] is True
    assert report["ownership_or_linkage_decision_exercised"] is True
    assert report["train_side_win_count_vs_best_reward"] >= 1
    assert report["train_side_loss_count_vs_best_reward"] == 0
    assert report["FE_total"] == 0
    assert report["objective_loop_executed"] is False
    assert report["new_objective_evaluation_used"] is False
    assert report["llm_call_used"] is False
    assert report["new_candidate_generation_used"] is False
    assert report["not_sota_claim"] is True
    assert report["not_final_performance_claim"] is True
    assert report["recommended_next_stage"] == "Stage 8.27"

    required = [
        "strategy_dsl_manifest.json",
        "behavior_equivalence_report.json",
        "branch_coverage_report.json",
        "ownership_decision_coverage_report.json",
        "train_side_win_loss_report.json",
        "synthetic_search_trace.jsonl",
        "fe_ledger.json",
        "runtime_boundary.json",
        "next_route_decision.json",
        "stage8_26_report.json",
    ]
    for filename in required:
        assert (tmp_path / filename).is_file(), filename

    manifest = json.loads((tmp_path / "strategy_dsl_manifest.json").read_text())
    equivalence = json.loads((tmp_path / "behavior_equivalence_report.json").read_text())
    branch = json.loads((tmp_path / "branch_coverage_report.json").read_text())
    ownership = json.loads(
        (tmp_path / "ownership_decision_coverage_report.json").read_text()
    )
    win_loss = json.loads((tmp_path / "train_side_win_loss_report.json").read_text())
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())
    trace_rows = [
        json.loads(line)
        for line in (tmp_path / "synthetic_search_trace.jsonl").read_text().splitlines()
        if line.strip()
    ]

    assert manifest["target_scope"] == "shared_variables_and_decomposition_consequences"
    assert "shared_variable_owner" in manifest["allowed_outputs"]
    assert "multi_owner_weighted_vote" in manifest["allowed_coordination_actions"]
    assert manifest["strategy_count"] >= 3
    assert equivalence["selected_strategy_id"] == "ownership_conflict_guard_v1"
    assert equivalence["not_equivalent_to_best_reward_select"] is True
    assert branch["non_trust_branch_exercised"] is True
    assert ownership["ownership_or_linkage_decision_exercised"] is True
    assert win_loss["win_count_vs_best_reward"] >= 1
    assert win_loss["loss_count_vs_best_reward"] == 0
    assert len(trace_rows) >= 9
    assert ledger["FE_total"] == 0
    assert boundary["objective_loop_executed"] is False
    assert boundary["llm_call_used"] is False
    assert route["next_stage"] == "Stage 8.27"


def test_stage8_26_committed_artifacts_docs_and_readme_record_mvp_dsl() -> None:
    required = [
        CONFIG,
        REPORT,
        DSL_MANIFEST,
        BEHAVIOR_EQUIVALENCE,
        BRANCH_COVERAGE,
        OWNERSHIP_COVERAGE,
        TRAIN_WIN_LOSS,
        SEARCH_TRACE,
        FE_LEDGER,
        RUNTIME_BOUNDARY,
        NEXT_ROUTE,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    manifest = json.loads(DSL_MANIFEST.read_text(encoding="utf-8"))
    equivalence = json.loads(BEHAVIOR_EQUIVALENCE.read_text(encoding="utf-8"))
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))
    route = json.loads(NEXT_ROUTE.read_text(encoding="utf-8"))

    assert report["stage"] == "8.26"
    assert report["status"] == "PASS"
    assert manifest["mvp_strategy_dsl_implemented"] is True
    assert equivalence["not_equivalent_to_best_reward_select"] is True
    assert ledger["FE_total"] == 0
    assert route["next_stage"] == "Stage 8.27"

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Current repository state: `Stage 8.33 PASS`" in combined
    assert "Stage 8.26   MVP strategy DSL and behavior-equivalence checker" in combined
    assert "ownership-aware strategy DSL" in combined
    assert "behavior-equivalence checker" in combined
    assert "not equivalent to best_reward_select" in combined
    assert "Stage 8.27" in combined
    assert "not a final objective-value performance claim" in combined
    assert "not a SOTA claim" in combined
