"""Handwritten frozen-AST smoke operator for Stage 2.5.

This module bridges the Stage 2.3 DSL runtime into the existing synthetic
runner through a frozen Stage 2.5 artifact. It does not generate candidates,
call LLMs, run evolution, or evaluate objectives.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loco.conflict.conflict_state import SharedVariableConflictState
from loco.coordination.baselines import CoordinationResult
from loco.coordination.dsl import load_coordination_ast, stage3_preflight_check
from loco.coordination.dsl_runtime import FrozenASTRuntime
from loco.coordination.operator_artifacts import (
    DEFAULT_STAGE2_5_ARTIFACT_PATH,
    FrozenOperatorArtifact,
    load_frozen_operator_artifact,
)


class FrozenASTSmokeOperator:
    """Interpret a fixed AST template for each shared-variable conflict state."""

    name = "FrozenASTSmoke"

    def __init__(
        self,
        artifact_path: Path | str = DEFAULT_STAGE2_5_ARTIFACT_PATH,
        artifact: FrozenOperatorArtifact | None = None,
    ):
        self.artifact = artifact or load_frozen_operator_artifact(artifact_path)

    def coordinate(
        self, conflict_state: SharedVariableConflictState
    ) -> CoordinationResult:
        payload = self.artifact.instantiate_for_conflict_state(conflict_state)
        preflight = stage3_preflight_check(
            [payload], shared_variables={conflict_state.variable_id}
        )
        if preflight.accepted_count != 1:
            reason = (
                preflight.rejected[0].reject_reason
                if preflight.rejected
                else "unknown preflight rejection"
            )
            raise ValueError(f"Frozen AST smoke payload failed preflight: {reason}")

        ast = load_coordination_ast(payload)
        result = FrozenASTRuntime(ast).coordinate(
            conflict_state, shared_variables={conflict_state.variable_id}
        )
        diagnostics = dict(result.diagnostics)
        diagnostics.update(self.artifact.metadata())
        diagnostics["accepted_fingerprint_sha256"] = preflight.accepted[
            0
        ].fingerprint_sha256
        return CoordinationResult(
            variable_id=result.variable_id,
            coordinated_value=result.coordinated_value,
            operator_name=result.operator_name,
            extra_fe=result.extra_fe,
            diagnostics=diagnostics,
        )

    def runtime_metadata(self) -> dict[str, Any]:
        metadata = self.artifact.metadata()
        metadata["accepted_by_preflight"] = True
        return metadata
