from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

from .config import Config, SkillError


def run_tool(args: list[str], *, timeout: int = 1800, text: str | None = None) -> str:
    try:
        result = subprocess.run(args, input=text, capture_output=True, text=True, encoding="utf-8",
                                errors="replace", timeout=timeout,
                                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SkillError(f"Falha ao executar {Path(args[0]).name}: {type(exc).__name__}") from exc
    if result.returncode:
        # Tool output can include private paths/text: do not echo it to logs.
        raise SkillError(f"{Path(args[0]).name} retornou erro {result.returncode}; verifique arquivo, codec e modelo.")
    return result.stdout


def probe(path: Path, config: Config) -> dict[str, Any]:
    if not path.is_file():
        raise SkillError("Arquivo de audio nao encontrado.")
    raw = run_tool([config.ffprobe, "-v", "error", "-show_entries",
                    "format=duration:stream=codec_type,sample_rate,channels", "-of", "json", str(path)])
    result = json.loads(raw)
    if not any(s.get("codec_type") == "audio" for s in result.get("streams", [])):
        raise SkillError("Arquivo nao possui uma faixa de audio valida.")
    return result


def pcm(path: Path, out: Path, config: Config, rate: int = 16000) -> None:
    run_tool([config.ffmpeg, "-v", "error", "-nostdin", "-y", "-i", str(path),
              "-vn", "-ac", "1", "-ar", str(rate), "-c:a", "pcm_s16le", str(out)])


def active_speech(path: Path, directory: Path, config: Config) -> tuple[list[Path], dict[str, Any]]:
    import torch
    from silero_vad import get_speech_timestamps, load_silero_vad

    details = probe(path, config)
    duration = float(details.get("format", {}).get("duration", 0))
    if not 4 <= duration <= 600:
        raise SkillError("Referencia deve ter entre 4 segundos e 10 minutos; recomendado: 15 a 60 segundos.")
    directory.mkdir(parents=True, exist_ok=True)
    raw = directory / "decoded.wav"
    pcm(path, raw, config)
    audio, rate = sf.read(raw, dtype="float32")
    if not np.isfinite(audio).all() or np.max(np.abs(audio), initial=0) < 0.001:
        raise SkillError("Audio vazio, silencioso ou com amostras invalidas.")
    torch.set_num_threads(config.threads)
    windows = get_speech_timestamps(torch.from_numpy(audio), load_silero_vad(), sampling_rate=rate,
                                   min_speech_duration_ms=250, min_silence_duration_ms=350,
                                   speech_pad_ms=100)
    if not windows:
        raise SkillError("Nenhuma fala detectada. Use uma gravacao limpa com um unico locutor.")
    speech = np.concatenate([audio[w["start"]:w["end"]] for w in windows])
    speech = speech[:rate * 120]
    speech_seconds = len(speech) / rate
    if speech_seconds < 4:
        raise SkillError("Menos de 4 segundos de fala detectada; grave uma referencia mais longa.")
    clip_fraction = float(np.mean(np.abs(audio) > 0.99))
    floor = float(np.sqrt(np.mean(audio[np.abs(audio) < np.percentile(np.abs(audio), 20)] ** 2)))
    rms = float(np.sqrt(np.mean(speech ** 2)))
    snr_estimate = float(20 * np.log10(max(rms, 1e-9) / max(floor, 1e-9)))
    warnings: list[str] = []
    if clip_fraction > 0.003:
        warnings.append("Possivel saturacao; use uma referencia com volume menor.")
    if snr_estimate < 15:
        warnings.append("Possivel ruido constante; estimativa heuristica, nao mede SNR verdadeiro.")
    if speech_seconds < 10:
        warnings.append("Referencia curta; 15 a 60 segundos costuma melhorar a estabilidade.")
    sf.write(directory / "reference.wav", speech, rate, subtype="PCM_16")
    segments: list[Path] = []
    for start in range(0, len(speech), rate * 8):
        chunk = speech[start:start + rate * 8]
        if len(chunk) < rate * 2:
            continue
        target = directory / f"segment-{len(segments):03d}.wav"
        sf.write(target, chunk, rate, subtype="PCM_16")
        segments.append(target)
    raw.unlink()
    return segments, {"duration_original": duration, "speech_seconds": round(speech_seconds, 3),
                      "sample_rate": rate, "silence_removed": True, "clipping_fraction": clip_fraction,
                      "snr_proxy_db": round(snr_estimate, 2), "warnings": warnings}


def finalize(source: Path, target: Path, config: Config) -> None:
    codec = ["-c:a", "libmp3lame", "-b:a", "192k"] if target.suffix.lower() == ".mp3" else ["-c:a", "pcm_s16le"]
    run_tool([config.ffmpeg, "-v", "error", "-nostdin", "-y", "-i", str(source),
              "-af", "loudnorm=I=-18:TP=-1.5:LRA=11", "-ar", "44100", *codec,
              "-metadata", "comment=AI-generated speech; OpenVoice/Piper", str(target)])
    if target.stat().st_size < 1000:
        raise SkillError("A exportacao nao gerou audio suficiente.")
