import json
import os
import urllib.error
import urllib.request


class LocalLLMError(RuntimeError):
    pass


class LocalLLM:
    """OpenAI-free local inference adapter for ANDY.

    Defaults are intentionally conservative for the current 16 GB ARI
    development PC. Ollama is asked to unload the model after each response so
    Whisper and Flutter/Django do not have to compete with a permanently loaded
    LLM. Environment variables can raise these limits later on a larger server.
    """

    def __init__(self):
        self.base_url = os.getenv("ANDY_LLM_URL", "http://127.0.0.1:11434").rstrip("/")
        self.model = os.getenv("ANDY_LLM_MODEL", "qwen2.5-coder:3b")
        self.timeout = int(os.getenv("ANDY_LLM_TIMEOUT", "180"))
        self.num_ctx = int(os.getenv("ANDY_LLM_NUM_CTX", "2048"))
        self.num_predict = int(os.getenv("ANDY_LLM_NUM_PREDICT", "384"))
        self.keep_alive = os.getenv("ANDY_LLM_KEEP_ALIVE", "0s")

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

    def _options(self):
        return {
            "temperature": 0.2,
            "num_ctx": self.num_ctx,
            "num_predict": self.num_predict,
        }

    def chat(self, messages):
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
