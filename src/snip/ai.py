import os
from dataclasses import dataclass
from typing import Callable


class AIError(Exception):
    """An AI provider call failed in a recoverable way."""


class AIUnavailable(AIError):
    """No provider is configured or reachable."""


@dataclass
class ProviderInfo:
    name: str
    env_var: str | None
    model: str
    reason: str


# Resolution order for auto-detect.
_PROVIDERS: list[tuple[str, str | None, str]] = [
    ("anthropic", "SNIP_ANTHROPIC_KEY", "claude-haiku-4-5-20251001"),
    ("openai",    "SNIP_OPENAI_KEY",    "gpt-4o-mini"),
    ("google",    "SNIP_GOOGLE_KEY",    "gemini-1.5-flash"),
    ("ollama",    None,                 "llama3"),
]


def list_providers() -> list[tuple[str, str | None, str]]:
    return list(_PROVIDERS)


def select_provider(override: str | None = None) -> ProviderInfo:
    if override:
        for name, env, model in _PROVIDERS:
            if name == override:
                return ProviderInfo(name, env, model, "selected via --provider")
        raise AIError(f"unknown provider: {override}")

    for name, env, model in _PROVIDERS:
        if env and os.environ.get(env):
            return ProviderInfo(name, env, model, f"{env} is set")

    # No keys fall back to local Ollama if it's actually running.
    if _ollama_running():
        return ProviderInfo("ollama", None, "llama3", "no API keys set, using local Ollama")

    raise AIUnavailable("no AI provider configured")


def annotate(code: str, language: str, provider: ProviderInfo) -> tuple[list[str], str]:
    """Return (tags, description). Raises AIError on failure."""
    fn = _load_provider(provider.name)
    return fn(code, language, provider.model)


def test_connection(provider: ProviderInfo) -> tuple[bool, str]:
    try:
        annotate("print('hello')", "python", provider)
        return True, "ok"
    except AIError as e:
        return False, str(e)
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def _ollama_running() -> bool:
    import urllib.error
    import urllib.request
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=1) as r:
            return r.status == 200
    except Exception:
        return False


def _load_provider(name: str) -> Callable[[str, str, str], tuple[list[str], str]]:
    if name == "anthropic":
        from .providers.anthropic import annotate as fn
    elif name == "openai":
        from .providers.openai import annotate as fn
    elif name == "google":
        from .providers.google import annotate as fn
    elif name == "ollama":
        from .providers.ollama import annotate as fn
    else:
        raise AIError(f"unknown provider: {name}")
    return fn
