import numpy as np
import pytest

from loco.benchmarks.overlap_metadata import build_overlap_metadata


def test_overlap_metadata_computes_shared_variables_degree_and_incidence() -> None:
    metadata = build_overlap_metadata(
        groups=[[0, 1, 2], [2, 3], [3, 4]],
        dimension=5,
        topology="line",
        grouping_source="unit-test",
    )

    assert metadata.shared_variables == frozenset({2, 3})
    assert metadata.overlap_degree == {0: 1, 1: 1, 2: 2, 3: 2, 4: 1}
    assert metadata.incidence_matrix.shape == (5, 3)
    assert metadata.incidence_matrix[2, 0] == 1
    assert metadata.incidence_matrix[2, 1] == 1
    assert np.isclose(metadata.overlap_ratio, 2 / 5)


def test_overlap_metadata_rejects_invalid_groups() -> None:
    with pytest.raises(ValueError, match="out of bounds"):
        build_overlap_metadata([[0, 5]], dimension=5, topology="line", grouping_source="bad")

    with pytest.raises(ValueError, match="non-empty"):
        build_overlap_metadata([[]], dimension=5, topology="line", grouping_source="bad")
