import json
import os
import urllib.error
import urllib.request


class LocalLLMError(RuntimeError):
    pass


class LocalLLM:
    """OpenAI-free local inference adapter for ANDY.

    Prefer Ollama's chat endpoint, but fall back to the generate endpoint when
    a local model/runner does not accept chat requests. Everything remains on
    the ARI-owned machine.
    """

    def __init__(self):
        self.base_url = os.getenv("ANDY_LLM_URL", "http://127.0.0.1:11434").rstrip("/")
        self.model = os.getenv("ANDY_LLM_MODEL", "qwen2.5-coder:3b")
        self.timeout = int(os.getenv("ANDY_LLM_TIMEOUT", "180"))

    def _post_json(self, path, payload):
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                body = exc.read().decode("utf-8", errors="replace").strip()
            except Exception:
                body = ""
            detail = body[:1000] if body else str(exc)
            raise LocalLLMError(f"Ollama {path} HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise LocalLLMError(f"Local Ollama connection failed at {path}: {exc}") from exc

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

    def chat(self, messages):
        chat_error = None
        try:
            data = self._post_json("/api/chat", {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_ctx": 8192,
                },
            })
            text = ((data.get("message") or {}).get("content") or "").strip()
            if text:
                return text
            chat_error = LocalLLMError("Ollama chat endpoint returned an empty response.")
        except LocalLLMError as exc:
            chat_error = exc

        # qwen2.5-coder also supports completion. This fallback makes ANDY
        # resilient if the installed Ollama runner rejects /api/chat.
        try:
            data = self._post_json("/api/generate", {
                "model": self.model,
                "prompt": self._messages_to_prompt(messages),
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_ctx": 8192,
                },
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
