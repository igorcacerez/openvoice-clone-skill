"""Opt-in real inference; only a synthetic/public-domain TTS reference is used."""
import os
from pathlib import Path

import pytest
import soundfile as sf

from openvoice_skill.audio import active_speech, probe
from openvoice_skill.config import SkillError
from openvoice_skill.service import Service
from openvoice_skill.storage import Library

pytestmark = [pytest.mark.integration, pytest.mark.skipif(os.environ.get("OPENVOICE_TEST_MODELS") != "1",
                                                        reason="Set OPENVOICE_TEST_MODELS=1 to run real inference")]


def test_real_roundtrip_and_long_narration(config, tmp_path):
    service = Service(config)
    reference = service.tts.synthesize(["Esta é uma voz sintética de teste, criada localmente. Vamos verificar a gravação, a biblioteca persistente e a geração de uma nova narração com clareza. O céu está azul e amanhã teremos novas ideias."],
                                       tmp_path / "reference", "pt-BR", 1.0)[0]
    voice = service.add("Synthetic integration test", reference, True)
    recovered = Library(config).get(voice["id"])
    assert recovered["id"] == voice["id"]
    assert (service.library.folder(recovered) / "speaker.npy").is_file()
    short = service.generate(voice["id"], "Olá, estamos testando a geração local em português brasileiro.",
                             output=tmp_path / "short.wav")
    assert short["duration_seconds"] > 2
    with pytest.raises(SkillError, match="ja existe"):
        service.generate(voice["id"], "Novo texto", output=tmp_path / "short.wav")
    long_text = ("Esta narração testa textos extensos em português brasileiro. Cada frase deve preservar as palavras, a pontuação e a continuidade do áudio. A geração é local, com uma voz base e conversão de timbre. " * 5)
    result = service.generate(voice["id"], long_text, output=tmp_path / "long.mp3", max_chars=180)
    assert result["segments"] >= 5
    assert result["duration_seconds"] > 20
    metadata = probe(Path(result["output"]), config)
    assert metadata["streams"][0]["sample_rate"] == "44100"
    wav = sf.info(tmp_path / "short.wav")
    assert wav.channels == 1
    assert wav.frames > 44100
    archive = tmp_path / "profile.zip"
    service.library.export(voice["id"], archive)
    imported = service.library.import_profile(archive, tmp_path / "import", "Imported synthetic", True)
    assert imported["id"] != voice["id"]
    service.library.rename(imported["id"], "Renamed synthetic")
    service.library.delete("Renamed synthetic")
    bad = tmp_path / "invalid.wav"
    bad.write_text("invalid audio", encoding="utf-8")
    with pytest.raises(SkillError):
        active_speech(bad, tmp_path / "bad", config)
    if "en-US" in config.piper_models:
        english = service.generate(voice["id"], "This is a local test of cross language tone conversion.",
                                   language="en-US", output=tmp_path / "english.wav")
        assert english["duration_seconds"] > 2
