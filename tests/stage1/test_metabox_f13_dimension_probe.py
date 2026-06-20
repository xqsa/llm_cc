import pytest

from loco.benchmarks.metabox_adapter import MetaBoxImportError


def test_metabox_f13_dimension_probe_reports_internal_shape_contract() -> None:
    from scripts.stage1.probe_metabox_f13_dimension import run_probe

    result = run_probe(seed=23)
    if result["status"] == "SKIP":
        pytest.skip(result["summary"])

    assert result["stage"] == "1.8"
    assert result["status"] == "PARTIAL"
    assert result["claim_boundary"]["adapter_modified"] is False
    assert result["claim_boundary"]["objective_reimplemented"] is False
    assert result["claim_boundary"]["padding_applied"] is False

    f13 = result["functions"]["F13"]
    f14 = result["functions"]["F14"]
    assert f13["construction_ok"] is True
    assert f14["construction_ok"] is True
    assert f13["dimension"] == 905
    assert f13["dim"] == 1000
    assert f13["ovector_shape"] == [1000]
    assert f13["evaluate_905"]["ok"] is False
    assert "905" in f13["evaluate_905"]["error"]
    assert "1000" in f13["evaluate_905"]["error"]
    assert f13["evaluate_1000"]["ok"] is True

    assert f14["dimension"] == 905
    assert f14["dim"] == 1000
    assert f14["ovector_vec_len"] == 20
    assert f14["evaluate_905"]["ok"] is True
    assert f14["evaluate_1000"]["ok"] is True
    assert result["diagnosis"]["f14_dual_input_eval_compatible"] is True


def test_metabox_f13_dimension_probe_cleanly_skips_when_metabox_unavailable(
    monkeypatch,
) -> None:
    from scripts.stage1 import probe_metabox_f13_dimension as probe

    def _raise_import_error():
        raise MetaBoxImportError("metaevobox missing")

    monkeypatch.setattr(
        probe, "_import_cec2013lsgo_numpy_benchmark_only", _raise_import_error
    )

    result = probe.run_probe(seed=23)

    assert result["status"] == "SKIP"
    assert "metaevobox missing" in result["summary"]
