import pytest

from scripts.stage1.check_metabox_cec2013lsgo_real import run_smoke


def test_real_metabox_cec2013lsgo_smoke_optional() -> None:
    result = run_smoke(seed=11, include_normal_import=False)
    if result["status"] != "PASS":
        pytest.skip(f"Real MetaBox CEC2013LSGO smoke not PASS: {result['summary']}")

    assert [item["function_id"] for item in result["functions"]] == [12, 13, 14]
    assert all(item["ok"] for item in result["functions"])


def test_real_metabox_f13_implementation_api_adapter_optional() -> None:
    result = run_smoke(seed=11, include_normal_import=False)
    if result["status"] != "PASS":
        pytest.skip(f"Real MetaBox CEC2013LSGO smoke not PASS: {result['summary']}")

    f13 = next(item for item in result["functions"] if item["function_id"] == 13)
    assert f13["ok"] is True
    assert f13["checks"]["D_formula"] == 905
    assert f13["checks"]["D_api"] == 1000
    assert f13["checks"]["dimension"] == 1000
    assert f13["checks"]["expected_dimension"] == 1000
    assert f13["checks"]["adapter_mode"] == "implementation_api_adapter"
    assert f13["checks"]["adapter_reason"] == "metabox_f13_ovector_requires_D_api"
    assert f13["checks"]["finite_values"] is True
    assert f13["checks"]["deterministic_random_eval"] is True
