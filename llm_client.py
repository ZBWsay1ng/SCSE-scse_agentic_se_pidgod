"""Shared local Ollama transport; every call starts an isolated conversation."""

import json
import urllib.error
import urllib.request


MODEL_NAME = "qwen3:8b"
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"


def ask_qwen(system_prompt, user_prompt, *, json_output=False):
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "think": False,
        "options": {"temperature": 0},
    }
    if json_output:
        payload["format"] = "json"
    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(
            "Cannot complete the local Qwen request. Check 'ollama serve' "
            "and 'ollama list' (qwen3:8b is required)."
        ) from exc
    content = result["message"]["content"]
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Qwen returned empty content.")
    return content
