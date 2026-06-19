"""Controlled synthetic overlap structures for LOCO-specific metadata tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .overlap_metadata import OverlapMetadata, build_overlap_metadata
from .problem_interface import LSGOProblem


@dataclass(frozen=True)
class SyntheticOverlapStructure:
    groups: list[list[int]]
    metadata: OverlapMetadata
    topology_graph: dict[str, Any]
    generation_config: dict[str, Any]


def _topology_edges(
    num_groups: int, topology: str, rng: np.random.Generator
) -> list[tuple[int, int]]:
    if topology == "line":
        return [(i, i + 1) for i in range(num_groups - 1)]
    if topology == "ring":
        return [(i, i + 1) for i in range(num_groups - 1)] + [(num_groups - 1, 0)]
    if topology == "random_graph":
        edges = set()
        for i in range(num_groups - 1):
            edges.add((i, i + 1))
        target_edges = max(num_groups, int(num_groups * 1.5))
        while len(edges) < target_edges:
            a, b = sorted(rng.choice(num_groups, size=2, replace=False).tolist())
            edges.add((int(a), int(b)))
        return sorted(edges)
    raise ValueError("topology must be one of: line, ring, random_graph.")


def generate_synthetic_overlap(
    dimension: int,
    num_groups: int,
    base_group_size: int,
    overlap_ratio: float,
    topology: str,
    seed: int,
    allow_variable_overlap_degree: bool = False,
    max_overlap_degree: int = 2,
) -> SyntheticOverlapStructure:
    """Generate deterministic groups with an overlap ratio close to target."""

    if dimension <= 0 or num_groups <= 1 or base_group_size <= 0:
        raise ValueError("dimension, num_groups, and base_group_size must be positive.")
    if not 0.0 <= overlap_ratio <= 1.0:
        raise ValueError("overlap_ratio must be in [0, 1].")
    if max_overlap_degree < 2:
        raise ValueError("max_overlap_degree must be at least 2.")

    rng = np.random.default_rng(seed)
    target_shared = int(round(dimension * overlap_ratio))
    tolerance = max(int(round(0.02 * dimension)), 5)
    edges = _topology_edges(num_groups, topology, rng)
    groups = [set() for _ in range(num_groups)]

    shared_indices = np.arange(target_shared, dtype=int)
    for index, variable in enumerate(shared_indices):
        edge = edges[index % len(edges)]
        groups[edge[0]].add(int(variable))
        groups[edge[1]].add(int(variable))
        if allow_variable_overlap_degree and max_overlap_degree > 2 and index % 3 == 0:
            groups[(edge[1] + 1) % num_groups].add(int(variable))

    cursor = target_shared
    for group_id in range(num_groups):
        while len(groups[group_id]) < base_group_size and cursor < dimension:
            groups[group_id].add(cursor)
            cursor += 1

    for group_id in range(num_groups):
        if not groups[group_id] and cursor < dimension:
            groups[group_id].add(cursor)
            cursor += 1

    normalized = [sorted(group) for group in groups]
    metadata = build_overlap_metadata(
        normalized,
        dimension=dimension,
        topology=topology,
        grouping_source="synthetic_overlap_generator",
        grouping_confidence="high",
    )
    if abs(metadata.overlap_ratio - overlap_ratio) > tolerance / dimension:
        raise ValueError("Generated overlap ratio is outside tolerance.")

    return SyntheticOverlapStructure(
        groups=normalized,
        metadata=metadata,
        topology_graph={"topology": topology, "edges": edges},
        generation_config={
            "dimension": dimension,
            "num_groups": num_groups,
            "base_group_size": base_group_size,
            "overlap_ratio": overlap_ratio,
            "seed": seed,
            "allow_variable_overlap_degree": allow_variable_overlap_degree,
            "max_overlap_degree": max_overlap_degree,
        },
    )


class SyntheticOverlapProblem(LSGOProblem):
    """Simple controlled synthetic supplement using a sphere objective."""

    def __init__(self, structure: SyntheticOverlapStructure, name: str):
        self.structure = structure
        self.name = name

    def evaluate(self, x: np.ndarray) -> float:
        vector = np.asarray(x, dtype=float)
        if vector.shape != (self.dimension(),):
            raise ValueError(
                f"Expected x shape ({self.dimension()},), got {vector.shape}."
            )
        return float(np.sum(vector * vector))

    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        return np.full(self.dimension(), -100.0), np.full(self.dimension(), 100.0)

    def dimension(self) -> int:
        return int(self.structure.generation_config["dimension"])

    def optimum_value(self) -> float | None:
        return 0.0

    def grouping(self) -> list[list[int]] | None:
        return [list(group) for group in self.structure.groups]

    def shared_variables(self) -> set[int]:
        return set(self.structure.metadata.shared_variables)

    def overlap_degree(self) -> dict[int, int]:
        return dict(self.structure.metadata.overlap_degree)

    def metadata(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "source": "synthetic_overlap",
            "topology": self.structure.metadata.topology,
            "overlap_ratio": self.structure.metadata.overlap_ratio,
            "grouping_source": self.structure.metadata.grouping_source,
            "grouping_confidence": self.structure.metadata.grouping_confidence,
            "objective": "sphere_controlled_supplement",
        }
