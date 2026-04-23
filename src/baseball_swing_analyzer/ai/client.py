"""Thin HTTP client for Ollama Cloud + generic vision API."""

from typing import Any


def _default_httpx_client():
    import httpx

    return httpx.Client(timeout=60.0, follow_redirects=True)


def _default_ollama_url() -> str:
    import os

    return os.environ.get("OLLAMA_URL", "https://api.ollama.com/v1")


def _default_ollama_key() -> str:
    import os

    return os.environ.get("OLLAMA_API_KEY", "")


class AiClient:
    """Simple wrapper around Ollama Cloud chat completions."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str = "mistral",
        client: Any | None = None,
    ):
        self.base_url = base_url or _default_ollama_url()
        self.api_key = api_key or _default_ollama_key()
        self.model = model
        self._client = client

    def _get_client(self):
        if self._client is None:
            self._client = _default_httpx_client()
        return self._client

    def chat(self, system: str | None, user: str) -> str:
        """Send a chat completion request. Returns the assistant text."""
        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        resp = self._get_client().post(
            f"{self.base_url}/chat/completions", json=payload, headers=headers
        )
        resp.raise_for_status()
        data = resp.json()
        return str(data["choices"][0]["message"]["content"])

    def vision(self, image_b64_uri: str, prompt: str, model: str | None = None) -> str:
        """Send a vision request with a base64 image. Returns short analysis text."""
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_b64_uri}},
                ],
            }
        ]
        payload = {
            "model": model or self.model,
            "messages": messages,
            "max_tokens": 200,
            "stream": False,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        resp = self._get_client().post(
            f"{self.base_url}/chat/completions", json=payload, headers=headers
        )
        resp.raise_for_status()
        data = resp.json()
        return str(data["choices"][0]["message"]["content"])
