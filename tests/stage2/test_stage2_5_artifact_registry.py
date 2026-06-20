import json
import sys
from pathlib import Path

from loco.conflict.conflict_state import GroupProposal, SharedVariableConflictState
from loco.experiments.stage2_minimal_runner import run_stage2_synthetic_minimal


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_PATH = (
    ROOT
    / "artifacts"
    / "operators"
    / "stage2_5"
    / "frozen_ast_smoke_weighted_dampened_clip.json"
)
REGISTRY_PATH = ROOT / "artifacts" / "operators" / "stage2_5_registry.jsonl"


def _state(variable_id: int = 5) -> SharedVariableConflictState:
    return SharedVariableConflictState.from_group_proposals(
        variable_id=variable_id,
        current_value=0.1,
        bounds=(-0.25, 0.35),
        proposals=[
            GroupProposal(
                group_id=0,
                variable_id=variable_id,
                proposed_value=0.30,
                reward=0.5,
            ),
            GroupProposal(
                group_id=1,
                variable_id=variable_id,
                proposed_value=-0.20,
                reward=2.0,
            ),
        ],
        consensus_history=[0.2, -0.2, 0.1],
    )


def test_stage2_5_artifact_files_exist_and_are_registered() -> None:
    from loco.coordination.operator_artifacts import load_operator_registry

    registry = load_operator_registry(REGISTRY_PATH)

    assert ARTIFACT_PATH.is_file()
    assert REGISTRY_PATH.is_file()
    assert len(registry.entries) == 1
    entry = registry.entries[0]
    assert entry.artifact_id == "stage2_5.frozen_ast_smoke.weighted_dampened_clip"
    assert entry.operator_name == "FrozenASTSmoke"
    assert entry.source == "handwritten_frozen_ast_template"
    assert entry.target_scope == "shared_variables_only"
    assert entry.no_llm is True
    assert entry.no_evolution is True
    assert entry.no_test_feedback is True
    assert entry.frozen is True
    assert len(entry.artifact_fingerprint_sha256) == 64


def test_stage2_5_artifact_loads_instantiates_and_preflights_deterministically() -> (
    None
):
    from loco.coordination.operator_artifacts import load_frozen_operator_artifact

    artifact = load_frozen_operator_artifact(ARTIFACT_PATH)
    payload = artifact.instantiate_for_conflict_state(_state())
    report = artifact.preflight_for_conflict_state(_state())

    assert artifact.artifact_id == "stage2_5.frozen_ast_smoke.weighted_dampened_clip"
    assert artifact.operator_name == "FrozenASTSmoke"
    assert artifact.frozen is True
    assert artifact.no_test_feedback is True
    assert artifact.test_mode_allowed is True
    assert artifact.metadata()["artifact_path"].endswith(
        "artifacts/operators/stage2_5/frozen_ast_smoke_weighted_dampened_clip.json"
    )

    assert payload["operator_id"] == "stage2_5_frozen_ast_shared_5"
    assert payload["nodes"][0]["target"] == {"variable_id": 5}
    assert payload["nodes"][2]["inputs"]["lower"] == -0.25
    assert payload["nodes"][2]["inputs"]["upper"] == 0.35

    assert report.accepted_count == 1
    assert report.rejected_count == 0
    assert report.accepted[0].candidate_id == "stage2_5_frozen_ast_shared_5"
    assert report.accepted[0].fingerprint_sha256 == (
        artifact.preflight_for_conflict_state(_state()).accepted[0].fingerprint_sha256
    )


def test_stage2_5_artifact_fingerprint_changes_when_artifact_content_changes() -> None:
    from loco.coordination.operator_artifacts import (
        compute_artifact_fingerprint,
        load_frozen_operator_artifact,
    )

    artifact = load_frozen_operator_artifact(ARTIFACT_PATH)
    payload = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))
    payload["ast_template"]["nodes"][1]["inputs"]["damping_strength"] = 0.25

    assert compute_artifact_fingerprint(payload) != artifact.artifact_fingerprint_sha256


def test_stage2_5_artifact_rejects_unfrozen_or_test_feedback_payloads() -> None:
    from loco.coordination.operator_artifacts import load_operator_artifact_payload

    payload = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))
    payload["provenance"]["frozen"] = False
    try:
        load_operator_artifact_payload(payload, artifact_path=ARTIFACT_PATH)
    except ValueError as exc:
        assert "frozen" in str(exc)
    else:
        raise AssertionError("unfrozen artifact should be rejected")

    payload = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))
    payload["split_policy"]["no_test_feedback"] = False
    try:
        load_operator_artifact_payload(payload, artifact_path=ARTIFACT_PATH)
    except ValueError as exc:
        assert "no_test_feedback" in str(exc)
    else:
        raise AssertionError("artifact with test feedback should be rejected")


def test_stage2_5_runner_reports_artifact_provenance_without_polluting_stage2_1() -> (
    None
):
    result = run_stage2_synthetic_minimal(seed=31)
    operator = result["operators"]["FrozenASTSmoke"]
    runtime = operator["frozen_ast_runtime"]

    assert result["stage"] == "2.5"
    assert result["artifact_registry"]["enabled"] is True
    assert result["artifact_registry"]["registry_path"].endswith(
        "artifacts/operators/stage2_5_registry.jsonl"
    )
    assert runtime["source"] == "frozen_artifact_registry"
    assert runtime["artifact_id"] == "stage2_5.frozen_ast_smoke.weighted_dampened_clip"
    assert runtime["target_scope"] == "shared_variables_only"
    assert runtime["no_llm"] is True
    assert runtime["no_evolution"] is True
    assert runtime["no_test_feedback"] is True
    assert runtime["test_mode_allowed"] is True
    assert len(runtime["artifact_fingerprint_sha256"]) == 64

    for coordination_result in operator["coordination_results"].values():
        diagnostics = coordination_result["diagnostics"]
        assert diagnostics["artifact_id"] == runtime["artifact_id"]
        assert (
            diagnostics["artifact_fingerprint_sha256"]
            == runtime["artifact_fingerprint_sha256"]
        )
        assert diagnostics["template_id"] == "stage2_5_weighted_dampened_clip_template"


def test_stage2_5_runner_does_not_import_llm_or_evolution_modules() -> None:
    forbidden_loaded_before = {
        name
        for name in sys.modules
        if name.startswith(("openai", "anthropic", "google.generativeai", "deap"))
    }

    run_stage2_synthetic_minimal(seed=37)

    forbidden_loaded_after = {
        name
        for name in sys.modules
        if name.startswith(("openai", "anthropic", "google.generativeai", "deap"))
    }
    assert forbidden_loaded_after == forbidden_loaded_before
