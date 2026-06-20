import json
import sys
from pathlib import Path

import pytest

from loco.evaluation.fe_accounting import FEBudgetTracker


def _valid_ast() -> dict:
    return {
        "schema_version": "loco.dsl.v1",
        "operator_id": "weighted_clip_shared_5",
        "nodes": [
            {
                "id": "n1",
                "kind": "weighted_consensus",
                "target": {"variable_id": 5},
                "inputs": {"temperature": 1.0},
            },
            {
                "id": "n2",
                "kind": "clip",
                "target": {"variable_id": 5},
                "inputs": {"source": "n1"},
            },
        ],
        "output": {"source": "n2"},
    }


def test_valid_minimal_coordination_ast_passes_and_serializes_deterministically() -> (
    None
):
    from loco.coordination.dsl import (
        DSL_SCHEMA_VERSION,
        load_coordination_ast,
        serialize_coordination_ast,
        validate_coordination_ast,
    )

    ast = load_coordination_ast(_valid_ast())
    report = validate_coordination_ast(ast, shared_variables={5, 9})

    assert report.schema_version == DSL_SCHEMA_VERSION
    assert report.operator_id == "weighted_clip_shared_5"
    assert report.node_count == 2
    assert report.max_depth == 2
    assert report.target_variables == frozenset({5})

    encoded = serialize_coordination_ast(ast)
    assert json.loads(encoded)["schema_version"] == DSL_SCHEMA_VERSION
    assert encoded == serialize_coordination_ast(
        load_coordination_ast(json.loads(encoded))
    )


def test_valid_ast_targets_must_be_subset_of_shared_variables() -> None:
    from loco.coordination.dsl import load_coordination_ast, validate_coordination_ast

    ast = load_coordination_ast(_valid_ast())

    with pytest.raises(ValueError, match="non-shared variables"):
        validate_coordination_ast(ast, shared_variables={1, 2, 3})


@pytest.mark.parametrize(
    "forbidden_kind",
    [
        "optimizer",
        "de_optimizer",
        "controller",
        "scheduler",
        "optimizer_selection",
    ],
)
def test_forbidden_optimizer_controller_scheduler_nodes_are_rejected(
    forbidden_kind: str,
) -> None:
    from loco.coordination.dsl import load_coordination_ast

    payload = _valid_ast()
    payload["nodes"][0]["kind"] = forbidden_kind

    with pytest.raises(ValueError, match="Forbidden DSL node kind"):
        load_coordination_ast(payload)


@pytest.mark.parametrize(
    "code_like",
    [
        "lambda x: x",
        "import os",
        "__import__('os').system('echo unsafe')",
        "def coordinate(x): return x",
        "eval('1 + 1')",
    ],
)
def test_arbitrary_executable_code_strings_are_rejected(code_like: str) -> None:
    from loco.coordination.dsl import load_coordination_ast

    payload = _valid_ast()
    payload["nodes"][0]["inputs"]["source_code"] = code_like

    with pytest.raises(ValueError, match="executable code"):
        load_coordination_ast(payload)


@pytest.mark.parametrize(
    "forbidden_key",
    [
        "function_id",
        "benchmark_name",
        "true_optimum_location",
        "test_set_metadata",
        "future_evaluations",
        "hidden_test_information",
    ],
)
def test_forbidden_metadata_access_is_rejected(forbidden_key: str) -> None:
    from loco.coordination.dsl import load_coordination_ast

    payload = _valid_ast()
    payload["nodes"][0]["inputs"][forbidden_key] = "leaky"

    with pytest.raises(ValueError, match="forbidden metadata"):
        load_coordination_ast(payload)


def test_unknown_fields_are_rejected() -> None:
    from loco.coordination.dsl import load_coordination_ast

    payload = _valid_ast()
    payload["nodes"][0]["python_callable"] = "AverageConsensus"

    with pytest.raises(ValueError, match="Unknown node fields"):
        load_coordination_ast(payload)


def test_oversized_and_too_deep_asts_are_rejected() -> None:
    from loco.coordination.dsl import load_coordination_ast, validate_coordination_ast

    too_many_nodes = _valid_ast()
    too_many_nodes["nodes"] = [
        {
            "id": f"n{i}",
            "kind": "consensus",
            "target": {"variable_id": 5},
            "inputs": {},
        }
        for i in range(33)
    ]
    too_many_nodes["output"] = {"source": "n32"}

    with pytest.raises(ValueError, match="exceeds max_nodes"):
        validate_coordination_ast(load_coordination_ast(too_many_nodes), {5})

    too_deep = _valid_ast()
    too_deep["nodes"] = [
        {
            "id": f"n{i}",
            "kind": "dampening",
            "target": {"variable_id": 5},
            "inputs": {"source": f"n{i - 1}"} if i > 0 else {},
        }
        for i in range(9)
    ]
    too_deep["output"] = {"source": "n8"}

    with pytest.raises(ValueError, match="exceeds max_depth"):
        validate_coordination_ast(load_coordination_ast(too_deep), {5}, max_depth=8)


def test_validation_does_not_change_fe_accounting() -> None:
    from loco.coordination.dsl import load_coordination_ast, validate_coordination_ast

    tracker = FEBudgetTracker(max_fe=100)
    tracker.record("proposal", 4)
    before = tracker.to_dict()

    validate_coordination_ast(load_coordination_ast(_valid_ast()), shared_variables={5})

    assert tracker.to_dict() == before


def test_stage2_2_import_does_not_load_llm_or_evolution_modules() -> None:
    forbidden_loaded_before = {
        name
        for name in sys.modules
        if name.startswith(("openai", "anthropic", "google.generativeai", "deap"))
    }

    from loco.coordination.dsl import load_coordination_ast, validate_coordination_ast

    validate_coordination_ast(load_coordination_ast(_valid_ast()), shared_variables={5})

    forbidden_loaded_after = {
        name
        for name in sys.modules
        if name.startswith(("openai", "anthropic", "google.generativeai", "deap"))
    }
    assert forbidden_loaded_after == forbidden_loaded_before


def test_stage3_preflight_accepts_and_rejects_candidate_asts_without_execution() -> (
    None
):
    from loco.coordination.dsl import (
        serialize_coordination_ast,
        stage3_preflight_check,
    )

    valid_payload = _valid_ast()
    non_shared_payload = _valid_ast()
    non_shared_payload["operator_id"] = "targets_non_shared_7"
    non_shared_payload["nodes"][0]["target"]["variable_id"] = 7
    non_shared_payload["nodes"][1]["target"]["variable_id"] = 7
    forbidden_payload = _valid_ast()
    forbidden_payload["operator_id"] = "tries_optimizer"
    forbidden_payload["nodes"][0]["kind"] = "optimizer"

    tracker = FEBudgetTracker(max_fe=100)
    tracker.record("proposal", 2)
    before = tracker.to_dict()

    report = stage3_preflight_check(
        [valid_payload, non_shared_payload, forbidden_payload],
        shared_variables={5},
    )

    assert tracker.to_dict() == before
    assert report.total_count == 3
    assert report.accepted_count == 1
    assert report.rejected_count == 2

    accepted = report.accepted[0]
    assert accepted.candidate_id == "weighted_clip_shared_5"
    assert accepted.serialized_ast == serialize_coordination_ast(accepted.ast)
    assert len(accepted.fingerprint_sha256) == 64

    rejected_by_id = {item.candidate_id: item for item in report.rejected}
    assert "targets_non_shared_7" in rejected_by_id
    assert (
        "non-shared variables" in rejected_by_id["targets_non_shared_7"].reject_reason
    )
    assert "tries_optimizer" in rejected_by_id
    assert "Forbidden DSL node kind" in rejected_by_id["tries_optimizer"].reject_reason

    rerun = stage3_preflight_check([valid_payload], shared_variables={5})
    assert rerun.accepted[0].fingerprint_sha256 == accepted.fingerprint_sha256


def test_stage2_2_boundary_artifacts_exist_and_state_research_limits() -> None:
    root = Path(__file__).resolve().parents[2]
    config_text = (root / "configs" / "stage2_2_dsl_boundary.yaml").read_text(
        encoding="utf-8"
    )
    doc_text = (root / "docs" / "stage2" / "stage2_2_dsl_boundary.md").read_text(
        encoding="utf-8"
    )
    report_text = (
        root / "docs" / "stage2" / "stage2_2_self_check_report.md"
    ).read_text(encoding="utf-8")

    combined = "\n".join([config_text, doc_text, report_text])
    assert "typed coordination operator AST" in combined
    assert "shared variables" in combined
    assert "no LLM" in combined
    assert "no evolution" in combined
    assert "no optimizer" in combined
    assert "no controller/scheduler" in combined
    assert "arbitrary executable code" in combined
    assert "function_id" in config_text
    assert "benchmark_name" in config_text
    assert "future_evaluations" in config_text
    assert "Stage 3 preflight" in combined
