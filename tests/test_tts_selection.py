from dataclasses import replace

import pytest

from openvoice_skill.config import SkillError
from openvoice_skill.tts import TTS, split_text


def test_kokoro_missing_does_not_silently_fall_back(config):
    selected = replace(config, kokoro={"languages": {"pt-BR": {"voice": "pf_dora", "language": "pt-br"}}})
    with pytest.raises(SkillError, match="incompleto"):
        TTS(selected).identity("pt-BR")


def test_calibration_identity_changes_with_base_voice(config, tmp_path):
    files = {}
    for key in ("python", "model", "voices"):
        file = tmp_path / key
        file.write_bytes(key.encode())
        files[key] = str(file)
    first = replace(config, kokoro=files | {"languages": {"pt-BR": {"voice": "pf_dora", "language": "pt-br"}}})
    second = replace(config, kokoro=files | {"languages": {"pt-BR": {"voice": "pm_alex", "language": "pt-br"}}})
    assert TTS(first).identity("pt-BR") != TTS(second).identity("pt-BR")


def test_sentence_boundaries_preserve_words_for_pauses():
    text = "Olá! Vamos conversar com calma. Cada frase tem seu tempo."
    parts = split_text(text, keep_sentences=True)
    assert parts == ["Olá!", "Vamos conversar com calma.", "Cada frase tem seu tempo."]
    assert " ".join(parts) == text
