import os
import subprocess
import sys
import tempfile
from pathlib import Path

from django.conf import settings


class LocalTTSError(RuntimeError):
    pass


class LocalTTS:
    """ANDY Voice v2 local TTS.

    Primary engine: IndicF5 in an isolated Python 3.10 environment.
    Automatic fallback: the existing Piper Hindi voice.

    Environment variables:
      ANDY_TTS_ENGINE=auto|indicf5|piper
      ANDY_INDICF5_PYTHON=<path to Voice-v2 python.exe>
      ANDY_INDICF5_REF_AUDIO=<path to clean reference WAV>
      ANDY_INDICF5_REF_TEXT=<path to UTF-8 transcript for that WAV>
      ANDY_INDICF5_MODEL=ai4bharat/IndicF5
    """

    def __init__(self):
        voices_dir = Path(os.getenv("ANDY_TTS_VOICES_DIR", Path(settings.BASE_DIR) / "andy" / "voices"))
        self.engine = os.getenv("ANDY_TTS_ENGINE", "auto").strip().lower()
        self.model_name = os.getenv("ANDY_TTS_MODEL", "hi_IN-rohan-medium")
        self.model_path = voices_dir / f"{self.model_name}.onnx"
        self.config_path = voices_dir / f"{self.model_name}.onnx.json"
        self.timeout = int(os.getenv("ANDY_TTS_TIMEOUT", "90"))

        default_voice_v2_python = Path(settings.BASE_DIR) / "andy_voice_v2" / "Scripts" / "python.exe"
        self.indic_python = Path(os.getenv("ANDY_INDICF5_PYTHON", default_voice_v2_python))
        self.indic_runner = Path(settings.BASE_DIR) / "andy" / "indicf5_runner.py"
        self.indic_ref_audio = Path(os.getenv("ANDY_INDICF5_REF_AUDIO", voices_dir / "andy_reference.wav"))
        self.indic_ref_text = Path(os.getenv("ANDY_INDICF5_REF_TEXT", voices_dir / "andy_reference.txt"))
        self.indic_model = os.getenv("ANDY_INDICF5_MODEL", "ai4bharat/IndicF5")
        self.indic_timeout = int(os.getenv("ANDY_INDICF5_TIMEOUT", "180"))

    def _validate_piper(self):
        if not self.model_path.is_file():
            raise LocalTTSError(f"Piper voice model not found: {self.model_path}")
        if not self.config_path.is_file():
            raise LocalTTSError(f"Piper voice config not found: {self.config_path}")

    def _indicf5_ready(self) -> bool:
        return (
            self.indic_python.is_file()
            and self.indic_runner.is_file()
            and self.indic_ref_audio.is_file()
            and self.indic_ref_text.is_file()
        )

    def _synthesize_indicf5(self, text: str) -> bytes:
        if not self._indicf5_ready():
            raise LocalTTSError(
                "IndicF5 is not configured. Voice-v2 Python, reference WAV and transcript are required."
            )

        input_path = None
        output_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8", newline="") as input_file:
                input_path = input_file.name
                input_file.write(text)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as output_file:
                output_path = output_file.name

            command = [
                str(self.indic_python),
                str(self.indic_runner),
                "--text-file", input_path,
                "--ref-audio", str(self.indic_ref_audio),
                "--ref-text-file", str(self.indic_ref_text),
                "--output", output_path,
                "--model", self.indic_model,
            ]
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.indic_timeout,
                check=False,
            )
            if completed.returncode != 0:
                detail = (completed.stderr or completed.stdout or "IndicF5 failed").strip()[-1600:]
                raise LocalTTSError(f"IndicF5 synthesis failed: {detail}")

            audio = Path(output_path).read_bytes()
            if len(audio) <= 44:
                raise LocalTTSError("IndicF5 returned empty audio.")
            return audio
        except subprocess.TimeoutExpired as exc:
            raise LocalTTSError("IndicF5 synthesis timed out.") from exc
        finally:
            for path in (input_path, output_path):
                if path:
                    try:
                        os.remove(path)
                    except OSError:
                        pass

    def _synthesize_piper(self, text: str) -> bytes:
        self._validate_piper()
        input_path = None
        output_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8", newline="") as input_file:
                input_path = input_file.name
                input_file.write(text)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as output_file:
                output_path = output_file.name

            command = [
                sys.executable,
                "-m",
                "piper",
                "-m", str(self.model_path),
                "-c", str(self.config_path),
                "-i", input_path,
                "-f", output_path,
                "--sentence-silence", "0.12",
            ]
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
                check=False,
            )
            if completed.returncode != 0:
                detail = (completed.stderr or completed.stdout or "Piper failed").strip()[:1200]
                raise LocalTTSError(f"Local Piper synthesis failed: {detail}")

            audio = Path(output_path).read_bytes()
            if len(audio) <= 44:
                raise LocalTTSError("Local Piper returned empty audio.")
            return audio
        except subprocess.TimeoutExpired as exc:
            raise LocalTTSError("Local Piper synthesis timed out.") from exc
        finally:
            for path in (input_path, output_path):
                if path:
                    try:
                        os.remove(path)
                    except OSError:
                        pass

    def synthesize(self, text: str) -> bytes:
        text = (text or "").strip()
        if not text:
            raise LocalTTSError("Text is required for ANDY voice.")
        if len(text) > 1800:
            text = text[:1800]

        if self.engine not in {"auto", "indicf5", "piper"}:
            raise LocalTTSError(f"Unsupported ANDY_TTS_ENGINE: {self.engine}")

        if self.engine == "piper":
            return self._synthesize_piper(text)

        if self.engine == "indicf5":
            return self._synthesize_indicf5(text)

        # auto: prefer the human-quality Voice v2 engine, but never break speech
        # if its environment/model/reference voice is temporarily unavailable.
        if self._indicf5_ready():
            try:
                return self._synthesize_indicf5(text)
            except LocalTTSError:
                pass

        return self._synthesize_piper(text)
