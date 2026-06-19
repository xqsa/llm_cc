"""Function-evaluation budget accounting for Stage 2.0."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


_CATEGORY_TO_FIELD = {
    "grouping": "fe_grouping",
    "proposal": "fe_proposal",
    "coordination_extra": "fe_coordination_extra",
    "repair": "fe_repair",
}


@dataclass
class FEBudgetTracker:
    max_fe: int
    fe_grouping: int = 0
    fe_proposal: int = 0
    fe_coordination_extra: int = 0
    fe_repair: int = 0

    def __post_init__(self) -> None:
        if self.max_fe <= 0:
            raise ValueError("max_fe must be positive.")

    @property
    def fe_total(self) -> int:
        return self.fe_grouping + self.fe_proposal + self.fe_coordination_extra + self.fe_repair

    @property
    def remaining_fe(self) -> int:
        return max(0, self.max_fe - self.fe_total)

    @property
    def exhausted(self) -> bool:
        return self.fe_total >= self.max_fe

    def record(self, category: str, count: int = 1) -> None:
        if category not in _CATEGORY_TO_FIELD:
            raise ValueError(f"Unknown FE category: {category}")
        if count < 0:
            raise ValueError("FE count must be nonnegative.")
        if self.fe_total + count > self.max_fe:
            raise RuntimeError("FE budget exhausted; refusing to record evaluations past max_fe.")
        field = _CATEGORY_TO_FIELD[category]
        setattr(self, field, getattr(self, field) + int(count))

    def to_dict(self) -> dict[str, Any]:
        return {
            "fe_grouping": self.fe_grouping,
            "fe_proposal": self.fe_proposal,
            "fe_coordination_extra": self.fe_coordination_extra,
            "fe_repair": self.fe_repair,
            "fe_total": self.fe_total,
            "max_fe": self.max_fe,
            "remaining_fe": self.remaining_fe,
            "exhausted": self.exhausted,
        }
