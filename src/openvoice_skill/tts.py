from __future__ import annotations

import re
from pathlib import Path

from .audio import run_tool
from .config import Config, SkillError


def split_text(text: str, maximum: int = 260) -> list[str]:
    if maximum < 40:
        raise SkillError("Tamanho de segmento deve ser de pelo menos 40 caracteres.")
    if not text.strip():
        raise SkillError("Texto vazio.")
    if len(text) > 2_000_000:
        raise SkillError("Texto maior que o limite de dois milhoes de caracteres.")
    # Keep paragraph and sentence boundaries. Split huge sentences at whitespace.
    sentences = re.split(r"(?<=[.!?;:。！？])\s+|\n+", text.strip())
    result: list[str] = []
    for sentence in sentences:
        sentence = re.sub(r"\s+", " ", sentence).strip()
        while len(sentence) > maximum:
            boundary = sentence.rfind(" ", 0, maximum + 1)
            if boundary <= 0:
                # Never cut a word silently: excessive token length is actionable.
                raise SkillError("Palavra longa demais; verifique URLs ou texto sem espacos.")
            result.append(sentence[:boundary])
            sentence = sentence[boundary:].lstrip()
        if sentence:
            if result and len(result[-1]) + len(sentence) + 1 <= maximum:
                result[-1] += " " + sentence
            else:
                result.append(sentence)
    return result


class Piper:
    """Separate process: no dependency on the GPL Piper library in this package."""

    def __init__(self, config: Config) -> None:
        self.config = config

    def synthesize(self, texts: list[str], folder: Path, language: str, speed: float) -> list[Path]:
        model = self.config.piper_model(language)
        if not self.config.piper_python.is_file():
            raise SkillError("Ambiente Piper ausente; execute scripts/install.py.")
        folder.mkdir(parents=True, exist_ok=True)
        run_tool([str(self.config.piper_python), "-m", "piper", "--model", str(model),
                  "--output-dir", str(folder), "--length-scale", str(1 / speed), "--sentence-silence", "0.14"],
                 text="\n".join(texts) + "\n", timeout=max(1800, len(texts) * 90))
        files = sorted(folder.glob("*.wav"), key=lambda f: int(f.stem))
        if len(files) != len(texts):
            raise SkillError("Piper nao produziu todos os segmentos esperados.")
        return files
