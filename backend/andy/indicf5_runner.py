"""Isolated IndicF5 synthesis runner for ANDY Voice v2.

This file is intentionally executed by a separate Python 3.10 environment.
The Django backend invokes it as a subprocess so IndicF5's dependency stack
cannot destabilize the main ARI SMART RO backend environment.
"""

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text-file", required=True)
    parser.add_argument("--ref-audio", required=True)
    parser.add_argument("--ref-text-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default="ai4bharat/IndicF5")
    args = parser.parse_args()

    text_path = Path(args.text_file)
    ref_audio_path = Path(args.ref_audio)
    ref_text_path = Path(args.ref_text_file)
    output_path = Path(args.output)

    for path, label in (
        (text_path, "text file"),
        (ref_audio_path, "reference audio"),
        (ref_text_path, "reference transcript"),
    ):
        if not path.is_file():
            raise FileNotFoundError(f"IndicF5 {label} not found: {path}")

    text = text_path.read_text(encoding="utf-8").strip()
    ref_text = ref_text_path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("IndicF5 synthesis text is empty.")
    if not ref_text:
        raise ValueError("IndicF5 reference transcript is empty.")

    from transformers import AutoModel
    import numpy as np
    import soundfile as sf

    model = AutoModel.from_pretrained(args.model, trust_remote_code=True)
    audio = model(
        text,
        ref_audio_path=str(ref_audio_path),
        ref_text=ref_text,
    )

    if getattr(audio, "dtype", None) == np.int16:
        audio = audio.astype(np.float32) / 32768.0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), np.asarray(audio, dtype=np.float32), samplerate=24000)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"INDICF5_ERROR: {exc}", file=sys.stderr)
        raise
