from __future__ import annotations

import json
import os
import sqlite3
import unicodedata
import uuid
import zipfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import numpy as np
from filelock import FileLock

from .cloner import sha256
from .config import Config, SkillError


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def name_key(name: str) -> str:
    name = unicodedata.normalize("NFKC", name).strip()
    if not name or len(name) > 100 or any(ord(c) < 32 for c in name):
        raise SkillError("Nome deve ter entre 1 e 100 caracteres, sem caracteres de controle.")
    return name.casefold()


class Library:
    def __init__(self, config: Config) -> None:
        self.config = config
        config.initialize()
        self.root = config.data / "voices"
        self.root.mkdir(exist_ok=True)
        self.db = config.data / "library.sqlite3"
        self.lock = FileLock(str(config.data / "library.lock"), timeout=60)
        with self.lock, self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS voices (
                  id TEXT PRIMARY KEY, name TEXT NOT NULL, name_key TEXT UNIQUE NOT NULL,
                  revision TEXT NOT NULL, metadata TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS generations (
                  id TEXT PRIMARY KEY, voice_id TEXT, created_at TEXT, status TEXT, metadata TEXT);
            """)

    def connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db, timeout=60)
        db.row_factory = sqlite3.Row
        return db

    @contextmanager
    def locked(self) -> Iterator[None]:
        with self.lock:
            yield

    def get(self, value: str) -> dict[str, Any]:
        with self.connect() as db:
            row = db.execute("SELECT * FROM voices WHERE id=? OR name_key=?", (value, name_key(value))).fetchone()
        if row is None:
            raise SkillError("Voz nao encontrada. Use voices list.")
        return dict(row) | {"metadata": json.loads(row["metadata"])}

    def list(self) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute("SELECT id,name,metadata FROM voices ORDER BY name_key").fetchall()
        return [{"id": r["id"], "name": r["name"], **json.loads(r["metadata"])} for r in rows]

    def folder(self, voice: dict[str, Any]) -> Path:
        return self.root / voice["id"] / voice["revision"]

    def commit(self, name: str, stage: Path, metadata: dict[str, Any], existing: str | None = None) -> dict[str, Any]:
        key = name_key(name)
        with self.lock, self.connect() as db:
            voice = self.get(existing) if existing else None
            voice_id = voice["id"] if voice else "voice_" + uuid.uuid4().hex
            revision = "rev_" + uuid.uuid4().hex
            metadata.update({"created_at": voice["metadata"]["created_at"] if voice else now(),
                             "updated_at": now(), "status": "ready", "engine": "openvoice-" + self.config.version,
                             "reference_audio": "reference.wav", "speaker_embedding": "speaker.npy"})
            checksums = {file: sha256(stage / file) for file in ("reference.wav", "speaker.npy")}
            metadata["checksums"] = checksums
            (stage / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
            if db.execute("SELECT id FROM voices WHERE name_key=? AND id<>?", (key, voice_id)).fetchone():
                raise SkillError("Ja existe uma voz com esse nome. Renomeie ou use voices update.")
            destination = self.root / voice_id / revision
            destination.parent.mkdir(exist_ok=True)
            os.replace(stage, destination)
            try:
                db.execute("INSERT INTO voices VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,"
                           "name_key=excluded.name_key,revision=excluded.revision,metadata=excluded.metadata",
                           (voice_id, name.strip(), key, revision, json.dumps(metadata, ensure_ascii=False)))
                db.commit()
            except Exception:
                # Preserve the staged revision on transaction failure for recovery.
                raise SkillError("Falha ao registrar perfil. A revisao permanece no disco para recuperacao.") from None
        return self.get(voice_id)

    def validate(self, voice: dict[str, Any]) -> None:
        for filename, expected in voice["metadata"]["checksums"].items():
            if filename not in ("reference.wav", "speaker.npy"):
                raise SkillError("Manifesto de perfil invalido.")
            file = self.folder(voice) / filename
            if not file.is_file() or sha256(file) != expected:
                raise SkillError("Integridade do perfil falhou. Restaure um backup ou atualize a referencia.")

    def rename(self, value: str, name: str) -> dict[str, Any]:
        key = name_key(name)
        with self.lock, self.connect() as db:
            voice = self.get(value)
            try:
                db.execute("UPDATE voices SET name=?,name_key=? WHERE id=?", (name.strip(), key, voice["id"]))
                db.commit()
            except sqlite3.IntegrityError:
                raise SkillError("Ja existe uma voz com esse nome.") from None
        return self.get(voice["id"])

    def delete(self, value: str) -> dict[str, Any]:
        with self.lock, self.connect() as db:
            voice = self.get(value)
            trash = self.config.data / "trash"
            trash.mkdir(exist_ok=True)
            destination = trash / (voice["id"] + "_" + uuid.uuid4().hex)
            source = self.root / voice["id"]
            (source / "deleted-profile.json").write_text(json.dumps(voice, ensure_ascii=False), encoding="utf-8")
            os.replace(source, destination)
            try:
                db.execute("DELETE FROM voices WHERE id=?", (voice["id"],))
                db.commit()
            except Exception:
                os.replace(destination, source)
                raise
            return {"deleted": voice["name"], "recoverable_at": str(destination), "permanent_erasure": False}

    def export(self, value: str, path: Path) -> dict[str, Any]:
        with self.lock:
            voice = self.get(value)
            self.validate(voice)
            if path.exists():
                raise SkillError("Destino ja existe; escolha outro nome.")
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".part")
            metadata = dict(voice["metadata"]) | {"name": voice["name"]}
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("metadata.json", json.dumps(metadata, ensure_ascii=False))
                for file in ("reference.wav", "speaker.npy"):
                    archive.write(self.folder(voice) / file, file)
            os.replace(temporary, path)
            return {"profile": str(path), "contains_private_voice_data": True}

    def import_profile(self, path: Path, stage: Path, name: str | None, consent: bool) -> dict[str, Any]:
        if not consent:
            raise SkillError("Importacao exige autorizacao: --consent-confirmed.")
        stage.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path) as archive:
            files = archive.infolist()
            if len(files) != 3 or {f.filename for f in files} != {"metadata.json", "reference.wav", "speaker.npy"}:
                raise SkillError("Perfil ZIP invalido; apenas tres arquivos previstos sao aceitos.")
            if any(f.file_size > 50_000_000 or (f.external_attr >> 16) & 0o170000 == 0o120000 for f in files):
                raise SkillError("Perfil com arquivo grande demais ou link simbolico.")
            for f in files:
                (stage / f.filename).write_bytes(archive.read(f))
        metadata = json.loads((stage / "metadata.json").read_text(encoding="utf-8"))
        for file in ("reference.wav", "speaker.npy"):
            if sha256(stage / file) != metadata.get("checksums", {}).get(file):
                raise SkillError("Checksum do perfil importado nao confere.")
        embedding = np.load(stage / "speaker.npy", allow_pickle=False)
        if embedding.shape != (1, 256, 1) or not np.isfinite(embedding).all():
            raise SkillError("Embedding importado invalido; pickle nao e aceito.")
        if metadata.get("engine") != "openvoice-" + self.config.version:
            raise SkillError("Perfil pertence a outra versao do OpenVoice.")
        metadata["consent_confirmed_at"] = now()
        return self.commit(name or metadata.pop("name"), stage, metadata)

    def history(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute("SELECT * FROM generations ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) | {"metadata": json.loads(row["metadata"])} for row in rows]

    def record(self, voice_id: str, status: str, metadata: dict[str, Any], generation_id: str | None = None) -> str:
        generation_id = generation_id or "gen_" + uuid.uuid4().hex
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO generations VALUES (?,?,?,?,?)",
                       (generation_id, voice_id, now(), status, json.dumps(metadata, ensure_ascii=False)))
        return generation_id
