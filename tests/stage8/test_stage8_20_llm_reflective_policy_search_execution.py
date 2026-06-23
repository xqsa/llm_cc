import json
from pathlib import Path

from loco.llm.provider_client import ChatCompletionResult


ROOT = Path("E:/llm_cc")
CONFIG = ROOT / "configs" / "stage8_20_llm_reflective_policy_search_execution.yaml"
STAGE8_19_DIR = ROOT / "artifacts" / "selection_audit" / "stage8_19"
OUTPUT_DIR = ROOT / "artifacts" / "selection_audit" / "stage8_20"
REPORT = OUTPUT_DIR / "llm_reflective_search_report.json"
API_PREFLIGHT = OUTPUT_DIR / "api_preflight_report.json"
PROMPT_CONTEXT = OUTPUT_DIR / "reflection_prompt_context.json"
REFLECTION_ROUNDS = OUTPUT_DIR / "reflection_rounds.jsonl"
RAW_CANDIDATES = OUTPUT_DIR / "raw_llm_candidates.jsonl"
ACCEPTED_CANDIDATES = OUTPUT_DIR / "accepted_candidates.jsonl"
REJECTED_CANDIDATES = OUTPUT_DIR / "rejected_candidates.jsonl"
STATIC_AUDIT = OUTPUT_DIR / "static_audit_report.json"
EVALUATOR_REPORT = OUTPUT_DIR / "candidate_evaluator_report.json"
FE_LEDGER = OUTPUT_DIR / "fe_ledger.json"
RUNTIME_BOUNDARY = OUTPUT_DIR / "runtime_boundary.json"
NEXT_ROUTE = OUTPUT_DIR / "next_route_decision.json"
STAGE_DOC = ROOT / "docs" / "stage8" / "stage8_20_llm_reflective_policy_search_execution.md"
SELF_CHECK = ROOT / "docs" / "stage8" / "stage8_20_self_check_report.md"
README = ROOT / "README.md"


def _jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _policy_batch(round_index: int, *, family_offset: int = 0) -> str:
    families = [
        ("margin_weighted", "weighted_consensus", "low_reward_margin"),
        ("conflict_simple", "simple_consensus", "direction_inconsistent"),
        ("oversized_shrink", "shrinkage_repair", "oversized_best_reward"),
        ("outlier_reject", "reject_unstable_best_reward", "best_reward_outlier"),
        ("damp_regret", "damp_best_reward", "recent_best_reward_regret"),
        ("trust_gate", "trust_best_reward", "best_reward_trustworthy"),
        ("oscillation_simple", "simple_consensus", "shared_variable_oscillation"),
        ("dispersion_weighted", "weighted_consensus", "high_proposal_dispersion"),
        ("concentration_trust", "trust_best_reward", "high_reward_concentration"),
        ("low_margin_reject", "reject_unstable_best_reward", "low_reward_margin"),
        ("direction_damp", "damp_best_reward", "direction_inconsistent"),
        ("repair_combo", "shrinkage_repair", "best_reward_outlier"),
    ]
    policies = []
    for index in range(12):
        family, action, condition = families[(index + family_offset) % len(families)]
        policy_id = f"stage8_20_r{round_index}_{family}_{index}"
        rules = [
            {"condition": "best_reward_trustworthy", "action": "trust_best_reward"},
            {"condition": "low_reward_margin", "action": "weighted_consensus"},
            {"condition": "direction_inconsistent", "action": "simple_consensus"},
            {"condition": "oversized_best_reward", "action": "shrinkage_repair"},
            {"condition": condition, "action": action},
            {"condition": "always", "action": "simple_consensus"},
        ]
        policies.append(
            {
                "schema_version": "loco.stage8_20_coordination_policy_program.v1",
                "policy_id": policy_id,
                "origin": "llm_reflective_generated",
                "family": family,
                "target_scope": "shared_variables_only",
                "features": [
                    "reward_margin",
                    "reward_concentration",
                    "conflict_intensity",
                    "proposal_dispersion",
                    "direction_consistency",
                    "shared_variable_oscillation",
                    "recent_best_reward_regret",
                ],
                "memory": ["recent_best_reward_regret"],
                "rules": rules,
                "forbidden_capabilities_used": [],
            }
        )
    return json.dumps(
        {
            "schema_version": "loco.stage8_20_raw_policy_batch.v1",
            "stage": "8.20",
            "source": {
                "provider": "unit_fake",
                "model": "unit-fake-reflector",
                "captured_by": "Stage 8.20 injected unit provider",
            },
            "policies": policies,
        }
    )


class FakeReflectiveProvider:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, *, messages, temperature):
        self.calls += 1
        return ChatCompletionResult(
            content=_policy_batch(self.calls, family_offset=self.calls - 1),
            raw_response={
                "choices": [{"message": {"content": "<omitted>"}}],
                "usage": {"total_tokens": 1000 + self.calls},
            },
            sanitized_response={
                "choices": [{"message": {"content": "<omitted>"}}],
                "usage": {"total_tokens": 1000 + self.calls},
            },
            provenance={
                "base_url_host": "unit.fake.local",
                "model": "unit-fake-reflector",
                "wire_api": "chat",
                "reasoning_effort": "high",
                "endpoint_path": "/chat/completions",
            },
        )


def test_stage8_20_blocks_without_real_llm_api_and_does_not_fake_candidates(tmp_path) -> None:
    from loco.coordination.llm_reflective_policy_search_execution import (
        run_stage8_20_llm_reflective_policy_search_execution,
    )

    report = run_stage8_20_llm_reflective_policy_search_execution(
        stage8_19_design_path=STAGE8_19_DIR / "llm_reflective_policy_search_design.json",
        stage8_19_prompt_contract_path=STAGE8_19_DIR / "reflection_prompt_contract.json",
        stage8_19_dsl_contract_path=STAGE8_19_DIR / "coordination_policy_dsl_contract.json",
        stage8_19_ablation_plan_path=STAGE8_19_DIR / "llm_contribution_ablation_plan.json",
        stage8_19_gate_path=STAGE8_19_DIR / "beat_best_reward_gate.json",
        stage8_19_fe_ledger_path=STAGE8_19_DIR / "fe_ledger.json",
        stage8_19_runtime_boundary_path=STAGE8_19_DIR / "runtime_boundary.json",
        stage8_19_next_route_path=STAGE8_19_DIR / "next_route_decision.json",
        output_dir=tmp_path,
        env_path=tmp_path / "missing.env",
    )

    assert report["stage"] == "8.20"
    assert report["status"] == "BLOCKED_NEEDS_REAL_LLM_API"
    assert report["llm_call_used"] is False
    assert report["real_llm_api_called"] is False
    assert report["new_llm_candidate_generation_used"] is False
    assert report["fake_llm_candidates_used"] is False
    assert report["raw_llm_candidate_count"] == 0
    assert report["quality_pass_candidate_count"] == 0
    assert report["objective_evaluator_feedback_used"] is False
    assert report["objective_loop_executed"] is False
    assert report["new_objective_evaluation_used"] is False
    assert report["FE_total"] == 0
    assert report["not_sota_claim"] is True
    assert report["not_final_performance_claim"] is True

    preflight = json.loads((tmp_path / "api_preflight_report.json").read_text())
    ledger = json.loads((tmp_path / "fe_ledger.json").read_text())
    boundary = json.loads((tmp_path / "runtime_boundary.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())

    assert preflight["status"] == "BLOCKED_NEEDS_REAL_LLM_API"
    assert preflight["real_llm_api_available"] is False
    assert "LLM_API_KEY" in preflight["missing_or_invalid"]
    assert ledger["FE_total"] == 0
    assert ledger["llm_call_used"] is False
    assert boundary["forbidden_behaviors"]["fake_llm_candidate_generation"] is False
    assert route["next_route"] == "WAIT_FOR_REAL_LLM_API"


def test_stage8_20_executes_reflective_search_with_injected_provider_for_unit_test(
    tmp_path,
) -> None:
    from loco.coordination.llm_reflective_policy_search_execution import (
        run_stage8_20_llm_reflective_policy_search_execution,
    )

    fake_provider = FakeReflectiveProvider()
    report = run_stage8_20_llm_reflective_policy_search_execution(
        stage8_19_design_path=STAGE8_19_DIR / "llm_reflective_policy_search_design.json",
        stage8_19_prompt_contract_path=STAGE8_19_DIR / "reflection_prompt_contract.json",
        stage8_19_dsl_contract_path=STAGE8_19_DIR / "coordination_policy_dsl_contract.json",
        stage8_19_ablation_plan_path=STAGE8_19_DIR / "llm_contribution_ablation_plan.json",
        stage8_19_gate_path=STAGE8_19_DIR / "beat_best_reward_gate.json",
        stage8_19_fe_ledger_path=STAGE8_19_DIR / "fe_ledger.json",
        stage8_19_runtime_boundary_path=STAGE8_19_DIR / "runtime_boundary.json",
        stage8_19_next_route_path=STAGE8_19_DIR / "next_route_decision.json",
        output_dir=tmp_path,
        env_path=tmp_path / "unused.env",
        chat_caller=fake_provider,
        injected_provider_is_test_double=True,
    )

    assert report["stage"] == "8.20"
    assert report["status"] == "PASS"
    assert report["reflection_round_count"] == 2
    assert report["raw_llm_candidate_count"] >= 24
    assert report["quality_pass_candidate_count"] >= 8
    assert report["coordination_family_count"] >= 4
    assert report["selected_candidate_origin"] == "llm_reflective_generated"
    assert report["selected_candidate_not_equivalent_to_best_reward"] is True
    assert report["non_trust_best_reward_branch_exercised"] is True
    assert report["train_objective_win_count_vs_best_reward"] >= 1
    assert report["train_objective_loss_count_vs_best_reward"] == 0
    assert report["objective_evaluator_feedback_used"] is True
    assert report["objective_loop_executed"] is True
    assert report["new_objective_evaluation_used"] is True
    assert report["llm_call_used"] is False
    assert report["real_llm_api_called"] is False
    assert report["unit_test_injected_provider_used"] is True
    assert report["fake_llm_candidates_used"] is False
    assert report["FE_total"] > 0
    assert fake_provider.calls == 2

    rounds = _jsonl(tmp_path / "reflection_rounds.jsonl")
    raw = _jsonl(tmp_path / "raw_llm_candidates.jsonl")
    accepted = _jsonl(tmp_path / "accepted_candidates.jsonl")
    static_audit = json.loads((tmp_path / "static_audit_report.json").read_text())
    evaluator = json.loads((tmp_path / "candidate_evaluator_report.json").read_text())
    route = json.loads((tmp_path / "next_route_decision.json").read_text())

    assert len(rounds) == 2
    assert rounds[1]["feedback_from_previous_round"]["evaluated_candidate_count"] > 0
    assert len(raw) >= 24
    assert len(accepted) >= 8
    assert static_audit["quality_pass_candidate_count"] >= 8
    assert evaluator["selected_candidate_id"] == report["selected_candidate_id"]
    assert evaluator["selected_candidate_not_equivalent_to_best_reward"] is True
    assert route["next_stage"] == "Stage 8.21"
    assert route["allowed_next_work"] == "llm_vs_non_llm_contribution_ablation"


def test_stage8_20_reflection_prompt_satisfies_json_object_provider_requirement() -> None:
    from loco.coordination.llm_reflective_policy_search_execution import _round_messages

    messages = _round_messages(
        prompt_context={
            "allowed_actions": ["trust_best_reward"],
            "allowed_features": ["reward_margin"],
            "failure_patterns_used": ["stage8_18_always_trust_best_reward_degeneracy"],
        },
        round_index=1,
        candidate_count_per_round=12,
        previous_feedback={"evaluated_candidate_count": 0},
    )

    combined = "\n".join(message["content"] for message in messages).lower()
    assert "json" in combined
    assert "return json only" in combined


def test_stage8_20_reflection_prompt_includes_exact_policy_batch_schema() -> None:
    from loco.coordination.llm_reflective_policy_search_execution import _round_messages

    messages = _round_messages(
        prompt_context={
            "allowed_actions": ["trust_best_reward", "weighted_consensus"],
            "allowed_features": ["reward_margin", "conflict_intensity"],
            "failure_patterns_used": ["low_reward_margin_unreliability"],
        },
        round_index=1,
        candidate_count_per_round=12,
        previous_feedback={"evaluated_candidate_count": 0},
    )

    combined = "\n".join(message["content"] for message in messages)
    assert '"schema_version": "loco.stage8_20_raw_policy_batch.v1"' in combined
    assert '"stage": "8.20"' in combined
    assert '"policies"' in combined
    assert '"schema_version": "loco.stage8_20_coordination_policy_program.v1"' in combined
    assert '"policy_id"' in combined
    assert '"rules"' in combined
    assert '"condition"' in combined
    assert '"action"' in combined


def test_stage8_20_evaluator_executes_numeric_and_high_low_conditions() -> None:
    from loco.coordination.llm_reflective_policy_search_execution import (
        _load_policy_program,
        _run_policy_case,
        _train_cases,
    )

    policy = _load_policy_program(
        {
            "schema_version": "loco.stage8_20_coordination_policy_program.v1",
            "policy_id": "unit_condition_policy",
            "origin": "llm_reflective_generated",
            "family": "condition_parser_unit",
            "target_scope": "shared_variables_only",
            "features": [
                "reward_margin",
                "conflict_intensity",
                "direction_consistency",
                "shared_variable_oscillation",
                "recent_best_reward_regret",
            ],
            "memory": ["recent_best_reward_regret"],
            "rules": [
                {"condition": "reward_margin < 0.15", "action": "weighted_consensus"},
                {
                    "condition": "high shared_variable_oscillation OR high recent_best_reward_regret",
                    "action": "shrinkage_repair",
                },
                {
                    "condition": "high reward_margin AND high direction_consistency",
                    "action": "trust_best_reward",
                },
                {"condition": "always", "action": "simple_consensus"},
            ],
            "forbidden_capabilities_used": [],
        }
    )
    cases = {case.case_id: case for case in _train_cases()}

    _, trusted_branch = _run_policy_case(policy, cases["trusted_best_reward"])
    _, low_margin_branch = _run_policy_case(policy, cases["low_margin_weighted"])
    _, oversized_branch = _run_policy_case(
        policy, cases["oversized_best_reward_shrinkage"]
    )

    assert trusted_branch == "trust_best_reward"
    assert low_margin_branch == "weighted_consensus"
    assert oversized_branch == "shrinkage_repair"


def test_stage8_20_committed_artifacts_docs_and_readme_record_execution_or_blocked_state() -> None:
    required = [
        CONFIG,
        REPORT,
        API_PREFLIGHT,
        PROMPT_CONTEXT,
        REFLECTION_ROUNDS,
        RAW_CANDIDATES,
        ACCEPTED_CANDIDATES,
        REJECTED_CANDIDATES,
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
    ledger = json.loads(FE_LEDGER.read_text(encoding="utf-8"))
    boundary = json.loads(RUNTIME_BOUNDARY.read_text(encoding="utf-8"))
    route = json.loads(NEXT_ROUTE.read_text(encoding="utf-8"))

    assert report["stage"] == "8.20"
    assert report["status"] in {"PASS", "BLOCKED_NEEDS_REAL_LLM_API"}
    assert report["fake_llm_candidates_used"] is False
    assert preflight["secret_redacted"] is True
    assert ledger["FE_total"] == report["FE_total"]
    assert boundary["not_sota_claim"] is True
    assert boundary["not_final_performance_claim"] is True

    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [CONFIG, STAGE_DOC, SELF_CHECK, README]
    )
    assert "Current repository state: `Stage 8.35" in combined
    assert "Stage 8.20   LLM-reflective coordination policy search execution" in combined
    assert "fake LLM candidates are forbidden" in combined
    assert "BLOCKED_NEEDS_REAL_LLM_API" in combined or "Stage 8.21" in combined
    assert "not a SOTA claim" in combined
    assert "not a final objective-value performance claim" in combined
    if report["status"] == "PASS":
        assert route["next_stage"] == "Stage 8.21"
    else:
        assert route["next_route"] == "WAIT_FOR_REAL_LLM_API"
