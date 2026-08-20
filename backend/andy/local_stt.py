import gc
import os
import threading

from faster_whisper import WhisperModel


class LocalSTTError(RuntimeError):
    pass


class LocalSTT:
    """Fully local speech-to-text tuned for the 16 GB development PC.

    Whisper is loaded only while a voice request is being transcribed and is
    released afterwards. This is slower than keeping it resident, but leaves
    substantially more RAM available for Ollama/Qwen.
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
                segments, info = model.transcribe(
                    audio_path,
                    beam_size=1,
                    best_of=1,
                    vad_filter=True,
                    condition_on_previous_text=False,
                )
                text = " ".join(segment.text.strip() for segment in segments).strip()
                language = getattr(info, "language", None)
                language_probability = float(getattr(info, "language_probability", 0.0) or 0.0)
            except LocalSTTError:
                raise
            except Exception as exc:
                raise LocalSTTError(f"Local speech recognition failed: {exc}") from exc
            finally:
                # Critical on the current PC: do not keep Whisper resident while
                # Ollama loads the coding model for ANDY's response.
                self.release_model()

        if not text:
            raise LocalSTTError("No clear speech was detected. Please speak again closer to the microphone.")
        return {
            "text": text,
            "language": language,
            "language_probability": language_probability,
        }
