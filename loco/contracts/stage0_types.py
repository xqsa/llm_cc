"""Stage 0 boundary contracts for LOCO-LSGO.

This module intentionally contains only typed contract drafts and local
validation helpers. It must not implement an optimizer, benchmark, LLM search
loop, controller, scheduler, or parameter tuning logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Tuple


class GroupingMode(str, Enum):
    """Grouping report modes that must remain separate in experiments."""

    ORACLE = "oracle_grouping"
    DETECTED = "detected_grouping"


class OperatorTargetScope(str, Enum):
    """Legal target scope for a LOCO coordination operator."""

    SHARED_VARIABLES_ONLY = "shared_variables_only"


class LLMOutputKind(str, Enum):
    """The only legal LLM output kind for the LOCO line."""

    COORDINATION_OPERATOR_AST = "coordination_operator_ast"


class EvaluationLedgerPolicy(str, Enum):
    """Function-evaluation accounting policies."""

    COUNT_ALL_EXTRA_FUNCTION_EVALUATIONS = "count_all_extra_function_evaluations"


FORBIDDEN_LLM_OUTPUT_KINDS: Tuple[str, ...] = (
    "optimizer",
    "controller",
    "scheduler",
    "base_optimizer_replacement",
    "benchmark",
    "problem_generator",
    "budget_policy",
    "grouping_oracle",
    "arbitrary_executable_code_outside_typed_ast",
)


FORBIDDEN_LLM_ACTIONS: Tuple[str, ...] = (
    "generate_optimizer",
    "modify_baseopt",
    "generate_scheduler_or_controller",
    "select_optimizer",
    "access_test_feedback",
    "tune_on_test_set",
    "generate_arbitrary_executable_code_outside_typed_ast",
)


FORBIDDEN_INFORMATION_ACCESS: Tuple[str, ...] = (
    "function_id",
    "benchmark_name",
    "true_optimum_location",
    "test_set_metadata",
    "future_evaluations",
    "hidden_test_information",
)


REQUIRED_FE_COMPONENTS: Tuple[str, ...] = (
    "FE_grouping",
    "FE_proposal",
    "FE_coordination_extra",
    "FE_repair",
)


@dataclass(frozen=True)
class Stage0BoundaryConfig:
    """Machine-checkable draft of the Stage 0 boundary."""

    project_name: str = "LOCO-LSGO"
    original_problem_type: str = "single_objective_minimization"
    original_problem_form: str = "minimize f(x), x in Omega"
    grouping_notation: str = "G = {G_1, ..., G_M}"
    shared_variable_set_notation: str = "S = {i | m_i >= 2}"
    operator_mapping_notation: str = "O_theta: s_i^t -> x_i^{t+1}"
    llm_allowed_output: LLMOutputKind = LLMOutputKind.COORDINATION_OPERATOR_AST
    operator_target_scope: OperatorTargetScope = (
        OperatorTargetScope.SHARED_VARIABLES_ONLY
    )
    evaluation_ledger_policy: EvaluationLedgerPolicy = (
        EvaluationLedgerPolicy.COUNT_ALL_EXTRA_FUNCTION_EVALUATIONS
    )
    grouping_modes: Tuple[GroupingMode, ...] = (
        GroupingMode.ORACLE,
        GroupingMode.DETECTED,
    )
    base_optimizer_policy: str = "fixed_baseopt"
    fe_budget_decomposition: Tuple[str, ...] = REQUIRED_FE_COMPONENTS
    calls_llm_in_tests: bool = False
    runs_evolution_in_tests: bool = False
    tunes_parameters_in_tests: bool = False
    generates_benchmark_in_tests: bool = False
    runs_optimizer_in_tests: bool = False
    implements_coordination_operator_logic_in_stage0: bool = False
    claims_performance_in_stage0: bool = False
    forbidden_information_access: Tuple[str, ...] = FORBIDDEN_INFORMATION_ACCESS
    forbidden_llm_outputs: Tuple[str, ...] = FORBIDDEN_LLM_OUTPUT_KINDS
    forbidden_llm_actions: Tuple[str, ...] = FORBIDDEN_LLM_ACTIONS

    def validate(self) -> None:
        """Raise ValueError if the Stage 0 boundary has been weakened."""

        if self.original_problem_type != "single_objective_minimization":
            raise ValueError(
                "Stage 0 requires the original problem to be single-objective."
            )
        if self.original_problem_form != "minimize f(x), x in Omega":
            raise ValueError(
                "Original problem form must remain minimize f(x), x in Omega."
            )
        if self.grouping_notation != "G = {G_1, ..., G_M}":
            raise ValueError("Grouping notation must remain G = {G_1, ..., G_M}.")
        if self.shared_variable_set_notation != "S = {i | m_i >= 2}":
            raise ValueError(
                "Shared variable set notation must remain S = {i | m_i >= 2}."
            )
        if self.operator_mapping_notation != "O_theta: s_i^t -> x_i^{t+1}":
            raise ValueError("LOCO operator mapping notation must remain fixed.")
        if self.llm_allowed_output is not LLMOutputKind.COORDINATION_OPERATOR_AST:
            raise ValueError("LLM output must be limited to coordination operator AST.")
        if self.operator_target_scope is not OperatorTargetScope.SHARED_VARIABLES_ONLY:
            raise ValueError("LOCO operators must target shared variables only.")
        if (
            self.evaluation_ledger_policy
            is not EvaluationLedgerPolicy.COUNT_ALL_EXTRA_FUNCTION_EVALUATIONS
        ):
            raise ValueError("All extra function evaluations must be counted.")
        if set(self.grouping_modes) != {GroupingMode.ORACLE, GroupingMode.DETECTED}:
            raise ValueError(
                "Oracle and detected grouping modes must both be represented."
            )
        if self.base_optimizer_policy != "fixed_baseopt":
            raise ValueError("BaseOpt must remain fixed for LOCO comparisons.")
        if set(self.fe_budget_decomposition) != set(REQUIRED_FE_COMPONENTS):
            raise ValueError(
                "FE budget must include grouping, proposal, coordination, and repair."
            )
        if set(self.forbidden_information_access) != set(FORBIDDEN_INFORMATION_ACCESS):
            raise ValueError(
                "Forbidden information access boundary must remain complete."
            )
        if set(self.forbidden_llm_actions) != set(FORBIDDEN_LLM_ACTIONS):
            raise ValueError("Forbidden LLM action boundary must remain complete.")
        if any(
            (
                self.calls_llm_in_tests,
                self.runs_evolution_in_tests,
                self.tunes_parameters_in_tests,
                self.generates_benchmark_in_tests,
                self.runs_optimizer_in_tests,
                self.implements_coordination_operator_logic_in_stage0,
                self.claims_performance_in_stage0,
            )
        ):
            raise ValueError("Stage 0 tests and claims must remain boundary-only.")


@dataclass(frozen=True)
class CoordinationOperatorSpec:
    """Draft interface for a LOCO coordination operator AST."""

    name: str
    ast: Mapping[str, Any]
    target_scope: OperatorTargetScope
    ast_schema: str = "typed_ast"
    executable_code_allowed: bool = False
    shared_variable_indices: Tuple[int, ...] = field(default_factory=tuple)
    touched_variable_indices: Tuple[int, ...] = field(default_factory=tuple)

    def validate_scope(self) -> None:
        """Validate that the operator only declares shared-variable targets."""

        if self.target_scope is not OperatorTargetScope.SHARED_VARIABLES_ONLY:
            raise ValueError(
                "Coordination operator scope must be shared_variables_only."
            )
        if not self.name:
            raise ValueError("Coordination operator name is required.")
        if not self.ast:
            raise ValueError("Coordination operator AST is required.")
        if self.ast_schema != "typed_ast":
            raise ValueError("Coordination operator must use typed_ast schema.")
        if self.executable_code_allowed:
            raise ValueError(
                "Arbitrary executable code is forbidden outside typed AST."
            )

        shared = set(self.shared_variable_indices)
        touched = set(self.touched_variable_indices)
        if any(index < 0 for index in shared | touched):
            raise ValueError("Variable indices must be non-negative.")
        if not touched.issubset(shared):
            raise ValueError("Touched variables must be a subset of shared variables.")

        forbidden_code_keys = {"code", "source", "python", "exec", "eval"}
        if forbidden_code_keys.intersection(self.ast):
            raise ValueError(
                "Coordination operator AST must not embed executable code."
            )


@dataclass(frozen=True)
class GroupingReportContract:
    """Report contract that keeps oracle and detected grouping separate."""

    mode: GroupingMode
    shared_variable_count: int
    overlap_density: float
    uses_oracle_only_labels: bool = False

    def validate(self) -> None:
        """Validate grouping-report separation and basic overlap metadata."""

        if self.shared_variable_count < 0:
            raise ValueError("shared_variable_count must be non-negative.")
        if not 0.0 <= self.overlap_density <= 1.0:
            raise ValueError("overlap_density must be in [0, 1].")
        if self.mode is GroupingMode.DETECTED and self.uses_oracle_only_labels:
            raise ValueError(
                "Detected grouping reports must not use oracle-only labels."
            )


def default_stage0_boundary() -> Stage0BoundaryConfig:
    """Return the strict default Stage 0 boundary."""

    boundary = Stage0BoundaryConfig()
    boundary.validate()
    return boundary
