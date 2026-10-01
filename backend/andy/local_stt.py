import gc
import json
import mimetypes
import os
import threading
import urllib.error
import urllib.request
import uuid

from django.conf import settings


class LocalSTTError(RuntimeError):
    pass


class LocalSTT:
    """Speech-to-text adapter.

    Development may explicitly use local Faster-Whisper. Production defaults to
    a separate inference service so the main Django process never loads a heavy
    STT model on the 512 MB API instance.
    """

    _model = None
    _lock = threading.Lock()

    def __init__(self):
        default_backend = "local" if settings.DEBUG else "remote"
        self.backend = os.getenv("ANDY_STT_BACKEND", default_backend).strip().lower()
        self.remote_url = os.getenv("ANDY_STT_URL", "").strip()
        self.remote_timeout = int(os.getenv("ANDY_STT_TIMEOUT", "90"))
        self.model_name = os.getenv("ANDY_STT_MODEL", "small")
        self.device = os.getenv("ANDY_STT_DEVICE", "cpu")
        self.compute_type = os.getenv("ANDY_STT_COMPUTE_TYPE", "int8")
        self.language = os.getenv("ANDY_STT_LANGUAGE", "hi").strip().lower()
        self.release_after_request = os.getenv("ANDY_STT_RELEASE_AFTER_REQUEST", "0") == "1"

    def _get_model(self):
        if self.backend != "local":
            raise LocalSTTError("In-process STT is disabled for this environment.")
        if not settings.DEBUG and os.getenv("ANDY_ALLOW_INPROCESS_AI", "0") != "1":
            raise LocalSTTError(
                "In-process STT is disabled in production. Configure ANDY_STT_URL."
            )
        if LocalSTT._model is not None:
            return LocalSTT._model
        try:
            from faster_whisper import WhisperModel

            LocalSTT._model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
            )
            return LocalSTT._model
        except Exception as exc:
            raise LocalSTTError(f"Unable to load local Whisper model: {exc}") from exc

    @classmethod
    def release_model(cls):
        cls._model = None
        gc.collect()

    def _transcribe_local(self, audio_path: str):
        with LocalSTT._lock:
            try:
                model = self._get_model()
                language = None if self.language in ("", "auto", "none") else self.language
                segments, info = model.transcribe(
                    audio_path,
                    language=language,
                    task="transcribe",
                    beam_size=2,
                    best_of=2,
                    vad_filter=True,
                    vad_parameters={"min_silence_duration_ms": 250},
                    condition_on_previous_text=False,
                    initial_prompt=(
                        "ARI SMART RO ANDY assistant. Hindi, English aur Hinglish conversation. "
                        "ANDY, namaste, Hindi, samajh, customer, engineer, service, installation, RO."
                    ),
                )
                text = " ".join(segment.text.strip() for segment in segments).strip()
                detected_language = getattr(info, "language", None)
                language_probability = float(getattr(info, "language_probability", 0.0) or 0.0)
            except LocalSTTError:
                raise
            except Exception as exc:
                raise LocalSTTError(f"Local speech recognition failed: {exc}") from exc
            finally:
                if self.release_after_request:
                    self.release_model()

        if not text:
            raise LocalSTTError(
                "No clear speech was detected. Please speak again closer to the microphone."
            )
        return {
            "text": text,
            "language": detected_language,
            "language_probability": language_probability,
        }

    def _transcribe_remote(self, audio_path: str):
        if not self.remote_url:
            raise LocalSTTError(
                "ANDY speech recognition service is unavailable. Configure ANDY_STT_URL."
            )

        boundary = f"----ariandy{uuid.uuid4().hex}"
        filename = os.path.basename(audio_path) or "voice.m4a"
        mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        with open(audio_path, "rb") as handle:
            audio = handle.read()

        language = "" if self.language in ("", "auto", "none") else self.language
        parts = []
        for name, value in (("language", language),):
            parts.extend([
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                str(value).encode("utf-8"),
                b"\r\n",
            ])
        parts.extend([
            f"--{boundary}\r\n".encode(),
            (
                f'Content-Disposition: form-data; name="audio"; filename="{filename}"\r\n'
                f"Content-Type: {mime}\r\n\r\n"
            ).encode(),
            audio,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ])
        body = b"".join(parts)
        request = urllib.request.Request(
            self.remote_url,
            data=body,
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.remote_timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise LocalSTTError(
                f"ANDY speech service returned HTTP {exc.code}."
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise LocalSTTError("ANDY speech recognition service is unavailable.") from exc

        text = str(payload.get("text") or "").strip()
        if not text:
            raise LocalSTTError("ANDY speech service returned no transcription.")
        return {
            "text": text,
            "language": payload.get("language"),
            "language_probability": float(payload.get("language_probability") or 0.0),
        }

    def transcribe(self, audio_path: str):
        if self.backend == "remote":
            return self._transcribe_remote(audio_path)
        if self.backend == "local":
            return self._transcribe_local(audio_path)
        raise LocalSTTError(f"Unsupported ANDY_STT_BACKEND: {self.backend}")
