"""Local model plumbing: OpenAI-compatible chat + ollama embeddings.

Defaults run fully on-device (ollama). Override with env vars for any
OpenAI-compatible endpoint.
"""
import json
import os
import urllib.request

LLM_BASE = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:11434/v1").rstrip("/")
LLM_MODEL = os.environ.get("LLM_MODEL", "gemma4:12b")
EMBED_URL = os.environ.get("EMBED_URL", "http://127.0.0.1:11434/api/embeddings")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")


def chat(messages, timeout=180):
    req = urllib.request.Request(
        f"{LLM_BASE}/chat/completions",
        data=json.dumps({"model": LLM_MODEL, "messages": messages,
                         "temperature": 0.2}).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer local"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)["choices"][0]["message"]["content"]


def embed(text, kind="search_document"):
    """nomic-embed-text needs asymmetric task prefixes; without them retrieval
    collapses into a flat similarity band (measured, not folklore)."""
    req = urllib.request.Request(
        EMBED_URL,
        data=json.dumps({"model": EMBED_MODEL,
                         "prompt": f"{kind}: {text}"}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["embedding"]


def extract_json(text):
    """Models fence JSON in prose; dig it out."""
    depth, start = 0, None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    start = None
    raise ValueError(f"no JSON object found in: {text[:200]!r}")
