import json
import os
import urllib.error
import urllib.request


class LocalLLMError(RuntimeError):
    pass


class LocalLLM:
    """OpenAI-free local inference adapter.

    Defaults to the locally installed Ollama-compatible endpoint and a 3B
    coding model sized for the current ARI development PC. No request is sent
    to an external AI provider.
    """

    def __init__(self):
        self.base_url = os.getenv("ANDY_LLM_URL", "http://127.0.0.1:11434").rstrip("/")
        self.model = os.getenv("ANDY_LLM_MODEL", "qwen2.5-coder:3b")
        self.timeout = int(os.getenv("ANDY_LLM_TIMEOUT", "120"))

    def chat(self, messages):
        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.2},
        }).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise LocalLLMError(f"Local ANDY model is unavailable: {exc}") from exc

        text = ((data.get("message") or {}).get("content") or "").strip()
        if not text:
            raise LocalLLMError("Local ANDY model returned an empty response.")
        return text
