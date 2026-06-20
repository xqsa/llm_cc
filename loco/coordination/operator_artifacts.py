"""Frozen coordination-operator artifact registry for Stage 2.5.

This module handles artifact provenance and deterministic instantiation of
already-frozen typed AST templates. It does not execute operators, call LLMs,
run evolution, or evaluate objectives.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from loco.conflict.conflict_state import SharedVariableConflictState
from loco.coordination.dsl import DSL_SCHEMA_VERSION, stage3_preflight_check


ARTIFACT_SCHEMA_VERSION = "loco.operator_artifact.v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STAGE2_5_ARTIFACT_PATH = (
    REPO_ROOT
    / "artifacts"
    / "operators"
    / "stage2_5"
    / "frozen_ast_smoke_weighted_dampened_clip.json"
)
DEFAULT_STAGE2_5_REGISTRY_PATH = (
    REPO_ROOT / "artifacts" / "operators" / "stage2_5_registry.jsonl"
)


@dataclass(frozen=True)
class OperatorRegistryEntry:
    artifact_id: str
    artifact_path: Path
    operator_name: str
    source: str
    target_scope: str
    artifact_fingerprint_sha256: str
    no_llm: bool
    no_evolution: bool
    no_test_feedback: bool
    frozen: bool


@dataclass(frozen=True)
class OperatorRegistry:
    registry_path: Path
    entries: tuple[OperatorRegistryEntry, ...]


@dataclass(frozen=True)
class FrozenOperatorArtifact:
    artifact_path: Path
    payload: Mapping[str, Any]
    artifact_fingerprint_sha256: str

    @property
    def artifact_id(self) -> str:
        return str(self.payload["artifact_id"])

    @property
    def operator_name(self) -> str:
        return str(self.payload["operator_name"])

    @property
    def source(self) -> str:
        return str(self.payload["source"])

    @property
    def template_id(self) -> str:
        return str(self.payload["template_id"])

    @property
    def target_scope(self) -> str:
        return str(self.payload["target_scope"])

    @property
    def frozen(self) -> bool:
        return bool(self.payload["provenance"]["frozen"])

    @property
    def no_llm(self) -> bool:
        return bool(self.payload["provenance"]["no_llm"])

    @property
    def no_evolution(self) -> bool:
        return bool(self.payload["provenance"]["no_evolution"])

    @property
    def no_optimizer(self) -> bool:
        return bool(self.payload["provenance"]["no_optimizer"])

    @property
    def no_objective_evaluation(self) -> bool:
        return bool(self.payload["provenance"]["no_objective_evaluation"])

    @property
    def no_test_feedback(self) -> bool:
        return bool(self.payload["split_policy"]["no_test_feedback"])

    @property
    def test_mode_allowed(self) -> bool:
        return bool(self.payload["split_policy"]["test_mode_allowed"])

    def instantiate_for_conflict_state(
        self, conflict_state: SharedVariableConflictState
    ) -> dict[str, Any]:
        variable_id = int(conflict_state.variable_id)
        lower, upper = conflict_state.bounds
        template = self.payload["ast_template"]
        return {
            "schema_version": self.payload["dsl_schema_version"],
            "operator_id": str(template["operator_id_template"]).format(
                variable_id=variable_id
            ),
            "nodes": [
                _replace_template_placeholders(
                    node, variable_id, float(lower), float(upper)
                )
                for node in template["nodes"]
            ],
            "output": dict(template["output"]),
        }

    def preflight_for_conflict_state(self, conflict_state: SharedVariableConflictState):
        return stage3_preflight_check(
            [self.instantiate_for_conflict_state(conflict_state)],
            shared_variables={conflict_state.variable_id},
        )

    def metadata(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "operator_name": self.operator_name,
            "template_id": self.template_id,
            "schema_version": self.payload["dsl_schema_version"],
            "source": "frozen_artifact_registry",
            "artifact_source": self.source,
            "artifact_path": _display_path(self.artifact_path),
            "artifact_fingerprint_sha256": self.artifact_fingerprint_sha256,
            "template_fingerprint_sha256": self.artifact_fingerprint_sha256,
            "target_scope": self.target_scope,
            "frozen": self.frozen,
            "no_llm": self.no_llm,
            "no_evolution": self.no_evolution,
            "no_optimizer": self.no_optimizer,
            "no_objective_evaluation": self.no_objective_evaluation,
            "no_test_feedback": self.no_test_feedback,
            "test_mode_allowed": self.test_mode_allowed,
        }


def compute_artifact_fingerprint(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def load_operator_registry(
    registry_path: Path | str = DEFAULT_STAGE2_5_REGISTRY_PATH,
) -> OperatorRegistry:
    path = Path(registry_path)
    entries: list[OperatorRegistryEntry] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            continue
        row = json.loads(line)
        artifact_path = _resolve_repo_path(row["artifact_path"])
        artifact = load_frozen_operator_artifact(artifact_path)
        if artifact.artifact_id != row["artifact_id"]:
            raise ValueError(
                f"registry artifact_id mismatch on line {line_number}: {row['artifact_id']}"
            )
        entries.append(
            OperatorRegistryEntry(
                artifact_id=artifact.artifact_id,
                artifact_path=artifact.artifact_path,
                operator_name=artifact.operator_name,
                source=artifact.source,
                target_scope=artifact.target_scope,
                artifact_fingerprint_sha256=artifact.artifact_fingerprint_sha256,
                no_llm=artifact.no_llm,
                no_evolution=artifact.no_evolution,
                no_test_feedback=artifact.no_test_feedback,
                frozen=artifact.frozen,
            )
        )
    return OperatorRegistry(registry_path=path, entries=tuple(entries))


def load_frozen_operator_artifact(
    artifact_path: Path | str = DEFAULT_STAGE2_5_ARTIFACT_PATH,
) -> FrozenOperatorArtifact:
    path = Path(artifact_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return load_operator_artifact_payload(payload, artifact_path=path)


def load_operator_artifact_payload(
    payload: Mapping[str, Any], artifact_path: Path | str
) -> FrozenOperatorArtifact:
    _validate_artifact_payload(payload)
    path = Path(artifact_path)
    return FrozenOperatorArtifact(
        artifact_path=path,
        payload=dict(payload),
        artifact_fingerprint_sha256=compute_artifact_fingerprint(payload),
    )


def _validate_artifact_payload(payload: Mapping[str, Any]) -> None:
    required = {
        "artifact_schema_version",
        "artifact_id",
        "operator_name",
        "source",
        "stage_created",
        "template_id",
        "target_scope",
        "dsl_schema_version",
        "provenance",
        "split_policy",
        "ast_template",
    }
    missing = required - set(payload)
    if missing:
        raise ValueError(f"operator artifact missing fields: {sorted(missing)}")
    if payload["artifact_schema_version"] != ARTIFACT_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported artifact_schema_version: {payload['artifact_schema_version']}"
        )
    if payload["dsl_schema_version"] != DSL_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported dsl_schema_version: {payload['dsl_schema_version']}"
        )
    if payload["target_scope"] != "shared_variables_only":
        raise ValueError("operator artifact target_scope must be shared_variables_only")

    provenance = _require_mapping(payload["provenance"], "provenance")
    for key in (
        "frozen",
        "no_llm",
        "no_evolution",
        "no_optimizer",
        "no_objective_evaluation",
        "no_arbitrary_executable_code",
    ):
        if provenance.get(key) is not True:
            raise ValueError(f"operator artifact provenance must set {key}=true")

    split_policy = _require_mapping(payload["split_policy"], "split_policy")
    if split_policy.get("no_test_feedback") is not True:
        raise ValueError(
            "operator artifact split_policy must set no_test_feedback=true"
        )
    if split_policy.get("no_tuning_on_test") is not True:
        raise ValueError(
            "operator artifact split_policy must set no_tuning_on_test=true"
        )
    if split_policy.get("test_mode_allowed") is not True:
        raise ValueError(
            "operator artifact split_policy must set test_mode_allowed=true"
        )

    template = _require_mapping(payload["ast_template"], "ast_template")
    if not isinstance(template.get("operator_id_template"), str):
        raise ValueError("operator artifact ast_template requires operator_id_template")
    if not isinstance(template.get("nodes"), list) or not template["nodes"]:
        raise ValueError(
            "operator artifact ast_template nodes must be a non-empty list"
        )
    if not isinstance(template.get("output"), Mapping):
        raise ValueError("operator artifact ast_template output must be a mapping")


def _replace_template_placeholders(
    value: Any, variable_id: int, lower: float, upper: float
) -> Any:
    if value == "$shared_variable":
        return variable_id
    if value == "$lower_bound":
        return lower
    if value == "$upper_bound":
        return upper
    if isinstance(value, Mapping):
        return {
            str(key): _replace_template_placeholders(item, variable_id, lower, upper)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _replace_template_placeholders(item, variable_id, lower, upper)
            for item in value
        ]
    return value


def _require_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"operator artifact field must be a mapping: {field_name}")
    return value


def _resolve_repo_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()
