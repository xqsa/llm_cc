from pathlib import Path

from loco.datasets.split_generator import generate_default_manifest, write_manifest


def test_default_split_manifest_is_frozen_and_has_no_name_leakage() -> None:
    manifest = generate_default_manifest()
    names_by_split = {}
    for entry in manifest.entries:
        names_by_split.setdefault(entry.split, set()).add(entry.name)

    assert {"train", "val", "test"}.issubset(names_by_split)
    assert names_by_split["train"].isdisjoint(names_by_split["val"])
    assert names_by_split["train"].isdisjoint(names_by_split["test"])
    assert names_by_split["val"].isdisjoint(names_by_split["test"])


def test_manifest_can_be_written_with_stable_order(tmp_path: Path) -> None:
    manifest = generate_default_manifest()
    path = tmp_path / "manifest.json"

    write_manifest(manifest, path)
    first = path.read_text(encoding="utf-8")
    write_manifest(manifest, path)
    second = path.read_text(encoding="utf-8")

    assert first == second
