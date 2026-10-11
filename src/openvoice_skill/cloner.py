from __future__ import annotations

import contextlib
import hashlib
import io
import sys
from pathlib import Path
from typing import Any

import numpy as np

from .config import Config, SkillError


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for part in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


class Cloner:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._converter: Any = None

    @property
    def converter(self) -> Any:
        if self._converter is None:
            import torch
            if not (self.config.repo / "openvoice/api.py").is_file():
                raise SkillError("OpenVoice ausente; execute scripts/install.py.")
            checkpoint = self.config.converter_dir / "checkpoint.pth"
            if not checkpoint.is_file():
                raise SkillError("Checkpoint ausente; execute scripts/setup_models.py.")
            if self.config.version not in ("v1", "v2"):
                raise SkillError("Versao do conversor deve ser v1 ou v2.")
            expected = {"v2": "9652c27e92b6b2a91632590ac9962ef7ae2b712e5c5b7f4c34ec55ee2b37ab9e",
                        "v1": "89ae83aa4e3668fef64b388b789ff7b0ce0def9f801069edfc18a00ea420748d"}
            if sha256(checkpoint) != expected[self.config.version]:
                raise SkillError("Checksum do checkpoint oficial nao confere. Reinstale o modelo.")
            sys.path.insert(0, str(self.config.repo))
            from openvoice.api import OpenVoiceBaseClass, ToneColorConverter

            class LocalToneColorConverter(ToneColorConverter):
                """Upstream forwards enable_watermark to a base that cannot accept it.

                Initialize the same official model without the optional watermark loader.
                Extraction and conversion remain the unmodified upstream methods.
                """

                def __init__(self, path: str, selected_device: str) -> None:
                    OpenVoiceBaseClass.__init__(self, path, device=selected_device)
                    self.watermark_model = None
                    self.version = getattr(self.hps, "_version_", "v1")

                def load_ckpt(self, path: str) -> None:
                    checkpoint_dict = torch.load(path, map_location=torch.device(self.device), weights_only=True)
                    missing, unexpected = self.model.load_state_dict(checkpoint_dict["model"], strict=False)
                    if missing or unexpected:
                        raise SkillError("Checkpoint nao corresponde integralmente a arquitetura do conversor.")
            device = self.config.device
            if device == "auto":
                device = "cuda:0" if torch.cuda.is_available() else "cpu"
            if device.startswith("cuda") and not torch.cuda.is_available():
                raise SkillError("CUDA indisponivel; use OPENVOICE_DEVICE=cpu.")
            torch.set_num_threads(self.config.threads)
            # Disable optional wavmark model; disclose provenance in file metadata/history.
            # V2 checkpoint is official and validated during download; never load a user pickle.
            with contextlib.redirect_stdout(io.StringIO()):
                self._converter = LocalToneColorConverter(str(self.config.converter_dir / "config.json"), device)
                self._converter.load_ckpt(str(checkpoint))
            if self._converter.version != self.config.version:
                raise SkillError("Versao do checkpoint nao corresponde a configuracao.")
        return self._converter

    def extract(self, files: list[Path], output: Path) -> dict[str, Any]:
        import torch
        embeddings = [self.converter.extract_se(str(file)).detach().cpu().float() for file in files]
        if not embeddings:
            raise SkillError("Sem segmentos para extrair o perfil.")
        flat = torch.cat([e.flatten()[None] for e in embeddings], dim=0)
        distances = (torch.nn.functional.normalize(flat, dim=1) @ torch.nn.functional.normalize(flat, dim=1).T)
        similarity = float(distances.min())
        mean = torch.stack(embeddings).mean(0).numpy()
        if not np.isfinite(mean).all():
            raise SkillError("Embedding vocal invalido.")
        np.save(output, mean, allow_pickle=False)
        return {"embedding_shape": list(mean.shape), "segment_similarity_min": round(similarity, 4),
                "speaker_check": "heuristic_embeddings_not_diarization",
                "possible_multiple_speakers": similarity < 0.65,
                "converter_sha256": sha256(self.config.converter_dir / "checkpoint.pth")}

    def tensor(self, path: Path) -> Any:
        import torch
        array = np.load(path, allow_pickle=False)
        if array.shape != (1, 256, 1) or not np.isfinite(array).all():
            raise SkillError("Perfil vocal corrompido ou com dimensoes incompativeis.")
        return torch.from_numpy(array.astype(np.float32)).to(self.converter.device)

    def convert(self, source: Path, source_embedding: Path, target_embedding: Path,
                output: Path, tau: float) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            self.converter.convert(str(source), self.tensor(source_embedding), self.tensor(target_embedding),
                                   output_path=str(output), tau=tau, message="OpenVoice")
