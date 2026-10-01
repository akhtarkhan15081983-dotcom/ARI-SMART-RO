import json
import os
import urllib.error
import urllib.request

from django.conf import settings


class LocalLLMError(RuntimeError):
    pass


class LocalLLM:
    """OpenAI-free local inference adapter for ANDY, tuned for low latency."""

    def __init__(self):
        default_url = "http://127.0.0.1:11434" if settings.DEBUG else ""
        self.base_url = os.getenv("ANDY_LLM_URL", default_url).strip().rstrip("/")
        self.service_token = os.getenv("ANDY_AI_SERVICE_TOKEN", "").strip()
        self.model = os.getenv("ANDY_LLM_MODEL", "qwen2.5:3b")
        self.timeout = int(os.getenv("ANDY_LLM_TIMEOUT", "120"))
        self.remote_retries = max(0, min(int(os.getenv("ANDY_AI_REMOTE_RETRIES", "1")), 1))
        self.num_ctx = int(os.getenv("ANDY_LLM_NUM_CTX", "1536"))
        self.num_predict = int(os.getenv("ANDY_LLM_NUM_PREDICT", "96"))
        # Keeping the 3B model warm removes repeated model-start cost. The value
        # is intentionally bounded rather than permanent for the development PC.
        self.keep_alive = os.getenv("ANDY_LLM_KEEP_ALIVE", "10m")

    def _post_json(self, path, payload):
        if not self.base_url:
            raise LocalLLMError(
                "ANDY language service is unavailable. Configure ANDY_LLM_URL."
            )
        headers = {"Content-Type": "application/json"}
        if self.service_token:
            headers["Authorization"] = f"Bearer {self.service_token}"
        elif not settings.DEBUG:
            raise LocalLLMError(
                "ANDY AI service token is not configured."
            )
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        attempts = self.remote_retries + 1
        last_error = None
        for attempt in range(attempts):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code in {502, 503, 504} and attempt + 1 < attempts:
                    continue
                try:
                    body = exc.read().decode("utf-8", errors="replace").strip()
                except Exception:
                    body = ""
                detail = body[:1000] if body else str(exc)
                raise LocalLLMError(f"ANDY language service {path} HTTP {exc.code}: {detail}") from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
                if attempt + 1 < attempts:
                    continue
                raise LocalLLMError(f"ANDY language service unavailable at {path}.") from exc
            except ValueError as exc:
                raise LocalLLMError(f"ANDY language service returned invalid JSON at {path}.") from exc
        raise LocalLLMError(f"ANDY language service unavailable at {path}.") from last_error

    @staticmethod
    def _messages_to_prompt(messages):
        parts = []
        for item in messages:
            role = (item.get("role") or "user").upper()
            content = (item.get("content") or "").strip()
            if content:
                parts.append(f"{role}:\n{content}")
        parts.append("ASSISTANT:\n")
        return "\n\n".join(parts)

    def _options(self):
        return {
            "temperature": 0.1,
            "num_ctx": self.num_ctx,
            "num_predict": self.num_predict,
        }

    def chat(self, messages):
        # ANDY is Hindi/Hinglish-first on the ARI SMART RO mobile app. Keeping
        # replies short also makes high-quality local IndicF5 practical on CPU.
        policy = (
            "Final answer only natural Hindi or simple Indian Hinglish mein do. "
            "English-only answer mat do. Maximum do chhote vakya aur 180 characters. "
            "User ka sawal repeat mat karo, placeholder mat do, seedha factual jawab do. "
            "RO troubleshooting mein inlet water pressure, sediment/pre-carbon filters, RO membrane, "
            "booster pump, solenoid valve, flow restrictor, storage-tank pressure, leakage aur TDS ko "
            "relevant symptoms ke hisab se check karne ki practical salah do."
        )
        messages = [dict(item) for item in messages]
        if messages and messages[0].get("role") == "system":
            messages[0]["content"] = (messages[0].get("content") or "") + "\n\n" + policy
        else:
            messages.insert(0, {"role": "system", "content": policy})
        chat_error = None
        try:
            data = self._post_json("/api/chat", {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "keep_alive": self.keep_alive,
                "options": self._options(),
            })
            text = ((data.get("message") or {}).get("content") or "").strip()
            if text:
                return text
            chat_error = LocalLLMError("Ollama chat endpoint returned an empty response.")
        except LocalLLMError as exc:
            chat_error = exc

        try:
            data = self._post_json("/api/generate", {
                "model": self.model,
                "prompt": self._messages_to_prompt(messages),
                "stream": False,
                "keep_alive": self.keep_alive,
                "options": self._options(),
            })
            text = (data.get("response") or "").strip()
            if text:
                return text
            raise LocalLLMError("Ollama generate endpoint returned an empty response.")
        except LocalLLMError as generate_error:
            raise LocalLLMError(
                f"Local ANDY model failed. Chat error: {chat_error}. "
                f"Generate error: {generate_error}"
            ) from generate_error
