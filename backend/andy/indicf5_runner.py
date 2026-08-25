"""Deterministic local IndicF5 synthesis runner for ANDY Voice v2.

This runner deliberately bypasses Hugging Face AutoModel remote-code loading.
That path currently re-enters the IndicF5/Vocos meta-tensor bug on Windows.
Instead we download only the model assets and load the local f5_tts stack
explicitly, following the upstream IndicF5 fix direction.
"""

import argparse
import json
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


def _synthesize(text, output_path, ref_audio, normalized_ref_text, model, vocoder, device):
    import numpy as np
    import soundfile as sf
    from f5_tts.infer.utils_infer import infer_process

    print("Generating ANDY Voice v2...", flush=True)
    audio, sample_rate, _ = infer_process(
        ref_audio,
        normalized_ref_text,
        text,
        model,
        vocoder,
        mel_spec_type="vocos",
        device=device,
        speed=1.2,
        nfe_step=16,
    )
    if getattr(audio, "dtype", None) == np.int16:
        audio = audio.astype(np.float32) / 32768.0

    # Make ANDY clearly audible on laptop speakers without digital clipping.
    audio = np.asarray(audio, dtype=np.float32)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 0.0:
        audio = audio * (0.95 / peak)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), audio, samplerate=sample_rate or 24000)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--text-file")
    parser.add_argument("--ref-audio", required=True)
    parser.add_argument("--ref-text-file", required=True)
    parser.add_argument("--output")
    parser.add_argument("--model", default="ai4bharat/IndicF5")
    args = parser.parse_args()

    ref_audio_path = Path(args.ref_audio)
    ref_text_path = Path(args.ref_text_file)

    for path, label in (
        (ref_audio_path, "reference audio"),
        (ref_text_path, "reference transcript"),
    ):
        if not path.is_file():
            raise FileNotFoundError(f"IndicF5 {label} not found: {path}")

    ref_text = ref_text_path.read_text(encoding="utf-8").strip()
    if not ref_text:
        raise ValueError("IndicF5 reference transcript is empty.")

    import torch
    from f5_tts.infer.utils_infer import preprocess_ref_audio_text

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, vocoder = _build_model(args.model, device)

    print("Preprocessing reference voice...", flush=True)
    ref_audio, normalized_ref_text = preprocess_ref_audio_text(
        str(ref_audio_path), ref_text, device=device
    )

    if args.serve:
        print("ANDY_READY", flush=True)
        for line in sys.stdin:
            try:
                request = json.loads(line)
                text = str(request.get("text") or "").strip()
                if not text:
                    raise ValueError("IndicF5 synthesis text is empty.")
                output_path = Path(request["output"])
                _synthesize(text, output_path, ref_audio, normalized_ref_text, model, vocoder, device)
                print("ANDY_RESULT " + json.dumps({"ok": True}), flush=True)
            except Exception as exc:
                print("ANDY_RESULT " + json.dumps({"ok": False, "error": str(exc)}), flush=True)
        return 0

    if not args.text_file or not args.output:
        parser.error("--text-file and --output are required unless --serve is used")
    text = Path(args.text_file).read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("IndicF5 synthesis text is empty.")
    output_path = Path(args.output)
    _synthesize(text, output_path, ref_audio, normalized_ref_text, model, vocoder, device)
    print(f"ANDY Voice v2 saved: {output_path}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"INDICF5_ERROR: {exc}", file=sys.stderr, flush=True)
        raise
