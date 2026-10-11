"""Reproducible isolated install. Invoke with Python 3.10/3.11 or `uv run --python 3.11`."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

from setup_models import setup

OPENVOICE_REV = "74a1d147b17a8c3092dd5430504bd83ef6c7eb23"


def run(*args: str, env: dict[str, str] | None = None) -> None:
    subprocess.run(args, check=True, env=env)


def interpreter(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.home() / ".local/share/openvoice")
    parser.add_argument("--models", type=Path)
    parser.add_argument("--data", type=Path)
    parser.add_argument("--exports", type=Path)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--device", choices=("cpu", "cuda", "auto"), default="auto")
    parser.add_argument("--language", choices=("pt-BR", "en-US", "fr-FR"), action="append")
    args = parser.parse_args()
    for tool in ("uv", "git", "ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            parser.error(f"{tool} ausente. Veja README para instalar o requisito.")
    source = Path(__file__).resolve().parents[1]
    root = args.root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    repo = root / "repo"
    if not (repo / ".git").exists():
        run("git", "clone", "https://github.com/myshell-ai/OpenVoice.git", str(repo))
        run("git", "-C", str(repo), "checkout", OPENVOICE_REV)
    else:
        result = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        if result.stdout.strip() != OPENVOICE_REV:
            parser.error("OpenVoice existente em outra revisao; use um --root separado para preservar a instalacao.")
    cache = (args.cache or root / "cache").resolve()
    env = dict(os.environ, UV_CACHE_DIR=str(cache / "uv"))
    for folder in (root / ".venv", root / "piper-venv"):
        if not interpreter(folder).exists():
            run("uv", "venv", "--python", "3.11", str(folder), env=env)
    use_cuda = args.device == "cuda" or (args.device == "auto" and bool(shutil.which("nvidia-smi")))
    index = "https://download.pytorch.org/whl/cu118" if use_cuda else "https://download.pytorch.org/whl/cpu"
    python = interpreter(root / ".venv")
    piper = interpreter(root / "piper-venv")
    run("uv", "pip", "install", "--python", str(python), "torch==2.5.1", "torchaudio==2.5.1", "--index-url", index, env=env)
    run("uv", "pip", "install", "--python", str(python), "-e", str(source) + "[test]", env=env)
    run("uv", "pip", "install", "--python", str(piper), "piper-tts==1.8.0", env=env)
    models = (args.models or root / "models").resolve()
    catalog = setup(models, args.language or ["pt-BR"])
    config = {"root": str(root), "repo": str(repo), "models": str(models), "cache": str(cache),
              "data": str((args.data or root / "data").resolve()),
              "exports": str((args.exports or root / "exports").resolve()), "piper_python": str(piper),
              "piper_models": catalog, "version": "v2", "device": "auto" if args.device == "auto" else ("cuda:0" if use_cuda else "cpu")}
    config_path = Path(os.environ.get("APPDATA", Path.home() / ".config")) / "openvoice-clone/config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.exists():
        old = json.loads(config_path.read_text(encoding="utf-8-sig"))
        if Path(old.get("data", config["data"])).resolve() != Path(config["data"]):
            parser.error("Configuracao existente usa outra biblioteca. Preserve --data; nenhuma voz foi movida.")
        config = old | config
        config["piper_models"] = old.get("piper_models", {}) | catalog
        shutil.copyfile(config_path, config_path.with_suffix(".json.bak"))
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    destination = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "skills/openvoice-clone"
    for relative in ("SKILL.md", "agents/openai.yaml", "scripts/run.py", "references/operations.md"):
        output = destination / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / relative, output)
    run(str(python), "-m", "openvoice_skill.cli", "doctor", "--load-models", env=env)
    print(json.dumps({"installed": str(root), "skill": str(destination), "library": config["data"]}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError:
        print("Instalacao interrompida por erro de comando. Feche processos que usam o runtime antes de reinstalar; a biblioteca foi preservada.")
        raise SystemExit(2)
