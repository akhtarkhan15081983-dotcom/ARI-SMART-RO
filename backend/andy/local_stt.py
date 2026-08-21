import gc
import os
import threading

from faster_whisper import WhisperModel


class LocalSTTError(RuntimeError):
    pass


class LocalSTT:
    """Fully local speech-to-text tuned for fast Hindi/English/Hinglish use."""

    _model = None
    _lock = threading.Lock()

    def __init__(self):
        self.model_name = os.getenv("ANDY_STT_MODEL", "small")
        self.device = os.getenv("ANDY_STT_DEVICE", "cpu")
        self.compute_type = os.getenv("ANDY_STT_COMPUTE_TYPE", "int8")
        self.language = os.getenv("ANDY_STT_LANGUAGE", "hi").strip().lower()
        # Keep Whisper resident by default. Re-loading the model on every utterance
        # was a major source of latency. Set ANDY_STT_RELEASE_AFTER_REQUEST=1 if a
        # low-memory machine needs the old unload-after-each-request behaviour.
        self.release_after_request = os.getenv("ANDY_STT_RELEASE_AFTER_REQUEST", "0") == "1"

    def _get_model(self):
        if LocalSTT._model is not None:
            return LocalSTT._model
        try:
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

    def transcribe(self, audio_path: str):
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
            raise LocalSTTError("No clear speech was detected. Please speak again closer to the microphone.")
        return {
            "text": text,
            "language": detected_language,
            "language_probability": language_probability,
        }
