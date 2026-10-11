from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path


class SkillError(Exception):
    """An actionable user-facing error; never contains the narration text."""


def user_config_path() -> Path:
    base = Path(os.environ.get("APPDATA", Path.home() / ".config"))
    return base / "openvoice-clone" / "config.json"


@dataclass(frozen=True)
class Config:
    root: Path
    repo: Path
    models: Path
    data: Path
    exports: Path
    cache: Path
    piper_python: Path
    piper_models: dict[str, str]
    device: str = "auto"
    ffmpeg: str = "ffmpeg"
    ffprobe: str = "ffprobe"
    version: str = "v2"
    threads: int = 4
    kokoro: dict = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path | None = None) -> Config:
        file = Path(path or os.environ.get("OPENVOICE_CONFIG", user_config_path()))
        raw = json.loads(file.read_text(encoding="utf-8-sig")) if file.exists() else {}
        root = Path(os.environ.get("OPENVOICE_HOME", raw.get("root", Path.home() / ".local/share/openvoice")))
        def location(key: str, default: Path) -> Path:
            return Path(os.environ.get(f"OPENVOICE_{key.upper()}", raw.get(key, str(default)))).expanduser().resolve()
        return cls(
            root=root.resolve(), repo=location("repo", root / "repo"),
            models=location("models", root / "models"), data=location("data", root / "data"),
            exports=location("exports", root / "exports"), cache=location("cache", root / "cache"),
            piper_python=location("piper_python", root / "piper-venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")),
            piper_models=raw.get("piper_models", {"pt-BR": "piper/pt-BR/pt_BR-faber-medium.onnx"}),
            device=os.environ.get("OPENVOICE_DEVICE", raw.get("device", "auto")),
            ffmpeg=raw.get("ffmpeg", shutil.which("ffmpeg") or "ffmpeg"),
            ffprobe=raw.get("ffprobe", shutil.which("ffprobe") or "ffprobe"),
            version=raw.get("version", "v2"), threads=int(raw.get("threads", 4)),
            kokoro=raw.get("kokoro", {}),
        )

    def initialize(self) -> None:
        for folder in (self.data, self.cache, self.exports):
            folder.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("TORCH_HOME", str(self.cache / "torch"))
        os.environ.setdefault("HF_HOME", str(self.cache / "huggingface"))

    @property
    def converter_dir(self) -> Path:
        return self.models / self.version / "converter"

    def piper_model(self, language: str) -> Path:
        if language not in self.piper_models:
            raise SkillError(f"Idioma {language} sem TTS instalado. Configure piper_models; veja setup_models.py.")
        path = self.models / self.piper_models[language]
        if not path.is_file() or not Path(str(path) + ".json").is_file():
            raise SkillError(f"Modelo Piper ausente para {language}; execute scripts/setup_models.py.")
        return path
