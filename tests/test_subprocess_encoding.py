import json
import sys

from openvoice_skill.audio import run_tool


def test_utf8_input_survives_legacy_child_locale(monkeypatch):
    # Reproduce a Windows Python child using a legacy console encoding.
    monkeypatch.setenv("PYTHONUTF8", "0")
    monkeypatch.setenv("PYTHONIOENCODING", "cp1252")
    text = "Olá! Esta é uma narração em português brasileiro. Emoção, coração, amanhã."
    script = "import sys,json; print(json.dumps({'text':sys.stdin.read(),'encoding':sys.stdin.encoding}))"
    result = json.loads(run_tool([sys.executable, "-c", script], text=text))
    assert result["text"] == text
    assert result["encoding"].lower().replace("-", "") == "utf8"
