from pathlib import Path

from loco.benchmarks.benchmark_registry import BenchmarkRegistry, load_manifest
from loco.datasets.split_generator import generate_default_manifest, write_manifest


def test_registry_lists_and_loads_synthetic_manifest_entries(tmp_path: Path) -> None:
    manifest = generate_default_manifest()
    synthetic_entries = [
        entry for entry in manifest.entries if entry.source == "synthetic_overlap"
    ][:3]
    manifest.entries = synthetic_entries
    path = tmp_path / "manifest.json"
    write_manifest(manifest, path)

    loaded = load_manifest(path)
    registry = BenchmarkRegistry(loaded)

    names = registry.list_problems()
    assert len(names) == 3
    problem = registry.get_problem(names[0])
    assert problem.dimension() == synthetic_entries[0].dimension
    assert problem.metadata()["source"] == "synthetic_overlap"
    assert "function_id" not in problem.operator_view()
