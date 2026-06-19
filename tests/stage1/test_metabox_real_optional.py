import pytest

from scripts.stage1.check_metabox_cec2013lsgo_real import run_smoke


def test_real_metabox_cec2013lsgo_smoke_optional() -> None:
    result = run_smoke(seed=11, include_normal_import=False)
    if result["status"] != "PASS":
        pytest.skip(f"Real MetaBox CEC2013LSGO smoke not PASS: {result['summary']}")

    assert [item["function_id"] for item in result["functions"]] == [12, 13, 14]
    assert all(item["ok"] for item in result["functions"])
