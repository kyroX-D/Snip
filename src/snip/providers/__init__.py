"""Shared helpers for provider modules: prompt template + response parsing."""

import json
import re


_PROMPT = """You analyze code snippets. Reply with a single JSON object — no markdown, no commentary — with these fields:
  "tags":        a list of 3 to 6 short, lowercase tag strings (technologies, concepts, intent)
  "description": one sentence, max 120 characters, describing what the snippet does

Language: {language}
Code:
{code}
"""


def build_prompt(code: str, language: str) -> str:
    # Cap prompt size so we don't ship huge payloads to the API.
    if len(code) > 4000:
        code = code[:4000] + "\n...[truncated]"
    return _PROMPT.format(code=code, language=language or "unknown")


def parse_response(text: str) -> tuple[list[str], str]:
    text = (text or "").strip()
    if not text:
        raise ValueError("empty response from model")

    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("model did not return JSON")
        data = json.loads(match.group(0))

    raw_tags = data.get("tags") or []
    if not isinstance(raw_tags, list):
        raw_tags = []
    tags = [str(t).strip().lower() for t in raw_tags if str(t).strip()][:6]
    description = str(data.get("description", "")).strip()
    return tags, description
