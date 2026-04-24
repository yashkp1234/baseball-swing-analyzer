"""Smoke-test local Ollama for vision + multi-image support."""
import base64
import json
import urllib.request

import cv2
import numpy as np


def _make_image(text: str, color: tuple[int, int, int]) -> str:
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    img[:] = color
    cv2.putText(img, text, (20, 110), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
    _, buf = cv2.imencode(".png", img)
    return base64.b64encode(buf.tobytes()).decode("utf-8")


def _chat(model: str, prompt: str, images: list[str] | None = None) -> dict:
    msg: dict = {"role": "user", "content": prompt}
    if images:
        msg["images"] = images
    payload = {"model": model, "messages": [msg], "stream": False}
    req = urllib.request.Request(
        "http://localhost:11434/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def main() -> None:
    models = ["kimi-k2.6:cloud", "gemma4:26b", "qwen3.5:9b"]
    for model in models:
        print(f"\n=== {model} ===")
        # 1. Text-only sanity check
        r = _chat(model, "Say exactly: hello")
        if "error" in r:
            print(f"TEXT FAIL: {r['error']}")
            continue
        print(f"TEXT OK: {r['message']['content'].strip()!r}")

        # 2. Single-image vision check
        b64 = _make_image("RED", (0, 0, 255))
        r = _chat(model, "What color is the background? Answer in one word.", images=[b64])
        if "error" in r:
            print(f"VISION FAIL: {r['error']}")
            continue
        print(f"VISION OK: {r['message']['content'].strip()!r}")

        # 3. Multi-image temporal check
        frames = [
            _make_image("1", (255, 0, 0)),
            _make_image("2", (0, 255, 0)),
            _make_image("3", (0, 0, 255)),
        ]
        r = _chat(
            model,
            "These are 3 frames in order. List the numbers you see, separated by commas.",
            images=frames,
        )
        if "error" in r:
            print(f"MULTI FAIL: {r['error']}")
            continue
        print(f"MULTI OK: {r['message']['content'].strip()!r}")


if __name__ == "__main__":
    main()
