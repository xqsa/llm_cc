import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "stage7_5_sota_protocol.yaml"
STAGE7_4_DECISION = (
    ROOT / "artifacts" / "objective_eval" / "stage7_4" / "cec2013_panel_decision.json"
)
STAGE7_4_PROTOCOL = (
    ROOT
    / "artifacts"
    / "objective_eval"
    / "stage7_4"
    / "cec2013_optional_panel_protocol.json"
)
STAGE7_3_RANKING = (
    ROOT / "artifacts" / "objective_eval" / "stage7_3" / "method_ranking.json"
)
OUTPUT_DIR = ROOT / "artifacts" / "objective_eval" / "stage7_5"
REPORT = OUTPUT_DIR / "sota_protocol_report.json"
ADMISSIBILITY = OUTPUT_DIR / "comparator_admissibility_rules.json"
REUSE_POLICY = OUTPUT_DIR / "reported_results_reuse_policy.json"
CLAIM_CONTRACT = OUTPUT_DIR / "benchmark_claim_contract.json"
NEXT_DECISION = OUTPUT_DIR / "next_route_decision.json"
STAGE_DOC = ROOT / "docs" / "stage7" / "stage7_5_sota_protocol.md"
SELF_CHECK = ROOT / "docs" / "stage7" / "stage7_5_self_check_report.md"
README = ROOT / "README.md"


def test_stage7_5_locks_sota_protocol_without_running_objectives(tmp_path) -> None:
    from loco.coordination.sota_protocol_lock import run_stage7_5_sota_protocol

    report = run_stage7_5_sota_protocol(
        stage7_4_decision_path=STAGE7_4_DECISION,
        stage7_4_protocol_path=STAGE7_4_PROTOCOL,
        stage7_3_ranking_path=STAGE7_3_RANKING,
        output_dir=tmp_path,
    )

    assert report["stage"] == "7.5"
    assert report["status"] == "PASS"
    assert report["source_stage"] == "7.4"
    assert report["protocol_scope"] == "sota_targeted_real_benchmark_protocol_lock"
    assert report["official_cec2013_setting_locked"] is True
    assert report["official_run_count"] == 25
    assert report["official_max_fe"] == 3_000_000
    assert report["reported_results_reuse_allowed"] is True
    assert report["reported_results_direct_comparison_requires_same_setting"] is True
    assert report["f13_f14_only_not_full_sota"] is True
    assert report["current_selected_operator_rank_overall"] == 4
    assert report["current_selected_operator_not_sota_ready"] is True
    assert report["new_objective_evaluation_used"] is False
    assert report["cec2013_panel_run"] is False
    assert report["sota_claim_made"] is False
    assert (
        report["next_status"] == "READY_FOR_STAGE7_6_REPORTED_RESULTS_COMPARATOR_AUDIT"
    )

    admissibility = json.loads(
        (tmp_path / "comparator_admissibility_rules.json").read_text(encoding="utf-8")
    )
    reuse_policy = json.loads(
        (tmp_path / "reported_results_reuse_policy.json").read_text(encoding="utf-8")
    )
    claim_contract = json.loads(
        (tmp_path / "benchmark_claim_contract.json").read_text(encoding="utf-8")
    )
    route = json.loads(
        (tmp_path / "next_route_decision.json").read_text(encoding="utf-8")
    )

    required_fields = {
        "benchmark_suite",
        "function_ids",
        "max_fe",
        "run_count",
        "statistic",
        "objective_implementation",
        "dimension_semantics",
        "same_budget",
        "source_citation",
    }
    assert required_fields.issubset(admissibility["required_direct_comparison_fields"])
    assert admissibility["official_cec2013_lsgo"]["function_count"] == 15
    assert admissibility["official_cec2013_lsgo"]["run_count"] == 25
    assert admissibility["official_cec2013_lsgo"]["max_fe"] == 3_000_000
    assert admissibility["official_cec2013_lsgo"]["dimension"] == 1000
    assert admissibility["f13_f14_panel"]["allowed_claim_tier"] == "T1"
    assert admissibility["f13_f14_panel"]["forbidden_claim_tier"] == "T3"

    assert reuse_policy["reported_results_reuse_allowed"] is True
    assert reuse_policy["direct_comparison_requires_same_setting"] is True
    assert reuse_policy["unknown_or_mismatched_setting_policy"] == "background_only"
    assert "paper_table_values_not_extracted_in_stage7_5" in reuse_policy["limits"]
    assert "source_citation" in reuse_policy["must_record"]

    tiers = {tier["tier_id"]: tier for tier in claim_contract["claim_tiers"]}
    assert tiers["T0"]["sota_claim_allowed"] is False
    assert tiers["T1"]["scope"] == "overlap_focused_f13_f14_panel"
    assert tiers["T1"]["full_cec2013_sota_claim_allowed"] is False
    assert tiers["T3"]["scope"] == "full_or_sota_cec2013_lsgo_claim"
    assert tiers["T3"]["requires_admissible_comparators"] is True
    assert claim_contract["current_selected_operator"]["overall_rank"] == 4
    assert claim_contract["current_selected_operator"]["final_sota_candidate"] is False

    assert route["decision"] == "LOCK_SOTA_PROTOCOL_AND_AUDIT_REPORTED_RESULTS"
    assert route["next_stage"] == "Stage 7.6"
    assert route["allowed_next_work"] == "reported_results_comparator_audit"
    assert route["run_cec2013_panel_now"] is False


def test_stage7_5_committed_artifacts_docs_and_readme_record_protocol() -> None:
    required = [
        CONFIG,
        REPORT,
        ADMISSIBILITY,
        REUSE_POLICY,
        CLAIM_CONTRACT,
        NEXT_DECISION,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    admissibility = json.loads(ADMISSIBILITY.read_text(encoding="utf-8"))
    reuse_policy = json.loads(REUSE_POLICY.read_text(encoding="utf-8"))
    claim_contract = json.loads(CLAIM_CONTRACT.read_text(encoding="utf-8"))
    route = json.loads(NEXT_DECISION.read_text(encoding="utf-8"))

    assert report["status"] == "PASS"
    assert report["official_max_fe"] == 3_000_000
    assert admissibility["official_cec2013_lsgo"]["run_count"] == 25
    assert reuse_policy["direct_comparison_requires_same_setting"] is True
    assert claim_contract["f13_f14_only_not_full_sota"] is True
    assert route["next_stage"] == "Stage 7.6"

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Current repository state: `Stage 7.5 PASS`" in combined
    assert (
        "Stage 7.5    SOTA-targeted real benchmark protocol lock             PASS"
        in combined
    )
    assert "Stage 7.6" in combined
    assert "reported-results comparator audit" in combined
    assert "reported_results_reuse_policy.json" in combined
    assert "MaxFEs = 3e6" in combined
    assert "25 runs" in combined
    assert "F13/F14-only is not full CEC2013 LSGO SOTA" in combined
    assert "not a SOTA claim" in combined
    assert "no new objective evaluation" in combined
    assert "current selected LOCO operator is not SOTA-ready" in combined
