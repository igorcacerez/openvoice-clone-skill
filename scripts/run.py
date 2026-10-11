"""Skill entrypoint: find the global runtime without depending on the project cwd."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    base = Path(os.environ.get("APPDATA", Path.home() / ".config"))
    path = Path(os.environ.get("OPENVOICE_CONFIG", base / "openvoice-clone/config.json"))
    if not path.exists():
        print(json.dumps({"ok": False, "error": "OpenVoice nao configurado; execute scripts/install.py."}), file=sys.stderr)
        return 2
    config = json.loads(path.read_text(encoding="utf-8-sig"))
    root = Path(os.environ.get("OPENVOICE_HOME", config["root"]))
    python = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():
        print(json.dumps({"ok": False, "error": "Ambiente Python ausente; reinstale preservando a biblioteca."}), file=sys.stderr)
        return 2
    return subprocess.call([str(python), "-m", "openvoice_skill.cli", "--config", str(path), *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
