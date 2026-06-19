import numpy as np
import pytest

from loco.benchmarks.metabox_adapter import (
    MetaBoxImportError,
    MetaBoxProblemAdapter,
    require_metaevobox,
)


class FakeMetaBoxProblem:
    dim = 4
    lb = -2.0
    ub = 3.0
    opt = 0.0
    optimum = 0.0
    numevals = 0

    def func(self, x):
        self.numevals += x.shape[0]
        return np.sum(np.asarray(x, dtype=float) ** 2, axis=1)


def test_metabox_import_error_is_clear_when_unavailable(monkeypatch) -> None:
    def fake_import(_name):
        raise ModuleNotFoundError("no module named metaevobox")

    monkeypatch.setattr("importlib.import_module", fake_import)

    with pytest.raises(MetaBoxImportError, match="metaevobox"):
        require_metaevobox()


def test_metabox_adapter_wraps_problem_without_modifying_it() -> None:
    raw = FakeMetaBoxProblem()
    adapter = MetaBoxProblemAdapter(
        raw,
        grouping=[[0, 1], [1, 2]],
        metadata={"source": "fake-metabox"},
    )

    assert adapter.dimension() == 4
    lower, upper = adapter.bounds()
    assert lower.shape == (4,)
    assert upper.shape == (4,)
    assert adapter.evaluate(np.zeros(4)) == 0.0
    assert adapter.fe_count == 1
    assert raw.numevals == 1
    assert adapter.shared_variables() == {1}
    assert adapter.metadata()["source"] == "fake-metabox"
