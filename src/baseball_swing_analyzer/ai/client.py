"""Thin HTTP client for Ollama Cloud + generic vision API."""

import os
from typing import Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _default_httpx_client():
    import httpx

    return httpx.Client(timeout=60.0, follow_redirects=True)


def _default_ollama_url() -> str:
    return os.environ.get("OLLAMA_URL", "https://ollama.com/v1")


def _default_ollama_key() -> str:
    return os.environ.get("OLLAMA_API_KEY", "")


def _default_model() -> str:
    return os.environ.get("OLLAMA_MODEL", "kimi-k2.5")


def _extract_response(data: dict) -> str:
    """Extract text from an Ollama Cloud chat completion response.

    Some models (e.g. kimi-k2.5) return their output in a ``reasoning`` field
    with empty ``content``. We fall back to ``reasoning`` when ``content`` is
    absent or empty.
    """
    choice = data["choices"][0]["message"]
    text = choice.get("content") or ""
    if not text:
        text = choice.get("reasoning") or ""
    return text


class AiClient:
    """Simple wrapper around Ollama Cloud chat completions."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        client: Any | None = None,
    ):
        self.base_url = base_url or _default_ollama_url()
        self.api_key = api_key or _default_ollama_key()
        self.model = model or _default_model()
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
        return _extract_response(resp.json())

    def vision(
        self,
        prompt: str,
        images: list[str] | str,
        model: str | None = None,
        max_tokens: int = 400,
    ) -> str:
        """Send a vision request with one or more base64 data-URI images.

        *images* can be a single ``data:image/jpeg;base64,...`` string
        or a list of them.
        """
        if isinstance(images, str):
            images = [images]

        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        for img in images:
            content.append({"type": "image_url", "image_url": {"url": img}})

        messages = [{"role": "user", "content": content}]
        payload = {
            "model": model or self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": False,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        resp = self._get_client().post(
            f"{self.base_url}/chat/completions", json=payload, headers=headers
        )
        resp.raise_for_status()
        return _extract_response(resp.json())
