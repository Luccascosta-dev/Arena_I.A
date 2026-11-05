"""Gladiadores. A player is anything that can stream text for a task.

Two kinds ship today:
  * mock:sprint / mock:verbose — fake agents that type deterministic answers
    (so the arena works offline and in CI, no keys attached)
  * openai:<model>             — anything speaking the OpenAI chat-completions
    protocol: OpenAI proper, OpenRouter, Groq, Ollama (`OPENAI_BASE_URL`),
    LM Studio, vLLM…
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request


class Player:
    name: str

    def stream(self, task: str):
        raise NotImplementedError


# ── mocks ────────────────────────────────────────────────────────────────────
_SPRINT = """Quick fix — no ceremony.

The bug: `line.split(',')` is blind to quotes, so a comma inside `"a,b"`
splits where it must not.

```python
def split_csv_line(line: str) -> list[str]:
    out, cell, quoted = [], [], False
    for ch in line:
        if ch == '"':
            quoted = not quoted
        elif ch == ',' and not quoted:
            out.append("".join(cell)); cell = []
        else:
            cell.append(ch)
    out.append("".join(cell))
    return out
```

One pass, O(n), no dependency. Ship it.
"""

_VERBOSE = """Let me think out loud, carefully.

Scanning '{task}' … the parser crashes on quoted fields because it splits
on every comma instead of every *top-level* comma. Classic.

My plan:
  1. walk the line char by char;
  2. keep a boolean `quoted`, toggled by `"`;
  3. commit a cell only on an unquoted comma;
  4. always commit the last cell.

And then a unit test for the exact case that hurt:
`parse_line('a,"b,c",d') == ['a', 'b,c', 'd']`

```python
def split_csv_line(line: str) -> list[str]:
    out, cell, quoted = [], [], False
    for ch in line:
        if ch == '"':
            quoted = not quoted
        elif ch == ',' and not quoted:
            out.append("".join(cell)); cell = []
        else:
            cell.append(ch)
    out.append("".join(cell))
    return out
```
"""

_MOCKS = {
    "sprint": (_SPRINT, 0.004, 3),      # (text, delay/char, chunk size)
    "verbose": (_VERBOSE, 0.007, 3),
}


class MockPlayer(Player):
    def __init__(self, style: str):
        if style not in _MOCKS:
            raise ValueError(f"unknown mock {style!r} (try 'sprint' or 'verbose')")
        self.style = style
        self.name = f"mock:{style}"

    def stream(self, task: str):
        text, delay, chunk = _MOCKS[self.style]
        body = text.replace("{task}", task.strip()[:60])
        for i in range(0, len(body), chunk):
            yield body[i : i + chunk]
            time.sleep(delay * chunk)


# ── OpenAI-compatible ────────────────────────────────────────────────────────
class OpenAIPlayer(Player):
    def __init__(self, model: str):
        if not model:
            raise ValueError("openai:<model> needs a model name")
        self.model = model
        self.name = f"openai:{model}"

    def stream(self, task: str):
        base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        url = f"{base}/chat/completions"
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY not set — export it, or run `arena run --offline` "
                "to brawl against the built-in mocks."
            )
        body = json.dumps(
            {
                "model": self.model,
                "messages": [{"role": "user", "content": task}],
                "stream": True,
                "max_tokens": 1024,
            }
        ).encode()
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
        )
        try:
            resp = urllib.request.urlopen(req, timeout=180)
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read(300).decode(errors="replace")
            finally:
                raise RuntimeError(
                    f"API error {e.code} for {self.model} — {detail or e.reason} "
                    f"(check the model name / OPENAI_BASE_URL, or run --offline)"
                ) from None
        with resp:
            for raw in resp:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                try:
                    j = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                choices = j.get("choices") or []
                if choices:
                    delta = (choices[0].get("delta") or {}).get("content")
                    if delta:
                        yield delta


# ── factory ──────────────────────────────────────────────────────────────────
def build(spec: str) -> Player:
    """'mock:sprint' | 'openai:gpt-5-mini' -> Player."""
    if spec.startswith("mock:"):
        return MockPlayer(spec[5:])
    if spec.startswith("openai:"):
        return OpenAIPlayer(spec[7:])
    raise ValueError(
        f"unknown player/spec {spec!r} — use 'mock:sprint', 'mock:verbose' "
        f"or 'openai:<model>'"
    )
