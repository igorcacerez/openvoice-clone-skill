from __future__ import annotations

import hashlib
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from filelock import FileLock

from .audio import active_speech, finalize, pcm
from .cloner import Cloner, sha256
from .config import Config, SkillError
from .storage import Library, now
from .tts import TTS, split_text


CALIBRATION = {
    "pt-BR": "Esta é uma gravação sintética para calibrar o timbre da voz base. Hoje vamos conversar com calma sobre uma nova ideia. A pronúncia brasileira é importante para compreender todas as palavras.",
    "en-US": "This is a synthetic recording to calibrate the base speaker. Today we will talk calmly about a new idea. Clear pronunciation helps us understand every word in this message.",
    "es-ES": "Esta es una grabacion sintetica para calibrar la voz base. Hoy vamos a conversar con calma sobre una nueva idea. Una pronunciacion clara nos ayuda a comprender todas las palabras.",
    "fr-FR": "Ceci est un enregistrement synthetique pour calibrer la voix. Nous allons parler calmement de nouvelles idees. Une bonne prononciation aide a comprendre chaque mot.",
}


class Service:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.library = Library(config)
        self.cloner = Cloner(config)
        self.tts = TTS(config)

    def add(self, name: str, audio: Path, consent: bool, language: str = "pt-BR",
            existing: str | None = None) -> dict[str, Any]:
        if not consent:
            raise SkillError("Cadastro exige autorizacao para usar esta voz: --consent-confirmed.")
        from .storage import name_key
        name_key(name)
        # Validate conflicts before expensive inference; commit checks again under lock.
        if not existing and any(name_key(v["name"]) == name_key(name) for v in self.library.list()):
            raise SkillError("Ja existe uma voz com esse nome.")
        with tempfile.TemporaryDirectory(dir=self.config.data, prefix="stage-") as temporary:
            stage = Path(temporary) / "revision"
            segments, quality = active_speech(audio, stage, self.config)
            embedding = self.cloner.extract(segments, stage / "speaker.npy")
            if embedding["possible_multiple_speakers"]:
                raise SkillError("Referencia inconsistente: possiveis locutores distintos. Use fala limpa de uma pessoa.")
            quality["warnings"].append("Checagem de locutor e heuristica; nao substitui diarizacao nem escuta humana.")
            for segment in segments:
                segment.unlink()
            metadata = {"language": language, "consent_confirmed_at": now(), "quality": quality, **embedding}
            return self.library.commit(name, stage, metadata, existing)

    def source_embedding(self, language: str) -> Path:
        cache_key = hashlib.sha256((self.tts.identity(language) +
                                   sha256(self.config.converter_dir / "checkpoint.pth") + "calibration-v2-utf8" +
                                   CALIBRATION.get(language, "")).encode()).hexdigest()
        root = self.config.cache / "source-embeddings" / cache_key
        root.parent.mkdir(parents=True, exist_ok=True)
        with FileLock(str(root) + ".lock", timeout=600):
            cached = root / "speaker.npy"
            if cached.is_file():
                self.cloner.tensor(cached)
                return cached
            with tempfile.TemporaryDirectory(dir=root.parent) as temp:
                stage = Path(temp)
                text = CALIBRATION.get(language)
                if not text:
                    raise SkillError("Idioma sem texto de calibracao; adicione CALIBRATION para esta lingua.")
                wav = self.tts.synthesize([text], stage / "base", language, 1.0)[0]
                self.cloner.extract([wav], stage / "speaker.npy")
                root.mkdir(exist_ok=True)
                os.replace(stage / "speaker.npy", cached)
            return cached

    def generate(self, voice_name: str, text: str, language: str = "pt-BR", output: Path | None = None,
                 format: str = "wav", speed: float = 1.0, tau: float = 0.3,
                 max_chars: int = 260) -> dict[str, Any]:
        if not 0.5 <= speed <= 2.0 or not 0.05 <= tau <= 1:
            raise SkillError("Velocidade deve estar entre 0.5 e 2; tau entre 0.05 e 1.")
        if format not in ("wav", "mp3"):
            raise SkillError("Formato deve ser wav ou mp3.")
        segments = split_text(text, max_chars, keep_sentences=self.tts.uses_kokoro(language))
        self.tts.identity(language)
        target = output or self.config.exports / ("narracao-" + uuid.uuid4().hex[:12] + "." + format)
        target = target.expanduser().resolve()
        if target.suffix.lower() not in (".wav", ".mp3"):
            raise SkillError("Destino deve terminar em .wav ou .mp3.")
        if output is not None and format != "wav" and target.suffix.lower() != "." + format:
            raise SkillError("Formato e extensao de saida discordam.")
        target.parent.mkdir(parents=True, exist_ok=True)
        generation_id = "gen_" + uuid.uuid4().hex
        metadata: dict[str, Any] = {"language": language, "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                                    "characters": len(text), "segments": len(segments), "output": str(target),
                                    "speed": speed, "tau": tau, "synthetic": True, "watermark": False,
                                    "tts_base": "kokoro" if self.tts.uses_kokoro(language) else "piper"}
        with FileLock(str(target) + ".lock", timeout=60), self.library.locked():
            if target.exists():
                raise SkillError("Arquivo de destino ja existe. Escolha outro nome; nada foi sobrescrito.")
            voice = self.library.get(voice_name)
            self.library.validate(voice)
            if voice["metadata"].get("engine") != "openvoice-" + self.config.version:
                raise SkillError("Perfil de outra versao do conversor; atualize a referencia.")
            if voice["metadata"].get("converter_sha256") != sha256(self.config.converter_dir / "checkpoint.pth"):
                raise SkillError("Checkpoint mudou; atualize a referencia para recalcular o embedding.")
            self.library.record(voice["id"], "running", metadata, generation_id)
            try:
                source_embedding = self.source_embedding(language)
                with tempfile.TemporaryDirectory(dir=self.config.cache, prefix="generation-") as temp:
                    directory = Path(temp)
                    print(f"Sintetizando {len(segments)} segmentos...", file=sys.stderr)
                    base_files = self.tts.synthesize(segments, directory / "base", language, speed)
                    joined = directory / "joined.wav"
                    with sf.SoundFile(joined, mode="w", samplerate=22050, channels=1, subtype="PCM_16") as writer:
                        for index, source in enumerate(base_files):
                            print(f"Convertendo segmento {index + 1}/{len(segments)}", file=sys.stderr)
                            converted = directory / "converted.wav"
                            self.cloner.convert(source, source_embedding, self.library.folder(voice) / "speaker.npy", converted, tau)
                            resampled = directory / "resampled.wav"
                            pcm(converted, resampled, self.config, 22050)
                            samples, rate = sf.read(resampled, dtype="float32")
                            if rate != 22050 or not np.isfinite(samples).all() or len(samples) < 2205:
                                raise SkillError("Conversor retornou um segmento invalido.")
                            # Tiny edge fades prevent clicks without truncating a word.
                            fade = min(110, len(samples) // 4)
                            samples[:fade] *= np.linspace(0, 1, fade)
                            samples[-fade:] *= np.linspace(1, 0, fade)
                            writer.write(samples)
                            if index < len(base_files) - 1:
                                sentence_pause = 0.40 if self.tts.uses_kokoro(language) else 0.18
                                pause = sentence_pause if segments[index].endswith((".", "!", "?")) else 0.10
                                writer.write(np.zeros(int(22050 * pause), dtype="float32"))
                    rendered = directory / ("final" + target.suffix.lower())
                    finalize(joined, rendered, self.config)
                    shutil.copyfile(rendered, target.with_name(target.name + ".partial"))
                    os.replace(target.with_name(target.name + ".partial"), target)
                import json
                metadata.update({"sha256": sha256(target), "voice_revision": voice["revision"]})
                # Probe the final artifact, including MP3, after temporary files are removed.
                from .audio import probe
                metadata["duration_seconds"] = float(probe(target, self.config)["format"]["duration"])
                self.library.record(voice["id"], "complete", metadata, generation_id)
                # Adjacent JSON explicitly identifies synthesized audio, without saving the text.
                target.with_suffix(target.suffix + ".json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
                return {"generation_id": generation_id, "voice": voice["name"], **metadata}
            except Exception as exc:
                metadata["error_type"] = type(exc).__name__
                self.library.record(voice["id"], "failed", metadata, generation_id)
                raise
