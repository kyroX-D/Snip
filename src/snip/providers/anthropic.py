import os

from ..ai import AIError
from . import build_prompt, parse_response


def annotate(code: str, language: str, model: str) -> tuple[list[str], str]:
    try:
        import anthropic
    except ImportError:
        raise AIError("anthropic package not installed (pip install 'snip[anthropic]')")

    key = os.environ.get("SNIP_ANTHROPIC_KEY")
    if not key:
        raise AIError("SNIP_ANTHROPIC_KEY is not set")

    client = anthropic.Anthropic(api_key=key)
    try:
        msg = client.messages.create(
            model=model,
            max_tokens=300,
            messages=[{"role": "user", "content": build_prompt(code, language)}],
        )
    except anthropic.AuthenticationError:
        raise AIError("Anthropic rejected the API key")
    except anthropic.RateLimitError:
        raise AIError("Anthropic rate limit exceeded")
    except anthropic.APIError as e:
        raise AIError(f"Anthropic API error: {e}")

    text = "".join(
        getattr(b, "text", "") for b in msg.content if getattr(b, "type", "") == "text"
    )
    try:
        return parse_response(text)
    except ValueError as e:
        raise AIError(str(e))
