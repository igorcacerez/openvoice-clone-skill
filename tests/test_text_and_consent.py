from pathlib import Path

import pytest

from openvoice_skill.config import SkillError
from openvoice_skill.service import Service
from openvoice_skill.tts import split_text


def test_long_text_keeps_all_words_and_punctuation():
    source = "Uma frase brasileira com acentuação e números: 123. Outra frase! " * 20
    chunks = split_text(source, 120)
    assert len(chunks) > 5
    assert all(len(c) <= 120 for c in chunks)
    assert " ".join(chunks).split() == source.split()


def test_empty_text_and_unsplittable_token():
    with pytest.raises(SkillError, match="vazio"):
        split_text("   ")
    with pytest.raises(SkillError, match="Palavra longa"):
        split_text("x" * 300)


def test_add_stops_without_consent_before_models(config):
    with pytest.raises(SkillError, match="autorizacao"):
        Service(config).add("Example", Path("missing.wav"), False)


def test_invalid_generation_controls_fail_before_models(config):
    service = Service(config)
    with pytest.raises(SkillError, match="Velocidade"):
        service.generate("Example", "Ola", speed=0)
    with pytest.raises(SkillError, match="Formato"):
        service.generate("Example", "Ola", format="aac")
