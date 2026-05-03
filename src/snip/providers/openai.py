import os

from ..ai import AIError
from . import build_prompt, parse_response


def annotate(code: str, language: str, model: str) -> tuple[list[str], str]:
    try:
        from openai import OpenAI
        from openai import APIError, AuthenticationError, RateLimitError
    except ImportError:
        raise AIError("openai package not installed (pip install 'snip[openai]')")

    key = os.environ.get("SNIP_OPENAI_KEY")
    if not key:
        raise AIError("SNIP_OPENAI_KEY is not set")

    client = OpenAI(api_key=key)
    try:
        resp = client.chat.completions.create(
            model=model,
            max_tokens=300,
            messages=[{"role": "user", "content": build_prompt(code, language)}],
            response_format={"type": "json_object"},
        )
    except AuthenticationError:
        raise AIError("OpenAI rejected the API key")
    except RateLimitError:
        raise AIError("OpenAI rate limit or quota exceeded")
    except APIError as e:
        raise AIError(f"OpenAI API error: {e}")

    text = resp.choices[0].message.content or ""
    try:
        return parse_response(text)
    except ValueError as e:
        raise AIError(str(e))
