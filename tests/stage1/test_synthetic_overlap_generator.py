import numpy as np

from loco.benchmarks.synthetic_overlap_generator import generate_synthetic_overlap


def test_synthetic_generator_is_seed_reproducible() -> None:
    a = generate_synthetic_overlap(100, 10, 12, 0.10, "line", seed=7)
    b = generate_synthetic_overlap(100, 10, 12, 0.10, "line", seed=7)

    assert a.groups == b.groups
    assert a.metadata.shared_variables == b.metadata.shared_variables
    assert np.array_equal(a.metadata.incidence_matrix, b.metadata.incidence_matrix)


def test_synthetic_overlap_ratio_is_close_to_target() -> None:
    generated = generate_synthetic_overlap(500, 20, 30, 0.20, "ring", seed=3)

    error = abs(generated.metadata.overlap_ratio - 0.20)

    assert error <= max(0.02, 5 / 500)
    assert generated.metadata.incidence_matrix.shape == (500, 20)


def test_line_ring_and_random_graph_topologies_are_available() -> None:
    line = generate_synthetic_overlap(100, 8, 15, 0.10, "line", seed=1)
    ring = generate_synthetic_overlap(100, 8, 15, 0.10, "ring", seed=1)
    random_graph = generate_synthetic_overlap(100, 8, 15, 0.10, "random_graph", seed=1)

    assert line.topology_graph["edges"][0] == (0, 1)
    assert (7, 0) in ring.topology_graph["edges"]
    assert random_graph.topology_graph == generate_synthetic_overlap(
        100, 8, 15, 0.10, "random_graph", seed=1
    ).topology_graph
