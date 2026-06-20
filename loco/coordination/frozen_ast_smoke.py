"""Handwritten frozen-AST smoke operator for Stage 2.4.

This module bridges the Stage 2.3 DSL runtime into the existing synthetic
runner. It uses a fixed typed-AST template and does not generate candidates,
call LLMs, run evolution, or evaluate objectives.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from loco.conflict.conflict_state import SharedVariableConflictState
from loco.coordination.baselines import CoordinationResult
from loco.coordination.dsl import load_coordination_ast, stage3_preflight_check
from loco.coordination.dsl_runtime import FrozenASTRuntime


FROZEN_AST_SMOKE_TEMPLATE_ID = "stage2_4_weighted_dampened_clip_template"
FROZEN_AST_SMOKE_TEMPLATE = {
    "schema_version": "loco.dsl.v1",
    "operator_id": FROZEN_AST_SMOKE_TEMPLATE_ID,
    "target_variable": "$shared_variable",
    "nodes": [
        {"id": "weighted", "kind": "weighted_consensus"},
        {"id": "dampened", "kind": "dampening", "source": "weighted"},
        {"id": "bounded", "kind": "clip", "source": "dampened"},
    ],
    "output": {"source": "bounded"},
}
FROZEN_AST_SMOKE_TEMPLATE_FINGERPRINT = hashlib.sha256(
    json.dumps(FROZEN_AST_SMOKE_TEMPLATE, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
).hexdigest()


class FrozenASTSmokeOperator:
    """Interpret a fixed AST template for each shared-variable conflict state."""

    name = "FrozenASTSmoke"

    def coordinate(
        self, conflict_state: SharedVariableConflictState
    ) -> CoordinationResult:
        payload = frozen_ast_smoke_payload(conflict_state)
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
        diagnostics["template_id"] = FROZEN_AST_SMOKE_TEMPLATE_ID
        diagnostics["template_fingerprint_sha256"] = (
            FROZEN_AST_SMOKE_TEMPLATE_FINGERPRINT
        )
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
        return {
            "template_id": FROZEN_AST_SMOKE_TEMPLATE_ID,
            "schema_version": "loco.dsl.v1",
            "template_fingerprint_sha256": FROZEN_AST_SMOKE_TEMPLATE_FINGERPRINT,
            "accepted_by_preflight": True,
            "source": "handwritten_frozen_ast_template",
            "no_llm": True,
            "no_evolution": True,
            "no_objective_evaluation": True,
        }


def frozen_ast_smoke_payload(
    conflict_state: SharedVariableConflictState,
) -> dict[str, Any]:
    variable_id = int(conflict_state.variable_id)
    lower, upper = conflict_state.bounds
    return {
        "schema_version": "loco.dsl.v1",
        "operator_id": f"stage2_4_frozen_ast_shared_{variable_id}",
        "nodes": [
            {
                "id": "weighted",
                "kind": "weighted_consensus",
                "target": {"variable_id": variable_id},
                "inputs": {"temperature": 1.0},
            },
            {
                "id": "dampened",
                "kind": "dampening",
                "target": {"variable_id": variable_id},
                "inputs": {"source": "weighted", "damping_strength": 0.5},
            },
            {
                "id": "bounded",
                "kind": "clip",
                "target": {"variable_id": variable_id},
                "inputs": {
                    "source": "dampened",
                    "lower": float(lower),
                    "upper": float(upper),
                },
            },
        ],
        "output": {"source": "bounded"},
    }
