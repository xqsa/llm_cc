from pathlib import Path

import pytest

from loco.contracts.stage0_types import (
    CoordinationOperatorSpec,
    EvaluationLedgerPolicy,
    FORBIDDEN_INFORMATION_ACCESS,
    FORBIDDEN_LLM_ACTIONS,
    REQUIRED_FE_COMPONENTS,
    GroupingMode,
    GroupingReportContract,
    LLMOutputKind,
    OperatorTargetScope,
    Stage0BoundaryConfig,
    default_stage0_boundary,
)


ROOT = Path(__file__).resolve().parents[2]


def test_required_stage0_files_exist() -> None:
    required = [
        "docs/stage0/research_problem.md",
        "docs/stage0/system_boundary.md",
        "docs/stage0/mathematical_contract.md",
        "docs/stage0/allowed_and_forbidden_behaviors.md",
        "docs/stage0/stage0_acceptance_checklist.md",
        "docs/stage0/reviewer_risk_analysis.md",
        "docs/stage0/implementation_roadmap_from_stage0.md",
        "configs/stage0_boundary.yaml",
        "loco/contracts/stage0_types.py",
        "tests/stage0/test_boundary_contract.py",
    ]

    missing = [path for path in required if not (ROOT / path).is_file()]

    assert missing == []


def test_default_boundary_keeps_stage0_non_runtime() -> None:
    boundary = default_stage0_boundary()

    assert boundary.original_problem_type == "single_objective_minimization"
    assert boundary.original_problem_form == "minimize f(x), x in Omega"
    assert boundary.grouping_notation == "G = {G_1, ..., G_M}"
    assert boundary.shared_variable_set_notation == "S = {i | m_i >= 2}"
    assert boundary.operator_mapping_notation == "O_theta: s_i^t -> x_i^{t+1}"
    assert boundary.llm_allowed_output is LLMOutputKind.COORDINATION_OPERATOR_AST
    assert boundary.operator_target_scope is OperatorTargetScope.SHARED_VARIABLES_ONLY
    assert (
        boundary.evaluation_ledger_policy
        is EvaluationLedgerPolicy.COUNT_ALL_EXTRA_FUNCTION_EVALUATIONS
    )
    assert set(boundary.grouping_modes) == {GroupingMode.ORACLE, GroupingMode.DETECTED}
    assert boundary.base_optimizer_policy == "fixed_baseopt"
    assert set(boundary.fe_budget_decomposition) == set(REQUIRED_FE_COMPONENTS)
    assert set(boundary.forbidden_information_access) == set(FORBIDDEN_INFORMATION_ACCESS)
    assert set(boundary.forbidden_llm_actions) == set(FORBIDDEN_LLM_ACTIONS)
    assert not boundary.calls_llm_in_tests
    assert not boundary.runs_evolution_in_tests
    assert not boundary.tunes_parameters_in_tests
    assert not boundary.generates_benchmark_in_tests
    assert not boundary.runs_optimizer_in_tests
    assert not boundary.implements_coordination_operator_logic_in_stage0
    assert not boundary.claims_performance_in_stage0


def test_forbidden_llm_outputs_cover_optimizer_controller_scheduler() -> None:
    boundary = default_stage0_boundary()

    assert "optimizer" in boundary.forbidden_llm_outputs
    assert "controller" in boundary.forbidden_llm_outputs
    assert "scheduler" in boundary.forbidden_llm_outputs
    assert "benchmark" in boundary.forbidden_llm_outputs
    assert "base_optimizer_replacement" in boundary.forbidden_llm_outputs
    assert "arbitrary_executable_code_outside_typed_ast" in boundary.forbidden_llm_outputs
    assert "modify_baseopt" in boundary.forbidden_llm_actions
    assert "select_optimizer" in boundary.forbidden_llm_actions
    assert "access_test_feedback" in boundary.forbidden_llm_actions
    assert "tune_on_test_set" in boundary.forbidden_llm_actions


def test_loco_forbidden_information_access_is_complete() -> None:
    boundary = default_stage0_boundary()

    assert "function_id" in boundary.forbidden_information_access
    assert "benchmark_name" in boundary.forbidden_information_access
    assert "true_optimum_location" in boundary.forbidden_information_access
    assert "test_set_metadata" in boundary.forbidden_information_access
    assert "future_evaluations" in boundary.forbidden_information_access
    assert "hidden_test_information" in boundary.forbidden_information_access


def test_coordination_operator_scope_must_be_shared_variables_only() -> None:
    spec = CoordinationOperatorSpec(
        name="merge_shared_conflicts",
        ast={"type": "weighted_merge", "version": 0},
        target_scope=OperatorTargetScope.SHARED_VARIABLES_ONLY,
        shared_variable_indices=(1, 3, 5),
        touched_variable_indices=(3, 5),
    )

    spec.validate_scope()


def test_coordination_operator_rejects_non_shared_touched_variable() -> None:
    spec = CoordinationOperatorSpec(
        name="illegal_touch",
        ast={"type": "weighted_merge", "version": 0},
        target_scope=OperatorTargetScope.SHARED_VARIABLES_ONLY,
        shared_variable_indices=(1, 3, 5),
        touched_variable_indices=(2, 3),
    )

    with pytest.raises(ValueError, match="subset of shared variables"):
        spec.validate_scope()


def test_coordination_operator_rejects_executable_code_outside_typed_ast() -> None:
    spec = CoordinationOperatorSpec(
        name="illegal_code",
        ast={"type": "weighted_merge", "version": 0, "python": "x = x + 1"},
        target_scope=OperatorTargetScope.SHARED_VARIABLES_ONLY,
        shared_variable_indices=(1, 3, 5),
        touched_variable_indices=(3, 5),
    )

    with pytest.raises(ValueError, match="executable code"):
        spec.validate_scope()


def test_detected_grouping_cannot_use_oracle_only_labels() -> None:
    report = GroupingReportContract(
        mode=GroupingMode.DETECTED,
        shared_variable_count=10,
        overlap_density=0.25,
        uses_oracle_only_labels=True,
    )

    with pytest.raises(ValueError, match="oracle-only labels"):
        report.validate()


def test_stage0_boundary_rejects_runtime_testing_flags() -> None:
    boundary = Stage0BoundaryConfig(calls_llm_in_tests=True)

    with pytest.raises(ValueError, match="boundary-only"):
        boundary.validate()


def test_stage0_boundary_rejects_incomplete_fe_decomposition() -> None:
    boundary = Stage0BoundaryConfig(fe_budget_decomposition=("FE_proposal",))

    with pytest.raises(ValueError, match="FE budget"):
        boundary.validate()


def test_stage0_boundary_rejects_non_fixed_baseopt() -> None:
    boundary = Stage0BoundaryConfig(base_optimizer_policy="adaptive_optimizer_selection")

    with pytest.raises(ValueError, match="BaseOpt"):
        boundary.validate()


def test_yaml_boundary_contains_hard_requirements() -> None:
    text = (ROOT / "configs/stage0_boundary.yaml").read_text(encoding="utf-8")

    assert "single_objective_minimization" in text
    assert "minimize f(x), x in Omega" in text
    assert "G = {G_1, ..., G_M}" in text
    assert "S = {i | m_i >= 2}" in text
    assert "O_theta: s_i^t -> x_i^{t+1}" in text
    assert "shared_variables_only" in text
    assert "coordination_operator_ast" in text
    assert "count_all_extra_function_evaluations" in text
    assert "FE_total = FE_grouping + FE_proposal + FE_coordination_extra + FE_repair" in text
    assert "fixed_baseopt" in text
    assert "separate_oracle_and_detected: true" in text
    assert "function_id" in text
    assert "benchmark_name" in text
    assert "true_optimum_location" in text
    assert "test_set_metadata" in text
    assert "future_evaluations" in text
    assert "hidden_test_information" in text
    assert "modify_baseopt" in text
    assert "select_optimizer" in text
    assert "access_test_feedback" in text
    assert "tune_on_test_set" in text
    assert "arbitrary_executable_code_outside_typed_ast" in text
    assert "frozen_testing_required: true" in text
    assert "calls_llm: false" in text
    assert "runs_evolution: false" in text
    assert "tunes_parameters: false" in text
    assert "generates_benchmark: false" in text
    assert "implements_coordination_operator_logic: false" in text
