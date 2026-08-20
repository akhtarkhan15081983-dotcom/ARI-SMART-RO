import os
import threading

from faster_whisper import WhisperModel


class LocalSTTError(RuntimeError):
    pass


class LocalSTT:
    """Fully local speech-to-text using faster-whisper.

    The model is loaded lazily and kept in memory after the first request.
    `base` is the default because it is multilingual and practical on the
    current 16 GB development PC. The model may be overridden with
    ANDY_STT_MODEL without changing application code.
    """

    _model = None
    _lock = threading.Lock()

    def __init__(self):
        self.model_name = os.getenv("ANDY_STT_MODEL", "base")
        self.device = os.getenv("ANDY_STT_DEVICE", "cpu")
        self.compute_type = os.getenv("ANDY_STT_COMPUTE_TYPE", "int8")

    def _get_model(self):
        if LocalSTT._model is not None:
            return LocalSTT._model
        with LocalSTT._lock:
            if LocalSTT._model is None:
                try:
                    LocalSTT._model = WhisperModel(
                        self.model_name,
                        device=self.device,
                        compute_type=self.compute_type,
                    )
                except Exception as exc:
                    raise LocalSTTError(f"Unable to load local Whisper model: {exc}") from exc
        return LocalSTT._model

    def transcribe(self, audio_path: str):
        try:
            model = self._get_model()
            segments, info = model.transcribe(
                audio_path,
                beam_size=3,
                vad_filter=True,
                condition_on_previous_text=False,
            )
            text = " ".join(segment.text.strip() for segment in segments).strip()
        except LocalSTTError:
            raise
        except Exception as exc:
            raise LocalSTTError(f"Local speech recognition failed: {exc}") from exc

        if not text:
            raise LocalSTTError("No clear speech was detected. Please speak again closer to the microphone.")
        return {
            "text": text,
            "language": getattr(info, "language", None),
            "language_probability": float(getattr(info, "language_probability", 0.0) or 0.0),
        }
