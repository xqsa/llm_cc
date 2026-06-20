"""Typed coordination-operator AST boundary for Stage 2.2.

This module defines data-only AST structures and validation helpers. It does
not execute operators, call LLMs, run evolution, or implement an optimizer.
"""

from __future__ import annotations

import json
import re
import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence


DSL_SCHEMA_VERSION = "loco.dsl.v1"
DEFAULT_MAX_NODES = 32
DEFAULT_MAX_DEPTH = 8


class CoordinationNodeKind(str, Enum):
    CONSENSUS = "consensus"
    WEIGHTED_CONSENSUS = "weighted_consensus"
    BEST_REWARD_SELECT = "best_reward_select"
    PROJECTION = "projection"
    DAMPENING = "dampening"
    REWEIGHTING = "reweighting"
    CLIP = "clip"
    REPAIR = "repair"


ALLOWED_NODE_KINDS = frozenset(kind.value for kind in CoordinationNodeKind)
FORBIDDEN_NODE_KINDS = frozenset(
    {
        "optimizer",
        "de_optimizer",
        "cma_es_optimizer",
        "pso_optimizer",
        "shade_optimizer",
        "lshade_optimizer",
        "controller",
        "scheduler",
        "optimizer_selection",
        "base_optimizer_replacement",
    }
)
FORBIDDEN_METADATA_KEYS = frozenset(
    {
        "function_id",
        "benchmark_name",
        "true_optimum_location",
        "test_set_metadata",
        "future_evaluations",
        "hidden_test_information",
    }
)
ALLOWED_TOP_LEVEL_FIELDS = frozenset(
    {"schema_version", "operator_id", "nodes", "output"}
)
ALLOWED_NODE_FIELDS = frozenset({"id", "kind", "target", "inputs"})
ALLOWED_TARGET_FIELDS = frozenset({"variable_id"})
ALLOWED_OUTPUT_FIELDS = frozenset({"source"})
ALLOWED_INPUT_FIELDS = frozenset(
    {
        "source",
        "sources",
        "temperature",
        "damping_strength",
        "weights",
        "lower",
        "upper",
        "projection",
        "mode",
        "reward_key",
    }
)

_EXECUTABLE_CODE_PATTERN = re.compile(
    r"(__import__\s*\(|\beval\s*\(|\bexec\s*\(|\blambda\b|"
    r"\bimport\s+\w+|\bdef\s+\w+\s*\(|\bclass\s+\w+\s*\(|"
    r"\.system\s*\(|\bsubprocess\b)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DSLTarget:
    variable_id: int

    def to_dict(self) -> dict[str, int]:
        return {"variable_id": self.variable_id}


@dataclass(frozen=True)
class DSLNode:
    id: str
    kind: CoordinationNodeKind
    target: DSLTarget
    inputs: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "target": self.target.to_dict(),
            "inputs": _canonicalize_value(self.inputs),
        }


@dataclass(frozen=True)
class CoordinationOperatorAST:
    schema_version: str
    operator_id: str
    nodes: tuple[DSLNode, ...]
    output_source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "operator_id": self.operator_id,
            "nodes": [node.to_dict() for node in self.nodes],
            "output": {"source": self.output_source},
        }


@dataclass(frozen=True)
class DSLValidationReport:
    schema_version: str
    operator_id: str
    node_count: int
    max_depth: int
    target_variables: frozenset[int]


@dataclass(frozen=True)
class Stage3AcceptedCandidate:
    candidate_id: str
    ast: CoordinationOperatorAST
    serialized_ast: str
    fingerprint_sha256: str


@dataclass(frozen=True)
class Stage3RejectedCandidate:
    candidate_id: str
    reject_reason: str


@dataclass(frozen=True)
class Stage3PreflightReport:
    total_count: int
    accepted: tuple[Stage3AcceptedCandidate, ...]
    rejected: tuple[Stage3RejectedCandidate, ...]

    @property
    def accepted_count(self) -> int:
        return len(self.accepted)

    @property
    def rejected_count(self) -> int:
        return len(self.rejected)


def load_coordination_ast(payload: Mapping[str, Any]) -> CoordinationOperatorAST:
    """Load and validate the static AST schema without executing anything."""

    if not isinstance(payload, Mapping):
        raise ValueError("Coordination AST payload must be a mapping.")
    _reject_unknown_fields(payload, ALLOWED_TOP_LEVEL_FIELDS, "top-level")

    schema_version = _require_string(payload, "schema_version")
    if schema_version != DSL_SCHEMA_VERSION:
        raise ValueError(f"Unsupported DSL schema_version: {schema_version}")

    operator_id = _require_string(payload, "operator_id")
    _reject_forbidden_metadata_and_code(operator_id)
    nodes_payload = payload.get("nodes")
    if not isinstance(nodes_payload, Sequence) or isinstance(
        nodes_payload, (str, bytes)
    ):
        raise ValueError("Coordination AST nodes must be a list.")
    if not nodes_payload:
        raise ValueError("Coordination AST must contain at least one node.")

    nodes = tuple(_load_node(node_payload) for node_payload in nodes_payload)
    output = payload.get("output")
    if not isinstance(output, Mapping):
        raise ValueError("Coordination AST output must be a mapping.")
    _reject_unknown_fields(output, ALLOWED_OUTPUT_FIELDS, "output")
    _reject_forbidden_metadata_and_code(output)
    output_source = _require_string(output, "source")

    return CoordinationOperatorAST(
        schema_version=schema_version,
        operator_id=operator_id,
        nodes=nodes,
        output_source=output_source,
    )


def validate_coordination_ast(
    ast: CoordinationOperatorAST,
    shared_variables: set[int] | frozenset[int],
    *,
    max_nodes: int = DEFAULT_MAX_NODES,
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> DSLValidationReport:
    """Validate Stage 2.2 DSL boundaries against known shared variables."""

    if ast.schema_version != DSL_SCHEMA_VERSION:
        raise ValueError(f"Unsupported DSL schema_version: {ast.schema_version}")
    if len(ast.nodes) > max_nodes:
        raise ValueError(
            f"Coordination AST node count {len(ast.nodes)} exceeds max_nodes {max_nodes}."
        )

    shared = frozenset(int(variable_id) for variable_id in shared_variables)
    target_variables = frozenset(node.target.variable_id for node in ast.nodes)
    non_shared_targets = target_variables - shared
    if non_shared_targets:
        raise ValueError(
            "Coordination AST targets non-shared variables: "
            f"{sorted(non_shared_targets)}."
        )

    node_by_id = _validate_node_ids(ast.nodes)
    if ast.output_source not in node_by_id:
        raise ValueError(
            f"Coordination AST output source does not exist: {ast.output_source}"
        )

    depth = _max_depth(ast.output_source, node_by_id)
    if depth > max_depth:
        raise ValueError(
            f"Coordination AST depth {depth} exceeds max_depth {max_depth}."
        )

    return DSLValidationReport(
        schema_version=ast.schema_version,
        operator_id=ast.operator_id,
        node_count=len(ast.nodes),
        max_depth=depth,
        target_variables=target_variables,
    )


def serialize_coordination_ast(ast: CoordinationOperatorAST) -> str:
    """Return deterministic JSON for review, hashing, and frozen artifacts."""

    return json.dumps(ast.to_dict(), sort_keys=True, separators=(",", ":"))


def stage3_preflight_check(
    candidate_payloads: Sequence[Mapping[str, Any]],
    shared_variables: set[int] | frozenset[int],
    *,
    max_nodes: int = DEFAULT_MAX_NODES,
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> Stage3PreflightReport:
    """Check Stage 3 candidate AST payloads before any LLM/evolution runtime.

    The preflight is schema-only and data-only: it loads candidate ASTs,
    validates boundary constraints, and emits deterministic fingerprints for
    accepted candidates. It does not execute operators or evaluate objectives.
    """

    accepted: list[Stage3AcceptedCandidate] = []
    rejected: list[Stage3RejectedCandidate] = []

    for index, payload in enumerate(candidate_payloads):
        candidate_id = _candidate_id_from_payload(payload, index)
        try:
            ast = load_coordination_ast(payload)
            validate_coordination_ast(
                ast,
                shared_variables=shared_variables,
                max_nodes=max_nodes,
                max_depth=max_depth,
            )
        except ValueError as exc:
            rejected.append(
                Stage3RejectedCandidate(
                    candidate_id=candidate_id,
                    reject_reason=str(exc),
                )
            )
            continue

        serialized = serialize_coordination_ast(ast)
        accepted.append(
            Stage3AcceptedCandidate(
                candidate_id=ast.operator_id,
                ast=ast,
                serialized_ast=serialized,
                fingerprint_sha256=hashlib.sha256(
                    serialized.encode("utf-8")
                ).hexdigest(),
            )
        )

    return Stage3PreflightReport(
        total_count=len(candidate_payloads),
        accepted=tuple(accepted),
        rejected=tuple(rejected),
    )


def _load_node(payload: Any) -> DSLNode:
    if not isinstance(payload, Mapping):
        raise ValueError("Coordination AST node must be a mapping.")
    _reject_unknown_fields(payload, ALLOWED_NODE_FIELDS, "node")
    _reject_forbidden_metadata_and_code(payload)

    node_id = _require_string(payload, "id")
    kind_text = _require_string(payload, "kind")
    if kind_text in FORBIDDEN_NODE_KINDS:
        raise ValueError(f"Forbidden DSL node kind: {kind_text}")
    if kind_text not in ALLOWED_NODE_KINDS:
        raise ValueError(f"Unknown DSL node kind: {kind_text}")

    target_payload = payload.get("target")
    if not isinstance(target_payload, Mapping):
        raise ValueError("Coordination AST node target must be a mapping.")
    _reject_unknown_fields(target_payload, ALLOWED_TARGET_FIELDS, "target")
    _reject_forbidden_metadata_and_code(target_payload)
    variable_id = target_payload.get("variable_id")
    if not isinstance(variable_id, int):
        raise ValueError("Coordination AST target variable_id must be an integer.")

    inputs = payload.get("inputs", {})
    if not isinstance(inputs, Mapping):
        raise ValueError("Coordination AST node inputs must be a mapping.")
    _reject_unknown_fields(inputs, ALLOWED_INPUT_FIELDS, "inputs")
    _reject_forbidden_metadata_and_code(inputs)

    return DSLNode(
        id=node_id,
        kind=CoordinationNodeKind(kind_text),
        target=DSLTarget(variable_id=variable_id),
        inputs=_canonicalize_value(inputs),
    )


def _validate_node_ids(nodes: tuple[DSLNode, ...]) -> dict[str, DSLNode]:
    node_by_id: dict[str, DSLNode] = {}
    for node in nodes:
        if node.id in node_by_id:
            raise ValueError(f"Duplicate coordination AST node id: {node.id}")
        node_by_id[node.id] = node
    return node_by_id


def _max_depth(output_source: str, node_by_id: Mapping[str, DSLNode]) -> int:
    visiting: set[str] = set()
    memo: dict[str, int] = {}

    def depth(node_id: str) -> int:
        if node_id not in node_by_id:
            raise ValueError(f"Coordination AST source does not exist: {node_id}")
        if node_id in memo:
            return memo[node_id]
        if node_id in visiting:
            raise ValueError(f"Coordination AST contains a cycle at node: {node_id}")

        visiting.add(node_id)
        sources = _input_sources(node_by_id[node_id].inputs)
        if sources:
            value = 1 + max(depth(source) for source in sources)
        else:
            value = 1
        visiting.remove(node_id)
        memo[node_id] = value
        return value

    return depth(output_source)


def _input_sources(inputs: Mapping[str, Any]) -> tuple[str, ...]:
    sources: list[str] = []
    source = inputs.get("source")
    if source is not None:
        if not isinstance(source, str):
            raise ValueError("Coordination AST input source must be a string.")
        sources.append(source)

    source_list = inputs.get("sources")
    if source_list is not None:
        if not isinstance(source_list, Sequence) or isinstance(
            source_list, (str, bytes)
        ):
            raise ValueError("Coordination AST input sources must be a list.")
        for item in source_list:
            if not isinstance(item, str):
                raise ValueError("Coordination AST input sources must be strings.")
            sources.append(item)
    return tuple(sources)


def _require_string(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Coordination AST field must be a non-empty string: {key}")
    return value


def _reject_unknown_fields(
    payload: Mapping[str, Any], allowed_fields: frozenset[str], scope: str
) -> None:
    unknown_fields = set(payload) - allowed_fields
    if unknown_fields:
        raise ValueError(f"Unknown {scope} fields: {sorted(unknown_fields)}")


def _reject_forbidden_metadata_and_code(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in FORBIDDEN_METADATA_KEYS:
                raise ValueError(
                    f"Coordination AST requested forbidden metadata: {key}"
                )
            if "code" in key.lower() or "callable" in key.lower():
                raise ValueError(
                    f"Coordination AST cannot contain executable code field: {key}"
                )
            _reject_forbidden_metadata_and_code(item)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            _reject_forbidden_metadata_and_code(item)
    elif isinstance(value, str) and _EXECUTABLE_CODE_PATTERN.search(value):
        raise ValueError("Coordination AST cannot contain executable code strings.")


def _canonicalize_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _canonicalize_value(value[key]) for key in sorted(value)}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_canonicalize_value(item) for item in value]
    return value


def _candidate_id_from_payload(payload: Any, index: int) -> str:
    if isinstance(payload, Mapping):
        candidate_id = payload.get("operator_id")
        if isinstance(candidate_id, str) and candidate_id:
            return candidate_id
    return f"candidate_{index}"
