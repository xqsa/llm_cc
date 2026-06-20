import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DECISION_PATH = ROOT / "artifacts" / "readiness" / "stage2_10_readiness_decision.json"


def test_stage2_10_committed_readiness_decision_allows_stage3_with_boundaries() -> None:
    decision = json.loads(DECISION_PATH.read_text(encoding="utf-8"))

    assert decision["schema_version"] == "loco.pre_stage3_readiness.v1"
    assert decision["stage"] == "2.10"
    assert decision["decision"] == "READY_FOR_STAGE3_BOUNDARY_ONLY"
    assert decision["stage3_allowed"] is True
    assert (
        decision["stage3_allowed_scope"]
        == "LLM/evolution search over typed coordination operator ASTs only"
    )
    assert decision["stage3_forbidden_scope"] == [
        "optimizer generation",
        "BaseOpt modification",
        "scheduler/controller generation",
        "optimizer selection",
        "benchmark objective rewrite",
        "test feedback access",
        "test-set tuning",
        "untyped executable code generation",
    ]
    assert decision["required_pass_gates"] == [
        "stage2_7_sealed_split_replay_audit",
        "stage2_8_frozen_candidate_promotion_contract",
        "stage2_9_promotion_replay_and_registry_audit",
    ]
    assert decision["evidence"]["stage2_7"]["status"] == "PASS"
    assert decision["evidence"]["stage2_8"]["registry_entry_count"] == 1
    assert decision["evidence"]["stage2_9"]["status"] == "PASS"
    assert decision["known_risks"]["real_metabox_smoke_status"] in {
        "PASS",
        "PARTIAL",
        "OPTIONAL_SKIP",
    }
    assert decision["not_performance_claim"] is True
    assert decision["no_llm"] is True
    assert decision["no_evolution"] is True
    assert decision["no_optimizer"] is True
    assert decision["no_candidate_generation"] is True
    assert decision["no_test_feedback"] is True
    assert decision["no_objective_evaluation"] is True


def test_stage2_10_gate_recomputes_readiness_from_committed_artifacts(tmp_path) -> None:
    from loco.coordination.pre_stage3_readiness import evaluate_pre_stage3_readiness

    decision = evaluate_pre_stage3_readiness(
        decision_path=tmp_path / "stage2_10_readiness_decision.json"
    )

    assert decision["decision"] == "READY_FOR_STAGE3_BOUNDARY_ONLY"
    assert decision["stage3_allowed"] is True
    assert decision["evidence"]["stage2_9"]["status"] == "PASS"
    assert (tmp_path / "stage2_10_readiness_decision.json").is_file()


def test_stage2_10_gate_blocks_when_stage2_9_audit_fails(tmp_path) -> None:
    from loco.coordination.pre_stage3_readiness import evaluate_pre_stage3_readiness

    failing_report = tmp_path / "promotion_replay_audit_report.json"
    source = (
        ROOT
        / "artifacts"
        / "operators"
        / "stage2_9"
        / "promotion_replay_audit_report.json"
    )
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["status"] = "FAIL"
    payload["promotion_fingerprint_mismatch_count"] = 1
    failing_report.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    decision = evaluate_pre_stage3_readiness(
        stage2_9_audit_report_path=failing_report,
        decision_path=tmp_path / "blocked_readiness_decision.json",
    )

    assert decision["decision"] == "BLOCK_STAGE3"
    assert decision["stage3_allowed"] is False
    assert "stage2_9_promotion_replay_and_registry_audit" in decision["blocking_gates"]


def test_stage2_10_docs_and_config_state_boundaries() -> None:
    required = [
        ROOT / "configs" / "stage2_10_pre_stage3_readiness.yaml",
        ROOT / "docs" / "stage2" / "stage2_10_pre_stage3_readiness.md",
        ROOT / "docs" / "stage2" / "stage2_10_self_check_report.md",
        DECISION_PATH,
    ]
    for path in required:
        assert path.is_file(), path

    combined = "\n".join(path.read_text(encoding="utf-8") for path in required)
    assert "pre-Stage-3 readiness gate" in combined
    assert "READY_FOR_STAGE3_BOUNDARY_ONLY" in combined
    assert "no LLM" in combined
    assert "no evolution" in combined
    assert "no optimizer" in combined
    assert "no candidate generation" in combined
    assert "no test feedback" in combined
    assert "no objective evaluation" in combined
    assert "not a performance claim" in combined


def test_stage2_10_gate_does_not_import_llm_or_evolution_modules(tmp_path) -> None:
    forbidden_loaded_before = {
        name
        for name in sys.modules
        if name.startswith(("openai", "anthropic", "google.generativeai", "deap"))
    }

    from loco.coordination.pre_stage3_readiness import evaluate_pre_stage3_readiness

    evaluate_pre_stage3_readiness(
        decision_path=tmp_path / "stage2_10_readiness_decision.json"
    )

    forbidden_loaded_after = {
        name
        for name in sys.modules
        if name.startswith(("openai", "anthropic", "google.generativeai", "deap"))
    }
    assert forbidden_loaded_after == forbidden_loaded_before
