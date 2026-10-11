from __future__ import annotations

import argparse
import json
import platform
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from .config import Config, SkillError
from .storage import Library


def doctor(config: Config, load_models: bool = False) -> dict[str, Any]:
    checks: dict[str, bool] = {"python": (3, 10) <= sys.version_info[:2] < (3, 12),
                               "ffmpeg": bool(shutil.which(config.ffmpeg)), "ffprobe": bool(shutil.which(config.ffprobe)),
                               "openvoice_source": (config.repo / "openvoice/api.py").is_file(),
                               "checkpoint": (config.converter_dir / "checkpoint.pth").is_file(),
                               "converter_config": (config.converter_dir / "config.json").is_file(),
                               "piper_python": config.piper_python.is_file()}
    for language in config.piper_models:
        try:
            config.piper_model(language)
            checks["piper_" + language] = True
        except SkillError:
            checks["piper_" + language] = False
    from .tts import TTS
    for language in config.kokoro.get("languages", {}):
        try:
            TTS(config).identity(language)
            checks["kokoro_" + language] = True
        except SkillError:
            checks["kokoro_" + language] = False
    try:
        import torch
        gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        checks["torch"] = True
    except ImportError:
        gpu = None
        checks["torch"] = False
    if load_models:
        from .cloner import Cloner
        converter = Cloner(config).converter
        checks["converter_loaded"] = converter.version == config.version
    library = Library(config)
    for voice in library.list():
        library.validate(library.get(voice["id"]))
    return {"ok": all(checks.values()), "checks": checks, "platform": platform.platform(),
            "python": platform.python_version(), "gpu": gpu, "device_setting": config.device,
            "data": str(config.data), "exports": str(config.exports), "voices": len(library.list()),
            "languages_installed": list(config.piper_models)}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="OpenVoice local: cadastro persistente e narracao de vozes autorizadas")
    p.add_argument("--config", help="Arquivo JSON; padrao: configuracao global do usuario")
    commands = p.add_subparsers(dest="command", required=True)
    d = commands.add_parser("doctor")
    d.add_argument("--load-models", action="store_true")
    v = commands.add_parser("voices")
    operations = v.add_subparsers(dest="operation", required=True)
    operations.add_parser("list")
    for op in ("info", "delete", "preview", "rename", "export", "update"):
        item = operations.add_parser(op)
        item.add_argument("voice")
        if op == "rename":
            item.add_argument("name")
        if op == "export":
            item.add_argument("--output", required=True, type=Path)
        if op == "preview":
            item.add_argument("--language", default="pt-BR")
            item.add_argument("--output", type=Path)
        if op == "update":
            item.add_argument("--audio", required=True, type=Path)
            item.add_argument("--consent-confirmed", action="store_true")
    add = operations.add_parser("add")
    add.add_argument("--name", required=True)
    add.add_argument("--audio", required=True, type=Path)
    add.add_argument("--language", default="pt-BR")
    add.add_argument("--consent-confirmed", action="store_true")
    imp = operations.add_parser("import")
    imp.add_argument("profile", type=Path)
    imp.add_argument("--name")
    imp.add_argument("--consent-confirmed", action="store_true")
    g = commands.add_parser("generate")
    g.add_argument("--voice", required=True)
    text = g.add_mutually_exclusive_group(required=True)
    text.add_argument("--text")
    text.add_argument("--file", type=Path)
    g.add_argument("--language", default="pt-BR")
    g.add_argument("--output", type=Path)
    g.add_argument("--format", choices=("wav", "mp3"), default="wav")
    g.add_argument("--speed", type=float, default=1.0)
    g.add_argument("--tau", type=float, default=0.3)
    g.add_argument("--max-chars", type=int, default=260)
    history = commands.add_parser("history")
    history.add_argument("--limit", type=int, default=20)
    return p


def execute(args: argparse.Namespace, config: Config) -> Any:
    if args.command == "doctor":
        return doctor(config, args.load_models)
    library = Library(config)
    if args.command == "history":
        return library.history(args.limit)
    if args.command == "voices":
        op = args.operation
        if op == "list":
            return library.list()
        if op == "info":
            result = library.get(args.voice)
            library.validate(result)
            return result
        if op == "rename":
            return library.rename(args.voice, args.name)
        if op == "delete":
            return library.delete(args.voice)
        if op == "export":
            return library.export(args.voice, args.output)
        if op == "import":
            with tempfile.TemporaryDirectory(dir=config.data) as temp:
                return library.import_profile(args.profile, Path(temp) / "revision", args.name, args.consent_confirmed)
    from .service import Service
    service = Service(config)
    if args.command == "generate":
        text = args.text if args.text is not None else args.file.read_text(encoding="utf-8-sig")
        return service.generate(args.voice, text, args.language, args.output, args.format,
                                args.speed, args.tau, args.max_chars)
    if args.operation == "add":
        return service.add(args.name, args.audio, args.consent_confirmed, args.language)
    if args.operation == "update":
        voice = library.get(args.voice)
        return service.add(voice["name"], args.audio, args.consent_confirmed, voice["metadata"]["language"], args.voice)
    if args.operation == "preview":
        previews = {
            "pt-BR": "Olá! Esta é uma amostra sintética da voz cadastrada. A biblioteca está pronta para narrar novos textos em português brasileiro.",
            "en-US": "Hello! This is a synthetic sample of the saved voice. The local library is ready to narrate new texts in English.",
            "fr-FR": "Bonjour ! Ceci est un exemple synthétique de la voix enregistrée. La bibliothèque locale est prête pour de nouveaux textes.",
        }
        if args.language not in previews:
            raise SkillError("Previa indisponivel para este idioma; use generate com texto apropriado.")
        return service.generate(args.voice, previews[args.language], args.language, args.output)
    raise SkillError("Operacao desconhecida.")


def main() -> int:
    args = parser().parse_args()
    try:
        config = Config.load(args.config)
        config.initialize()
        result = execute(args, config)
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, indent=2))
        return 1 if args.command == "doctor" and not result["ok"] else 0
    except KeyboardInterrupt:
        print(json.dumps({"ok": False, "error": "Operacao interrompida."}), file=sys.stderr)
        return 130
    except (SkillError, OSError, ValueError) as exc:
        message = str(exc) if isinstance(exc, SkillError) else f"Falha de arquivo ou dados: {type(exc).__name__}."
        print(json.dumps({"ok": False, "error": message}, ensure_ascii=False), file=sys.stderr)
        return 2
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"Falha no processamento: {type(exc).__name__}. Consulte troubleshooting."}), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
