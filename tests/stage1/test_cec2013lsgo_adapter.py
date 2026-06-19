import numpy as np
from loco.benchmarks.cec2013lsgo_metabox import (
    load_cec2013lsgo_overlap_suite,
    load_cec2013lsgo_problem,
    reconstruct_cec2013lsgo_grouping,
)
from loco.benchmarks.metabox_adapter import MetaBoxImportError


class FakeCECProblem:
    ID = 13
    dim = 10
    dimension = 10
    lb = -100.0
    ub = 100.0
    opt = 0.0
    s_size = 3
    overlap = 2
    s = np.array([4, 4, 4])
    Pvector = np.arange(10)

    def func(self, x):
        return np.sum(x * x, axis=1)


def test_reconstruct_cec2013lsgo_grouping_from_pvector_overlap() -> None:
    groups, source, confidence = reconstruct_cec2013lsgo_grouping(FakeCECProblem())

    assert groups == [[0, 1, 2, 3], [2, 3, 4, 5], [4, 5, 6, 7]]
    assert source == "cec2013lsgo_pvector_overlap"
    assert confidence == "high"


def test_cec2013lsgo_loader_has_clear_error_without_metabox() -> None:
    import loco.benchmarks.cec2013lsgo_metabox as module

    def unavailable():
        raise MetaBoxImportError("metaevobox unavailable")

    original = module._import_cec2013lsgo_module
    module._import_cec2013lsgo_module = unavailable
    try:
        try:
            load_cec2013lsgo_problem(13)
        except MetaBoxImportError as exc:
            assert "metaevobox" in str(exc)
        else:
            raise AssertionError("Expected MetaBoxImportError")
    finally:
        module._import_cec2013lsgo_module = original


def test_cec2013lsgo_loader_wraps_fake_metabox_problem() -> None:
    import loco.benchmarks.cec2013lsgo_metabox as module

    class FakeModule:
        F13 = FakeCECProblem

    original = module._import_cec2013lsgo_module
    module._import_cec2013lsgo_module = lambda: FakeModule
    try:
        problem = load_cec2013lsgo_problem(13)
    finally:
        module._import_cec2013lsgo_module = original

    assert problem.dimension() == 10
    assert isinstance(problem.evaluate(np.zeros(problem.dimension())), float)
    assert problem.shared_variables() == {2, 3, 4, 5}


def test_overlap_suite_targets_f12_f13_f14_or_reports_metabox_unavailable() -> None:
    import loco.benchmarks.cec2013lsgo_metabox as module

    class FakeModule:
        F12 = FakeCECProblem
        F13 = FakeCECProblem
        F14 = FakeCECProblem

    original = module._import_cec2013lsgo_module
    module._import_cec2013lsgo_module = lambda: FakeModule
    try:
        suite = load_cec2013lsgo_overlap_suite()
    finally:
        module._import_cec2013lsgo_module = original

    assert [p.metadata()["function_id"] for p in suite] == [12, 13, 14]
