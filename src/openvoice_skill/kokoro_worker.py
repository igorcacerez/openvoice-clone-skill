"""Executed in the separate Kokoro environment; narration remains on this computer."""
import json
import sys
from pathlib import Path

import onnxruntime as rt
import soundfile as sf
from kokoro_onnx import Kokoro


def main() -> None:
    data = json.load(sys.stdin)
    options = rt.SessionOptions()
    options.intra_op_num_threads = data["threads"]
    options.inter_op_num_threads = 1
    session = rt.InferenceSession(data["model"], sess_options=options, providers=["CPUExecutionProvider"])
    engine = Kokoro.from_session(session, data["voices"])
    for index, text in enumerate(data["texts"]):
        samples, rate = engine.create(text, voice=data["voice"], speed=data["speed"], lang=data["language"])
        sf.write(Path(data["folder"]) / f"{index:06d}.wav", samples, rate, subtype="PCM_16")


if __name__ == "__main__":
    main()
