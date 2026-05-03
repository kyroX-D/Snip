import json
import urllib.error
import urllib.request

from ..ai import AIError
from . import build_prompt, parse_response


OLLAMA_URL = "http://localhost:11434/api/generate"


def annotate(code: str, language: str, model: str) -> tuple[list[str], str]:
    payload = json.dumps({
        "model": model,
        "prompt": build_prompt(code, language),
        "stream": False,
        "format": "json",
    }).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise AIError(f"Ollama returned HTTP {e.code}")
    except urllib.error.URLError as e:
        raise AIError(f"could not reach Ollama at localhost:11434 ({e.reason})")
    except TimeoutError:
        raise AIError("Ollama request timed out")

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        raise AIError("Ollama returned an invalid response")

    text = data.get("response", "")
    try:
        return parse_response(text)
    except ValueError as e:
        raise AIError(str(e))
