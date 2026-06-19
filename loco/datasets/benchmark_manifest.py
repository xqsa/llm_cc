"""Frozen benchmark manifest schema for LOCO-LSGO."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class BenchmarkManifestEntry:
    name: str
    source: str
    function_id: int | None
    dimension: int
    topology: str
    overlap_ratio: float
    split: str
    seed: int | None
    grouping_source: str
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if not data["extra"]:
            data.pop("extra")
        return data


@dataclass
class BenchmarkManifest:
    name: str
    entries: list[BenchmarkManifestEntry]
    frozen: bool = True
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "frozen": self.frozen,
            "entries": [entry.to_dict() for entry in self.entries],
        }

