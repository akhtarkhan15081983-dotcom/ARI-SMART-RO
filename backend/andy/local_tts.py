import os
import subprocess
import sys
import tempfile
from pathlib import Path

from django.conf import settings


class LocalTTSError(RuntimeError):
    pass


class LocalTTS:
    """Fully local Piper text-to-speech for ANDY.

    Uses the already downloaded Hindi Rohan voice by default. Synthesis runs
    through the current Django virtual environment and never calls an external
    speech API.
    """

    def __init__(self):
        voices_dir = Path(os.getenv("ANDY_TTS_VOICES_DIR", Path(settings.BASE_DIR) / "andy" / "voices"))
        self.model_name = os.getenv("ANDY_TTS_MODEL", "hi_IN-rohan-medium")
        self.model_path = voices_dir / f"{self.model_name}.onnx"
        self.config_path = voices_dir / f"{self.model_name}.onnx.json"
        self.timeout = int(os.getenv("ANDY_TTS_TIMEOUT", "90"))

    def _validate(self):
        if not self.model_path.is_file():
            raise LocalTTSError(f"Piper voice model not found: {self.model_path}")
        if not self.config_path.is_file():
            raise LocalTTSError(f"Piper voice config not found: {self.config_path}")

    def synthesize(self, text: str) -> bytes:
        text = (text or "").strip()
        if not text:
            raise LocalTTSError("Text is required for ANDY voice.")
        if len(text) > 1800:
            text = text[:1800]

        self._validate()
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
                "-m",
                str(self.model_path),
                "-c",
                str(self.config_path),
                "-i",
                input_path,
                "-f",
                output_path,
                "--sentence-silence",
                "0.12",
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
        except LocalTTSError:
            raise
        except Exception as exc:
            raise LocalTTSError(f"Unable to create ANDY voice: {exc}") from exc
        finally:
            for path in (input_path, output_path):
                if path:
                    try:
                        os.remove(path)
                    except OSError:
                        pass
