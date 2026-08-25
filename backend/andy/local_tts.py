import os
import atexit
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from django.conf import settings


_indic_process = None
_indic_process_key = None


def _stop_indic_process():
    global _indic_process
    if _indic_process is not None and _indic_process.poll() is None:
        _indic_process.terminate()
    _indic_process = None


atexit.register(_stop_indic_process)


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
      ANDY_INDICF5_ALLOW_CPU=1 to opt into slow CPU IndicF5 in auto mode
    """

    def __init__(self):
        voices_dir = Path(os.getenv("ANDY_TTS_VOICES_DIR", Path(settings.BASE_DIR) / "andy" / "voices"))
        # Keep the current release fast on CPU-only laptops. IndicF5 remains
        # available as an explicit opt-in for the next optimized voice version.
        self.engine = os.getenv("ANDY_TTS_ENGINE", "piper").strip().lower()
        self.model_name = os.getenv("ANDY_TTS_MODEL", "hi_IN-rohan-medium")
        self.model_path = voices_dir / f"{self.model_name}.onnx"
        self.config_path = voices_dir / f"{self.model_name}.onnx.json"
        self.timeout = int(os.getenv("ANDY_TTS_TIMEOUT", "90"))

        repo_root = Path(settings.BASE_DIR).parent
        default_voice_v2_python = repo_root / "voice_v2_clean" / "Scripts" / "python.exe"
        self.indic_python = Path(os.getenv("ANDY_INDICF5_PYTHON", default_voice_v2_python))
        self.indic_runner = Path(settings.BASE_DIR) / "andy" / "indicf5_runner.py"
        self.indic_ref_audio = Path(os.getenv("ANDY_INDICF5_REF_AUDIO", voices_dir / "andy_reference.wav"))
        self.indic_ref_text = Path(os.getenv("ANDY_INDICF5_REF_TEXT", voices_dir / "andy_reference.txt"))
        self.indic_model = os.getenv("ANDY_INDICF5_MODEL", "ai4bharat/IndicF5")
        self.indic_timeout = int(os.getenv("ANDY_INDICF5_TIMEOUT", "180"))
        self.indic_allow_cpu = os.getenv("ANDY_INDICF5_ALLOW_CPU", "0").strip().lower() in {"1", "true", "yes"}

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

    def _indicf5_fast_enough_for_auto(self) -> bool:
        # The presence of an NVIDIA driver does not mean the isolated IndicF5
        # Torch build has CUDA support. Stay fast by default; users can opt in
        # after verifying CUDA with ANDY_INDICF5_ALLOW_CPU=1, or force the
        # engine with ANDY_TTS_ENGINE=indicf5.
        return self.indic_allow_cpu

    def _synthesize_indicf5(self, text: str) -> bytes:
        global _indic_process, _indic_process_key
        if not self._indicf5_ready():
            raise LocalTTSError(
                "IndicF5 is not configured. Voice-v2 Python, reference WAV and transcript are required."
            )

        output_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as output_file:
                output_path = output_file.name

            process_key = (
                str(self.indic_python), str(self.indic_runner),
                str(self.indic_ref_audio), str(self.indic_ref_text), self.indic_model,
            )
            if (_indic_process is None or _indic_process.poll() is not None or
                    _indic_process_key != process_key):
                _stop_indic_process()
                command = [str(self.indic_python), str(self.indic_runner), "--serve",
                "--ref-audio", str(self.indic_ref_audio),
                "--ref-text-file", str(self.indic_ref_text),
                "--model", self.indic_model]
                _indic_process = subprocess.Popen(
                    command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                    errors="replace", bufsize=1,
                )
                _indic_process_key = process_key

            _indic_process.stdin.write(json.dumps({"text": text, "output": output_path}) + "\n")
            _indic_process.stdin.flush()
            recent_output = []
            while True:
                line = _indic_process.stdout.readline()
                if not line:
                    raise LocalTTSError("IndicF5 persistent runner stopped unexpectedly.")
                recent_output.append(line.strip())
                recent_output = recent_output[-20:]
                if line.startswith("ANDY_RESULT "):
                    result = json.loads(line[len("ANDY_RESULT "):])
                    if not result.get("ok"):
                        raise LocalTTSError(f"IndicF5 synthesis failed: {result.get('error')}")
                    break

            audio = Path(output_path).read_bytes()
            if len(audio) <= 44:
                raise LocalTTSError("IndicF5 returned empty audio.")
            return audio
        except (BrokenPipeError, OSError, json.JSONDecodeError) as exc:
            _stop_indic_process()
            raise LocalTTSError(f"IndicF5 persistent runner failed: {exc}") from exc
        finally:
            for path in (output_path,):
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
        if self._indicf5_ready() and self._indicf5_fast_enough_for_auto():
            try:
                return self._synthesize_indicf5(text)
            except LocalTTSError:
                pass

        return self._synthesize_piper(text)
