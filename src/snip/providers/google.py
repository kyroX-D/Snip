import os

from ..ai import AIError
from . import build_prompt, parse_response


def annotate(code: str, language: str, model: str) -> tuple[list[str], str]:
    try:
        import google.generativeai as genai
    except ImportError:
        raise AIError(
            "google-generativeai package not installed (pip install 'snip[google]')"
        )

    key = os.environ.get("SNIP_GOOGLE_KEY")
    if not key:
        raise AIError("SNIP_GOOGLE_KEY is not set")

    genai.configure(api_key=key)
    try:
        client = genai.GenerativeModel(model)
        resp = client.generate_content(build_prompt(code, language))
    except Exception as e:
        msg = str(e).lower()
        if any(s in msg for s in ("api key", "unauthenticated", "permission denied")):
            raise AIError("Google rejected the API key")
        raise AIError(f"Google API error: {e}")

    text = (getattr(resp, "text", "") or "").strip()
    try:
        return parse_response(text)
    except ValueError as e:
        raise AIError(str(e))
