"""Download pinned official weights. No audio or voice profiles are uploaded."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import urllib.request
from pathlib import Path

OPENVOICE_V2_REV = "f36e7edfe1684461a8343844af60babc2efbb727"
PIPER_REV = "c10ece1aade47bb51c153c893d14e5bf8e5b7117"
PIPER = {
    "pt-BR": ("pt/pt_BR/faber/medium", "pt_BR-faber-medium", "858555e3a064209c57088fe6bd70c4c3dc54d03eaa00c45d5ecaf43a33f95aa7"),
    "en-US": ("en/en_US/ljspeech/medium", "en_US-ljspeech-medium", "6f52a751e2349abe7a76735eb09dc1875298c77ea2342ffd2fef79ff81b87f22"),
    "fr-FR": ("fr/fr_FR/siwis/medium", "fr_FR-siwis-medium", "641d1ab097da2b81128c076810edb052b385decc8be3381814802a64a73baf99"),
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def download(url: str, target: Path, checksum: str | None = None) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and (checksum is None or digest(target) == checksum):
        return
    partial = target.with_suffix(target.suffix + ".download")
    print(f"Baixando {target.name}...", file=sys.stderr)
    request = urllib.request.Request(url, headers={"User-Agent": "openvoice-clone-skill/0.1"})
    with urllib.request.urlopen(request, timeout=120) as response, partial.open("wb") as output:
        shutil.copyfileobj(response, output)
    if checksum and digest(partial) != checksum:
        partial.unlink()
        raise RuntimeError("Checksum do modelo nao confere; download recusado.")
    os.replace(partial, target)


def setup(models: Path, languages: list[str], with_v1: bool = False) -> dict[str, str]:
    base = f"https://huggingface.co/myshell-ai/OpenVoiceV2/resolve/{OPENVOICE_V2_REV}/converter"
    download(base + "/checkpoint.pth", models / "v2/converter/checkpoint.pth",
             "9652c27e92b6b2a91632590ac9962ef7ae2b712e5c5b7f4c34ec55ee2b37ab9e")
    download(base + "/config.json", models / "v2/converter/config.json",
             "9dfff60350b8c63f2c664efd92a61b2516efb22671466960f0e5dfebd881fa47")
    catalog: dict[str, str] = {}
    for language in languages:
        folder, voice, checksum = PIPER[language]
        root = models / "piper" / language
        url = f"https://huggingface.co/rhasspy/piper-voices/resolve/{PIPER_REV}/{folder}"
        download(f"{url}/{voice}.onnx", root / (voice + ".onnx"), checksum)
        download(f"{url}/{voice}.onnx.json", root / (voice + ".onnx.json"),
                 "7e694de195ae3fc36dd732c445eb04fb49b649854893cb5506b978f0d50a1d6f" if language == "pt-BR" else None)
        download(url + "/MODEL_CARD", root / "MODEL_CARD")
        catalog[language] = str(Path("piper") / language / (voice + ".onnx"))
    if with_v1:
        # V1 remains optional. Pin to the official repository revision.
        url = "https://huggingface.co/myshell-ai/OpenVoice/resolve/c70fc8b939bd1d8213994ff7c88e32be39708271/checkpoints/converter"
        for file in ("config.json", "checkpoint.pth"):
            download(url + "/" + file, models / "v1/converter" / file,
                     "89ae83aa4e3668fef64b388b789ff7b0ce0def9f801069edfc18a00ea420748d" if file == "checkpoint.pth" else None)
    files = {str(file.relative_to(models)): digest(file) for file in models.rglob("*") if file.is_file() and file.name != "manifest.json"}
    (models / "manifest.json").write_text(json.dumps({"openvoice_revision": OPENVOICE_V2_REV,
                                                      "piper_revision": PIPER_REV, "sha256": files}, indent=2), encoding="utf-8")
    return catalog


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", required=True, type=Path)
    parser.add_argument("--language", action="append", choices=list(PIPER))
    parser.add_argument("--with-v1", action="store_true")
    args = parser.parse_args()
    print(json.dumps(setup(args.models, args.language or ["pt-BR"], args.with_v1), indent=2))


if __name__ == "__main__":
    main()
