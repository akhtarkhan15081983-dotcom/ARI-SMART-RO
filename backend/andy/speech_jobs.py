import atexit
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from django.db import close_old_connections

from .local_tts import LocalTTS, LocalTTSError
from .models import AndySpeechJob


_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="andy-tts")
_active_job_ids = set()
_active_job_ids_lock = Lock()
atexit.register(lambda: _executor.shutdown(wait=False, cancel_futures=True))


def _run_speech_job(job_id):
    close_old_connections()
    try:
        job = AndySpeechJob.objects.get(id=job_id)
        AndySpeechJob.objects.filter(id=job_id).update(status="RUNNING")
        audio = LocalTTS().synthesize(job.text)
        AndySpeechJob.objects.filter(id=job_id).update(status="COMPLETED", audio=audio, error="")
    except (AndySpeechJob.DoesNotExist, LocalTTSError) as exc:
        AndySpeechJob.objects.filter(id=job_id).update(status="FAILED", error=str(exc), audio=None)
    except Exception as exc:
        AndySpeechJob.objects.filter(id=job_id).update(status="FAILED", error=f"Unable to create ANDY voice: {exc}", audio=None)
    finally:
        with _active_job_ids_lock:
            _active_job_ids.discard(job_id)
        close_old_connections()


def enqueue_speech_job(job_id):
    with _active_job_ids_lock:
        if job_id in _active_job_ids:
            return False
        _active_job_ids.add(job_id)
    _executor.submit(_run_speech_job, job_id)
    return True
