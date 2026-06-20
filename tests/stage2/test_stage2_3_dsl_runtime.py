import sys
from pathlib import Path

import numpy as np
import pytest

from loco.conflict.conflict_state import GroupProposal, SharedVariableConflictState
from loco.evaluation.fe_accounting import FEBudgetTracker


def _state() -> SharedVariableConflictState:
    return SharedVariableConflictState.from_group_proposals(
        variable_id=5,
        current_value=0.0,
        bounds=(-0.5, 0.5),
        proposals=[
            GroupProposal(group_id=0, variable_id=5, proposed_value=0.8, reward=0.0),
            GroupProposal(group_id=1, variable_id=5, proposed_value=-0.2, reward=2.0),
            GroupProposal(group_id=2, variable_id=5, proposed_value=0.4, reward=1.0),
        ],
        consensus_history=[0.2, -0.2, 0.2],
    )


def _ast_payload() -> dict:
    return {
        "schema_version": "loco.dsl.v1",
        "operator_id": "weighted_dampened_clip_shared_5",
        "nodes": [
            {
                "id": "weighted",
                "kind": "weighted_consensus",
                "target": {"variable_id": 5},
                "inputs": {"temperature": 1.0},
            },
            {
                "id": "dampened",
                "kind": "dampening",
                "target": {"variable_id": 5},
                "inputs": {"source": "weighted", "damping_strength": 0.75},
            },
            {
                "id": "bounded",
                "kind": "clip",
                "target": {"variable_id": 5},
                "inputs": {"source": "dampened", "lower": -0.1, "upper": 0.1},
            },
        ],
        "output": {"source": "bounded"},
    }


def test_frozen_ast_runtime_interprets_coordination_primitives_without_extra_fe() -> (
    None
):
    from loco.coordination.dsl import load_coordination_ast
    from loco.coordination.dsl_runtime import FrozenASTRuntime

    tracker = FEBudgetTracker(max_fe=100)
    tracker.record("proposal", 3)
    before = tracker.to_dict()

    runtime = FrozenASTRuntime(load_coordination_ast(_ast_payload()))
    result = runtime.coordinate(_state(), shared_variables={5})

    assert tracker.to_dict() == before
    assert result.variable_id == 5
    assert result.operator_name == "DSLRuntime(weighted_dampened_clip_shared_5)"
    assert result.extra_fe == 0
    assert -0.1 <= result.coordinated_value <= 0.1
    assert result.diagnostics["schema_version"] == "loco.dsl.v1"
    assert result.diagnostics["output_node"] == "bounded"
    assert [step["node_id"] for step in result.diagnostics["trace"]] == [
        "weighted",
        "dampened",
        "bounded",
    ]


def test_frozen_ast_runtime_matches_weighted_consensus_when_ast_has_single_node() -> (
    None
):
    from loco.coordination.baselines import WeightedConsensus
    from loco.coordination.dsl import load_coordination_ast
    from loco.coordination.dsl_runtime import FrozenASTRuntime

    payload = {
        "schema_version": "loco.dsl.v1",
        "operator_id": "weighted_only_shared_5",
        "nodes": [
            {
                "id": "weighted",
                "kind": "weighted_consensus",
                "target": {"variable_id": 5},
                "inputs": {"temperature": 1.0},
            }
        ],
        "output": {"source": "weighted"},
    }

    state = _state()
    runtime_result = FrozenASTRuntime(load_coordination_ast(payload)).coordinate(
        state, shared_variables={5}
    )
    baseline_result = WeightedConsensus(temperature=1.0).coordinate(state)

    assert np.isclose(
        runtime_result.coordinated_value, baseline_result.coordinated_value
    )
    assert runtime_result.extra_fe == 0


def test_frozen_ast_runtime_supports_root_projection_without_source() -> None:
    from loco.coordination.dsl import load_coordination_ast
    from loco.coordination.dsl_runtime import FrozenASTRuntime

    payload = {
        "schema_version": "loco.dsl.v1",
        "operator_id": "root_projection_shared_5",
        "nodes": [
            {
                "id": "project",
                "kind": "projection",
                "target": {"variable_id": 5},
                "inputs": {"projection": "box"},
            }
        ],
        "output": {"source": "project"},
    }

    result = FrozenASTRuntime(load_coordination_ast(payload)).coordinate(
        _state(), shared_variables={5}
    )

    assert result.variable_id == 5
    assert result.extra_fe == 0
    assert result.coordinated_value == 0.3333333333333333
    assert result.diagnostics["trace"][0]["diagnostics"] == {
        "projection": "bounds",
        "source": "proposal_mean",
    }


def test_frozen_ast_runtime_rejects_wrong_variable_state() -> None:
    from loco.coordination.dsl import load_coordination_ast
    from loco.coordination.dsl_runtime import FrozenASTRuntime

    wrong_state = SharedVariableConflictState.from_group_proposals(
        variable_id=6,
        current_value=0.0,
        bounds=(-1.0, 1.0),
        proposals=[
            GroupProposal(group_id=0, variable_id=6, proposed_value=0.1, reward=0.0),
            GroupProposal(group_id=1, variable_id=6, proposed_value=0.2, reward=1.0),
        ],
    )

    runtime = FrozenASTRuntime(load_coordination_ast(_ast_payload()))
    with pytest.raises(ValueError, match="does not match conflict_state.variable_id"):
        runtime.coordinate(wrong_state, shared_variables={5, 6})


def test_stage2_3_runtime_does_not_load_llm_or_evolution_modules() -> None:
    forbidden_loaded_before = {
        name
        for name in sys.modules
        if name.startswith(("openai", "anthropic", "google.generativeai", "deap"))
    }

    from loco.coordination.dsl import load_coordination_ast
    from loco.coordination.dsl_runtime import FrozenASTRuntime

    FrozenASTRuntime(load_coordination_ast(_ast_payload())).coordinate(
        _state(), shared_variables={5}
    )

    forbidden_loaded_after = {
        name
        for name in sys.modules
        if name.startswith(("openai", "anthropic", "google.generativeai", "deap"))
    }
    assert forbidden_loaded_after == forbidden_loaded_before


def test_stage2_3_boundary_artifacts_exist_and_state_runtime_limits() -> None:
    root = Path(__file__).resolve().parents[2]
    config_text = (root / "configs" / "stage2_3_dsl_runtime.yaml").read_text(
        encoding="utf-8"
    )
    doc_text = (root / "docs" / "stage2" / "stage2_3_dsl_runtime.md").read_text(
        encoding="utf-8"
    )
    report_text = (
        root / "docs" / "stage2" / "stage2_3_self_check_report.md"
    ).read_text(encoding="utf-8")

    combined = "\n".join([config_text, doc_text, report_text])
    assert "frozen typed AST" in combined
    assert "shared variables" in combined
    assert "no LLM" in combined
    assert "no evolution" in combined
    assert "no optimizer" in combined
    assert "no controller/scheduler" in combined
    assert "no objective evaluation" in combined
