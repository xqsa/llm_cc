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


class FakeF12Problem:
    ID = 12
    dim = 1000
    lb = -100.0
    ub = 100.0
    opt = 0.0

    def func(self, x):
        return np.sum(x * x, axis=1)


class FakeOverlapProblem:
    dim = 1000
    dimension = 905
    lb = -100.0
    ub = 100.0
    opt = 0.0
    s_size = 20
    overlap = 5
    s = np.array(
        [
            50,
            50,
            25,
            25,
            100,
            100,
            25,
            25,
            50,
            25,
            100,
            25,
            100,
            50,
            25,
            25,
            25,
            100,
            50,
            25,
        ]
    )
    Pvector = np.arange(905)

    def func(self, x):
        return np.sum(x * x, axis=1)


class FakeF13Problem(FakeOverlapProblem):
    ID = 13


class FakeF14Problem(FakeOverlapProblem):
    ID = 14


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


def test_f13_f14_metadata_records_formula_and_api_dimensions() -> None:
    import loco.benchmarks.cec2013lsgo_metabox as module

    class FakeModule:
        F13 = FakeF13Problem
        F14 = FakeF14Problem

    original = module._import_cec2013lsgo_module
    module._import_cec2013lsgo_module = lambda: FakeModule
    try:
        f13 = load_cec2013lsgo_problem(13)
        f14 = load_cec2013lsgo_problem(14)
    finally:
        module._import_cec2013lsgo_module = original

    for problem in (f13, f14):
        metadata = problem.metadata()
        groups = problem.grouping()

        assert metadata["D_formula"] == 905
        assert metadata["D_api"] == 1000
        assert metadata["overlap_size"] == 5
        assert metadata["grouping_status"] == "available"
        assert metadata["grouping_source"] == "cec2013lsgo_f13_f14_pvector_s_overlap"
        assert len(groups) == 20
        assert len(problem.shared_variables()) == 95
        assert np.isclose(metadata["overlap_ratio"], 95 / 905)

    assert f13.metadata()["overlap_semantics"] == "conforming_overlap"
    assert f14.metadata()["overlap_semantics"] == "conflicting_overlap"


def test_f12_metadata_does_not_require_f13_f14_pvector_rule() -> None:
    import loco.benchmarks.cec2013lsgo_metabox as module

    class FakeModule:
        F12 = FakeF12Problem

    original = module._import_cec2013lsgo_module
    module._import_cec2013lsgo_module = lambda: FakeModule
    try:
        problem = load_cec2013lsgo_problem(12)
    finally:
        module._import_cec2013lsgo_module = original

    metadata = problem.metadata()
    assert problem.dimension() == 1000
    assert problem.grouping() is None
    assert problem.shared_variables() == set()
    assert metadata["D_formula"] == 1000
    assert metadata["D_api"] == 1000
    assert metadata["grouping_status"] == "unavailable"
    assert metadata["grouping_source"] == "unavailable"
    assert metadata["overlap_semantics"] == "rosenbrock_chain_overlap"
    assert "pvector" not in metadata["grouping_source"]


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
