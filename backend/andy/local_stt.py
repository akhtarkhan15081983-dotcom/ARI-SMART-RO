import gc
import os
import threading

from faster_whisper import WhisperModel


class LocalSTTError(RuntimeError):
    pass


class LocalSTT:
    """Fully local speech-to-text tuned for Hindi, English and Hinglish.

    Whisper is loaded only while a voice request is being transcribed and is
    released afterwards so Ollama has enough RAM on the 16 GB development PC.
    """

    _model = None
    _lock = threading.Lock()

    def __init__(self):
        # "small" is materially better than "base" for Indian/Hindi speech,
        # while still being practical on the current CPU/RAM setup.
        self.model_name = os.getenv("ANDY_STT_MODEL", "small")
        self.device = os.getenv("ANDY_STT_DEVICE", "cpu")
        self.compute_type = os.getenv("ANDY_STT_COMPUTE_TYPE", "int8")
        # Default to Hindi because ANDY is primarily used in Hindi/Hinglish.
        # Set ANDY_STT_LANGUAGE=auto if unrestricted language detection is wanted.
        self.language = os.getenv("ANDY_STT_LANGUAGE", "hi").strip().lower()

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
                    beam_size=5,
                    best_of=5,
                    vad_filter=True,
                    vad_parameters={"min_silence_duration_ms": 350},
                    condition_on_previous_text=False,
                    initial_prompt=(
                        "यह ARI SMART RO के ANDY assistant से हिंदी, English और Hinglish में बातचीत है। "
                        "नाम ANDY है। सामान्य भारतीय हिंदी और English technical words को सही लिखें।"
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
                self.release_model()

        if not text:
            raise LocalSTTError("No clear speech was detected. Please speak again closer to the microphone.")
        return {
            "text": text,
            "language": detected_language,
            "language_probability": language_probability,
        }
