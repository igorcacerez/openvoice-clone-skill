"""Optional PT-BR base upgrade; preserves the voice library."""
import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

from setup_models import download


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8-sig"))
    environment = Path(config["root"]) / "kokoro-venv"
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():
        subprocess.run(["uv", "venv", "--python", "3.11", str(environment)], check=True)
    subprocess.run(["uv", "pip", "install", "--python", str(python),
                    "kokoro-onnx==0.4.9", "soundfile==0.13.1"], check=True)
    root = Path(config["models"]) / "kokoro"
    base = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
    for name, checksum in {
        "kokoro-v1.0.onnx": "7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5",
        "voices-v1.0.bin": "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d",
    }.items():
        download(base + name, root / name, checksum)
    config["kokoro"] = {"python": str(python), "model": str(root / "kokoro-v1.0.onnx"),
                        "voices": str(root / "voices-v1.0.bin"),
                        "languages": {"pt-BR": {"voice": "pf_dora", "language": "pt-br"}}}
    shutil.copyfile(args.config, args.config.with_suffix(".before-kokoro.json"))
    args.config.write_text(json.dumps(config, indent=2), encoding="utf-8")
    print("Kokoro configurado. Escute uma previa antes de considerar a qualidade aprovada.")


if __name__ == "__main__":
    main()
