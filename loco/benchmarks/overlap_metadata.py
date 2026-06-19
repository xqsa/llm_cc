"""Overlap grouping metadata for LOCO-LSGO."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class OverlapMetadata:
    groups: tuple[tuple[int, ...], ...]
    shared_variables: frozenset[int]
    overlap_degree: dict[int, int]
    incidence_matrix: np.ndarray
    topology: str
    overlap_ratio: float
    grouping_source: str
    grouping_confidence: str


def build_overlap_metadata(
    groups,
    dimension: int,
    topology: str,
    grouping_source: str,
    grouping_confidence: str = "high",
) -> OverlapMetadata:
    """Build validated overlap metadata from groups."""

    if not isinstance(dimension, int) or dimension <= 0:
        raise ValueError("dimension must be a positive integer.")

    normalized: list[tuple[int, ...]] = []
    degree = {i: 0 for i in range(dimension)}

    for raw_group in groups:
        group = tuple(int(index) for index in raw_group)
        if not group:
            raise ValueError("Each group must be non-empty.")
        if len(set(group)) != len(group):
            raise ValueError("Duplicate indices inside a group are not allowed.")
        for index in group:
            if index < 0 or index >= dimension:
                raise ValueError(
                    f"Group index {index} out of bounds for D={dimension}."
                )
            degree[index] += 1
        normalized.append(group)

    incidence = np.zeros((dimension, len(normalized)), dtype=np.int8)
    for column, group in enumerate(normalized):
        incidence[list(group), column] = 1

    computed_degree = {i: int(incidence[i].sum()) for i in range(dimension)}
    if computed_degree != degree:
        raise ValueError("overlap_degree computation mismatch.")

    shared = frozenset(i for i, count in degree.items() if count >= 2)
    return OverlapMetadata(
        groups=tuple(normalized),
        shared_variables=shared,
        overlap_degree=degree,
        incidence_matrix=incidence,
        topology=topology,
        overlap_ratio=len(shared) / dimension,
        grouping_source=grouping_source,
        grouping_confidence=grouping_confidence,
    )
