"""Deterministic local IndicF5 synthesis runner for ANDY Voice v2.

This runner deliberately bypasses Hugging Face AutoModel remote-code loading.
That path currently re-enters the IndicF5/Vocos meta-tensor bug on Windows.
Instead we download only the model assets and load the local f5_tts stack
explicitly, following the upstream IndicF5 fix direction.
"""

import argparse
import sys
from pathlib import Path


def _build_model(repo_id: str, device: str):
    import torch
    from huggingface_hub import hf_hub_download
    from safetensors.torch import load_file
    from f5_tts.model import DiT
    from f5_tts.infer.utils_infer import load_model, load_vocoder

    vocab_path = hf_hub_download(repo_id, filename="checkpoints/vocab.txt")
    ckpt_path = hf_hub_download(repo_id, filename="model.safetensors")

    print(f"ANDY Voice v2 device: {device}", flush=True)
    print("Loading Vocos...", flush=True)
    vocoder = load_vocoder(vocoder_name="vocos", is_local=False, device=device)

    print("Loading IndicF5 DiT...", flush=True)
    model = load_model(
        DiT,
        dict(dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512, conv_layers=4),
        mel_spec_type="vocos",
        vocab_file=vocab_path,
        device=device,
    )

    print("Loading IndicF5 checkpoint...", flush=True)
    state_dict = load_file(ckpt_path, device=device)
    state_dict = {
        key.replace("ema_model._orig_mod.", ""): value
        for key, value in state_dict.items()
        if key.startswith("ema_model.")
    }
    model.load_state_dict(state_dict)
    model.eval()
    return model, vocoder


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

    import numpy as np
    import soundfile as sf
    import torch
    from f5_tts.infer.utils_infer import infer_process, preprocess_ref_audio_text

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, vocoder = _build_model(args.model, device)

    print("Preprocessing reference voice...", flush=True)
    ref_audio, normalized_ref_text = preprocess_ref_audio_text(
        str(ref_audio_path), ref_text, device=device
    )

    print("Generating ANDY Voice v2...", flush=True)
    audio, sample_rate, _ = infer_process(
        ref_audio,
        normalized_ref_text,
        text,
        model,
        vocoder,
        mel_spec_type="vocos",
        device=device,
    )

    if getattr(audio, "dtype", None) == np.int16:
        audio = audio.astype(np.float32) / 32768.0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), np.asarray(audio, dtype=np.float32), samplerate=sample_rate or 24000)
    print(f"ANDY Voice v2 saved: {output_path}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"INDICF5_ERROR: {exc}", file=sys.stderr, flush=True)
        raise
