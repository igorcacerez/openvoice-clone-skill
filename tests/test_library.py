import json
import zipfile
from pathlib import Path

import numpy as np
import pytest

from openvoice_skill.config import SkillError
from openvoice_skill.storage import Library, name_key


def stage(config, tmp_path: Path, suffix="one"):
    root = tmp_path / suffix
    root.mkdir()
    (root / "reference.wav").write_bytes(b"unit-test-placeholder-not-real-audio")
    np.save(root / "speaker.npy", np.ones((1, 256, 1), dtype=np.float32), allow_pickle=False)
    return root


def test_persistence_names_and_conflicts(config, tmp_path):
    lib = Library(config)
    first = lib.commit("Example", stage(config, tmp_path), {"language": "pt-BR"})
    assert Library(config).get("example")["id"] == first["id"]
    with pytest.raises(SkillError, match="existe"):
        lib.commit("EXAMPLE", stage(config, tmp_path, "two"), {})
    lib.validate(first)
    renamed = lib.rename("Example", "New name")
    assert renamed["id"] == first["id"]
    with pytest.raises(SkillError, match="encontrada"):
        lib.get("Example")


def test_updates_preserve_previous_revision_and_delete_is_recoverable(config, tmp_path):
    lib = Library(config)
    first = lib.commit("Example", stage(config, tmp_path), {})
    second = lib.commit("Example", stage(config, tmp_path, "new"), {}, existing="Example")
    assert first["id"] == second["id"]
    assert first["revision"] != second["revision"]
    assert (lib.folder(first) / "speaker.npy").exists()
    result = lib.delete("Example")
    assert not lib.list()
    assert (Path(result["recoverable_at"]) / first["revision"] / "reference.wav").exists()


def test_checksum_detection(config, tmp_path):
    lib = Library(config)
    voice = lib.commit("Example", stage(config, tmp_path), {})
    (lib.folder(voice) / "speaker.npy").write_bytes(b"tampered")
    with pytest.raises(SkillError, match="Integridade"):
        lib.validate(voice)


def test_export_import_requires_consent_and_new_identity(config, tmp_path):
    lib = Library(config)
    first = lib.commit("Example", stage(config, tmp_path), {})
    archive = tmp_path / "profile.zip"
    lib.export("Example", archive)
    with pytest.raises(SkillError, match="autorizacao"):
        lib.import_profile(archive, tmp_path / "import-denied", "Imported", False)
    imported = lib.import_profile(archive, tmp_path / "import", "Imported", True)
    assert imported["id"] != first["id"]
    lib.validate(imported)
    with pytest.raises(SkillError, match="existe"):
        lib.export("Example", archive)


def test_zip_traversal_is_rejected(config, tmp_path):
    lib = Library(config)
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as out:
        out.writestr("../outside", "bad")
    with pytest.raises(SkillError, match="ZIP invalido"):
        lib.import_profile(archive, tmp_path / "import", "Example", True)
    assert not (tmp_path / "outside").exists()


def test_import_refuses_untrusted_pickle_and_malformed_embedding(config, tmp_path):
    from openvoice_skill.cloner import sha256
    lib = Library(config)
    root = stage(config, tmp_path)
    np.save(root / "speaker.npy", np.array(["not a tensor"], dtype=object), allow_pickle=True)
    metadata = {"engine": "openvoice-v2", "name": "Example",
                "checksums": {file: sha256(root / file) for file in ("reference.wav", "speaker.npy")}}
    archive = tmp_path / "pickle.zip"
    with zipfile.ZipFile(archive, "w") as out:
        out.writestr("metadata.json", json.dumps(metadata))
        for file in ("reference.wav", "speaker.npy"):
            out.write(root / file, file)
    with pytest.raises(ValueError, match="allow_pickle"):
        lib.import_profile(archive, tmp_path / "import", "Example", True)


def test_history_does_not_store_narration_text(config):
    lib = Library(config)
    identifier = lib.record("example", "running", {"characters": 100, "text_sha256": "hash"})
    lib.record("example", "complete", {"characters": 100, "text_sha256": "hash"}, identifier)
    rows = lib.history()
    assert len(rows) == 1
    assert rows[0]["status"] == "complete"
    assert "text" not in rows[0]["metadata"]


@pytest.mark.parametrize("value", ["", " ", "x" * 101, "bad\nname"])
def test_invalid_names(value):
    with pytest.raises(SkillError):
        name_key(value)
