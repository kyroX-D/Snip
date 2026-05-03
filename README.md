# snip

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![pip installable](https://img.shields.io/badge/pip-installable-brightgreen.svg)](#installation)

A local-first code snippet manager. Save snippets, optionally let an AI provider auto-tag and describe them, then search across everything in natural language. SQLite under the hood, no account required.

## Installation

```bash
git clone https://github.com/kyroX-D/Snip.git
cd Snip
pip install -e .
```

Optional dependency groups install the SDK for whichever AI provider you want to use:

```bash
pip install -e ".[anthropic]"   # Claude
pip install -e ".[openai]"      # GPT
pip install -e ".[google]"      # Gemini
pip install -e ".[all]"         # all three
```

Ollama needs no extra install — `snip` talks to it directly over HTTP.

## Commands

```bash
snip add                  # paste a snippet, auto-tagged if an AI provider is available
snip add --no-ai          # skip AI, save as-is
snip add --provider openai

snip list                 # tabular listing
snip search "redis pubsub"
snip show 42
snip copy 42              # to system clipboard
snip edit 42              # opens $EDITOR
snip delete 42
snip delete 42 --yes      # no confirmation

snip config               # which provider is active, key/dep status, db info
```

### Example

```bash
$ snip add
Paste code, then press Ctrl-D to finish:
def chunked(iterable, n):
    it = iter(iterable)
    while batch := list(islice(it, n)):
        yield batch
^D
Saved snippet #7 (python)
#python #generator #itertools #batching #utility

$ snip search batching
1 match(es):

╭──────────────────────────────────────╮
│ #7  python  2025-04-26 10:14         │
│ Yields successive n-sized chunks…    │
│ #python #generator #itertools …      │
╰──────────────────────────────────────╯
```

## AI providers

`snip` auto-detects which provider to use based on environment variables. Detection order is **Anthropic → OpenAI → Google → Ollama**. The first one with a valid key wins; if none are set, `snip` checks whether Ollama is running locally. If nothing is available, AI tagging is silently skipped and the snippet is saved as-is.

| Provider  | Env var               | Model                          | Cost                |
|-----------|-----------------------|--------------------------------|---------------------|
| Anthropic | `SNIP_ANTHROPIC_KEY`  | `claude-haiku-4-5-20251001`    | API billed          |
| OpenAI    | `SNIP_OPENAI_KEY`     | `gpt-4o-mini`                  | API billed          |
| Google    | `SNIP_GOOGLE_KEY`     | `gemini-1.5-flash`             | API billed          |
| Ollama    | (none)                | `llama3` on `localhost:11434`  | free, fully local   |

Cloud AI providers receive the snippet text for tagging. Use `--no-ai` to keep a snippet entirely local, or use Ollama for local-only tagging.

Override the auto-detected choice with `--provider` on `snip add`.

### Anthropic

```bash
export SNIP_ANTHROPIC_KEY=sk-ant-...
pip install -e ".[anthropic]"
```

### OpenAI

```bash
export SNIP_OPENAI_KEY=sk-...
pip install -e ".[openai]"
```

### Google (Gemini)

```bash
export SNIP_GOOGLE_KEY=...
pip install -e ".[google]"
```

### Ollama (local, free)

Install Ollama from <https://ollama.com>, then:

```bash
ollama pull llama3
ollama serve   # usually starts automatically
```

That's it. With no API keys set, `snip` will use Ollama by default when it is running. In that mode, snippet text stays on your machine.

## Privacy

All snippets live in a single SQLite file at `~/.snip/snippets.db` (mode `0600` on POSIX). Nothing is ever uploaded or transmitted, with one exception: when AI tagging is enabled, the snippet body is sent to whichever provider you configured. Pick Ollama if you want full local-only operation.

API keys are read from environment variables only. They are never logged, printed, or written to disk by `snip`.

## License

MIT
