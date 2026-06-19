"""Benchmark registry for LOCO-LSGO Stage 1."""

from __future__ import annotations

import json
from pathlib import Path

from loco.datasets.benchmark_manifest import BenchmarkManifest, BenchmarkManifestEntry
from loco.datasets.split_generator import manifest_from_dict

from .cec2013lsgo_metabox import load_cec2013lsgo_problem
from .problem_interface import LSGOProblem
from .synthetic_overlap_generator import SyntheticOverlapProblem, generate_synthetic_overlap


class BenchmarkRegistry:
    """Load problems through LOCO interfaces instead of MetaBox internals."""

    def __init__(self, manifest: BenchmarkManifest):
        self.manifest = manifest
        self._entries = {entry.name: entry for entry in manifest.entries}

    def list_problems(self, split: str | None = None) -> list[str]:
        names = [
            entry.name
            for entry in self.manifest.entries
            if split is None or entry.split == split
        ]
        return sorted(names)

    def get_problem(self, name: str) -> LSGOProblem:
        try:
            entry = self._entries[name]
        except KeyError as exc:
            raise KeyError(f"Unknown benchmark problem: {name}") from exc
        return problem_from_manifest_entry(entry)


def load_manifest(path: str | Path) -> BenchmarkManifest:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return manifest_from_dict(data)


def problem_from_manifest_entry(entry: BenchmarkManifestEntry) -> LSGOProblem:
    if entry.source == "metabox_cec2013lsgo":
        if entry.function_id is None:
            raise ValueError("metabox_cec2013lsgo entries require function_id.")
        return load_cec2013lsgo_problem(entry.function_id)
    if entry.source == "synthetic_overlap":
        num_groups = max(4, min(40, entry.dimension // 25))
        base_group_size = max(8, min(entry.dimension, int(entry.dimension / max(num_groups, 1) * 1.5)))
        structure = generate_synthetic_overlap(
            dimension=entry.dimension,
            num_groups=num_groups,
            base_group_size=base_group_size,
            overlap_ratio=entry.overlap_ratio,
            topology=entry.topology,
            seed=entry.seed or 0,
        )
        return SyntheticOverlapProblem(structure, name=entry.name)
    raise ValueError(f"Unsupported benchmark source: {entry.source}")


_DEFAULT_REGISTRY: BenchmarkRegistry | None = None


def configure_default_registry(manifest: BenchmarkManifest) -> None:
    global _DEFAULT_REGISTRY
    _DEFAULT_REGISTRY = BenchmarkRegistry(manifest)


def get_problem(name: str) -> LSGOProblem:
    if _DEFAULT_REGISTRY is None:
        raise RuntimeError("No default benchmark registry configured.")
    return _DEFAULT_REGISTRY.get_problem(name)


def list_problems(split: str | None = None) -> list[str]:
    if _DEFAULT_REGISTRY is None:
        raise RuntimeError("No default benchmark registry configured.")
    return _DEFAULT_REGISTRY.list_problems(split=split)

