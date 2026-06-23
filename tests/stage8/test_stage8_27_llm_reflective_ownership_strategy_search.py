import json
from pathlib import Path

from loco.llm.provider_client import ChatCompletionResult


ROOT = Path("E:/llm_cc")
STAGE8_26_DIR = ROOT / "artifacts" / "analysis" / "stage8_26"
OUTPUT_DIR = ROOT / "artifacts" / "selection_audit" / "stage8_27"
CONFIG = ROOT / "configs" / "stage8_27_llm_reflective_ownership_strategy_search.yaml"
REPORT = OUTPUT_DIR / "llm_reflective_ownership_strategy_search_report.json"
API_PREFLIGHT = OUTPUT_DIR / "api_preflight_report.json"
PROMPT_CONTEXT = OUTPUT_DIR / "reflection_prompt_context.json"
REFLECTION_ROUNDS = OUTPUT_DIR / "reflection_rounds.jsonl"
RAW_STRATEGIES = OUTPUT_DIR / "raw_llm_strategies.jsonl"
ACCEPTED_STRATEGIES = OUTPUT_DIR / "accepted_strategies.jsonl"
REJECTED_STRATEGIES = OUTPUT_DIR / "rejected_strategies.jsonl"
STATIC_AUDIT = OUTPUT_DIR / "static_audit_report.json"
EVALUATOR_REPORT = OUTPUT_DIR / "strategy_evaluator_report.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
NEXT_ROUTE = OUTPUT_DIR / "next_route_decision.json"
STAGE_DOC = ROOT / "docs" / "stage8" / "stage8_27_llm_reflective_ownership_strategy_search.md"
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_27_self_check_report.md"
README = ROOT / "README.md"


def _strategy_batch(round_index: int) -> str:
    strategies = []
    for index in range(6):
        strategy_id = f"stage8_27_r{round_index}_ownership_{index}"
        strategies.append(
            {
                "schema_version": "loco.stage8_26_ownership_aware_strategy_program.v1",
                "strategy_id": strategy_id,
                "origin": "llm_reflective_generated",
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
        )
    return json.dumps(
        {
            "schema_version": "loco.stage8_27_raw_strategy_batch.v1",
            "stage": "8.27",
            "source": {
                "provider": "unit_fake",
                "model": "unit-fake-ownership-reflector",
                "captured_by": "Stage 8.27 injected unit provider",
            },
            "strategies": strategies,
        }
    )


class FakeOwnershipReflectiveProvider:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, *, messages, temperature):
        self.calls += 1
        return ChatCompletionResult(
            content=_strategy_batch(self.calls),
            raw_response={"choices": [{"message": {"content": "<omitted>"}}]},
            sanitized_response={"choices": [{"message": {"content": "<omitted>"}}]},
            provenance={
                "base_url_host": "unit.fake.local",
                "model": "unit-fake-ownership-reflector",
                "wire_api": "chat",
                "reasoning_effort": "high",
                "endpoint_path": "/chat/completions",
            },
        )


def _jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_stage8_27_blocks_without_real_llm_api_and_does_not_fake_strategies(tmp_path) -> None:
    from loco.coordination.llm_reflective_ownership_strategy_search import (
        run_stage8_27_llm_reflective_ownership_strategy_search,
    )

    report = run_stage8_27_llm_reflective_ownership_strategy_search(
        stage8_26_report_path=STAGE8_26_DIR / "stage8_26_report.json",
        stage8_26_manifest_path=STAGE8_26_DIR / "strategy_dsl_manifest.json",
        stage8_26_equivalence_path=STAGE8_26_DIR / "behavior_equivalence_report.json",
        stage8_26_fe_ledger_path=STAGE8_26_DIR / "fe_ledger.json",
        stage8_26_runtime_boundary_path=STAGE8_26_DIR / "runtime_boundary.json",
        stage8_26_next_route_path=STAGE8_26_DIR / "next_route_decision.json",
        output_dir=tmp_path,
        env_path=tmp_path / "missing.env",
    )

    assert report["stage"] == "8.27"
    assert report["status"] == "BLOCKED_NEEDS_REAL_LLM_API"
    assert report["llm_call_used"] is False
    assert report["real_llm_api_called"] is False
    assert report["new_llm_strategy_generation_used"] is False
    assert report["fake_llm_strategies_used"] is False
    assert report["raw_llm_strategy_count"] == 0
    assert report["accepted_strategy_count"] == 0
    assert report["objective_loop_executed"] is False
    assert report["new_objective_evaluation_used"] is False
    assert report["FE_total"] == 0

    preflight = json.loads((tmp_path / "api_preflight_report.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())

    assert preflight["status"] == "BLOCKED_NEEDS_REAL_LLM_API"
    assert preflight["real_llm_api_available"] is False
    assert "LLM_API_KEY" in preflight["missing_or_invalid"]
    assert boundary["fake_llm_strategies_used"] is False
    assert route["next_route"] == "WAIT_FOR_REAL_LLM_API"


def test_stage8_27_executes_reflective_search_with_injected_provider_for_unit_test(
    tmp_path,
) -> None:
    from loco.coordination.llm_reflective_ownership_strategy_search import (
        run_stage8_27_llm_reflective_ownership_strategy_search,
    )

    fake_provider = FakeOwnershipReflectiveProvider()
    report = run_stage8_27_llm_reflective_ownership_strategy_search(
        stage8_26_report_path=STAGE8_26_DIR / "stage8_26_report.json",
        stage8_26_manifest_path=STAGE8_26_DIR / "strategy_dsl_manifest.json",
        stage8_26_equivalence_path=STAGE8_26_DIR / "behavior_equivalence_report.json",
        stage8_26_fe_ledger_path=STAGE8_26_DIR / "fe_ledger.json",
        stage8_26_runtime_boundary_path=STAGE8_26_DIR / "runtime_boundary.json",
        stage8_26_next_route_path=STAGE8_26_DIR / "next_route_decision.json",
        output_dir=tmp_path,
        env_path=tmp_path / "unused.env",
        chat_caller=fake_provider,
        injected_provider_is_test_double=True,
    )

    assert report["stage"] == "8.27"
    assert report["status"] == "PASS"
    assert report["reflection_round_count"] == 2
    assert report["raw_llm_strategy_count"] == 12
    assert report["accepted_strategy_count"] == 12
    assert report["selected_strategy_origin"] == "llm_reflective_generated"
    assert report["selected_strategy_not_equivalent_to_best_reward_select"] is True
    assert report["non_trust_branch_exercised"] is True
    assert report["ownership_or_linkage_decision_exercised"] is True
    assert report["train_side_win_count_vs_best_reward"] >= 1
    assert report["train_side_loss_count_vs_best_reward"] == 0
    assert report["llm_call_used"] is False
    assert report["real_llm_api_called"] is False
    assert report["unit_test_injected_provider_used"] is True
    assert report["fake_llm_strategies_used"] is False
    assert report["FE_total"] == 0
    assert fake_provider.calls == 2

    rounds = _jsonl(tmp_path / "reflection_rounds.jsonl")
    raw = _jsonl(tmp_path / "raw_llm_strategies.jsonl")
    accepted = _jsonl(tmp_path / "accepted_strategies.jsonl")
    evaluator = json.loads((tmp_path / "strategy_evaluator_report.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())

    assert len(rounds) == 2
    assert rounds[1]["feedback_from_previous_round"]["evaluated_strategy_count"] > 0
    assert len(raw) == 12
    assert len(accepted) == 12
    assert evaluator["selected_strategy_id"] == report["selected_strategy_id"]
    assert route["next_stage"] == "Stage 8.28"


def test_stage8_27_committed_artifacts_docs_and_readme_record_execution_or_blocked_state() -> None:
    required = [
        CONFIG,
        REPORT,
        API_PREFLIGHT,
        PROMPT_CONTEXT,
        REFLECTION_ROUNDS,
        RAW_STRATEGIES,
        ACCEPTED_STRATEGIES,
        REJECTED_STRATEGIES,
        STATIC_AUDIT,
        EVALUATOR_REPORT,
        FE_LEDGER,
        RUNTIME_BOUNDARY,
        NEXT_ROUTE,
        STAGE_DOC,
        SELF_CHECK,
    ]
    for path in required:
        assert path.is_file(), path

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    preflight = json.loads(API_PREFLIGHT.read_text(encoding="utf-8"))
    boundary = json.loads(RUNTIME_BOUNDARY.read_text(encoding="utf-8"))

    assert report["stage"] == "8.27"
    assert report["status"] in {"PASS", "BLOCKED_NEEDS_REAL_LLM_API"}
    assert report["fake_llm_strategies_used"] is False
    assert preflight["secret_redacted"] is True
    assert boundary["not_sota_claim"] is True
    assert boundary["not_final_performance_claim"] is True

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Current repository state: `Stage 8.28" in combined
    assert "Stage 8.27   real LLM reflective ownership-aware strategy search" in combined
    assert "ownership-aware strategy programs" in combined
    assert "fake LLM strategies are forbidden" in combined
    assert "not a SOTA claim" in combined
    assert "not a final objective-value performance claim" in combined
