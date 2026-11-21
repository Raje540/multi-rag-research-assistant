"""
One place that talks to the language model.

Default (nothing to set): local Ollama, exactly as before.

Hosted mode: set these environment variables on the server and the same code uses
any OpenAI-compatible API (Groq, Gemini's OpenAI endpoint, OpenRouter, ...):

    LLM_BASE_URL = https://api.groq.com/openai/v1
    LLM_API_KEY  = <your key>
    LLM_MODEL    = <model name from the provider's model list>
"""
import os

import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").strip().rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "").strip()


def hosted() -> bool:
    return bool(LLM_BASE_URL)


def model_name() -> str:
    return (LLM_MODEL or OLLAMA_MODEL) if hosted() else OLLAMA_MODEL


def generate(prompt: str, *, timeout: int = 180, temperature=None, max_tokens=None,
             num_ctx=None, keep_alive=None) -> str:
    """Return the model's text answer. Raises on any HTTP / network error."""
    if hosted():
        body = {"model": LLM_MODEL, "messages": [{"role": "user", "content": prompt}]}
        if temperature is not None:
            body["temperature"] = temperature
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        headers = {"Authorization": f"Bearer {LLM_API_KEY}"} if LLM_API_KEY else {}
        res = requests.post(f"{LLM_BASE_URL}/chat/completions", json=body, headers=headers, timeout=timeout)
        res.raise_for_status()
        return (res.json()["choices"][0]["message"].get("content") or "").strip()

    body = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
    if keep_alive:
        body["keep_alive"] = keep_alive
    options = {}
    if temperature is not None:
        options["temperature"] = temperature
    if max_tokens is not None:
        options["num_predict"] = max_tokens
    if num_ctx is not None:
        options["num_ctx"] = num_ctx
    if options:
        body["options"] = options
    res = requests.post(OLLAMA_URL, json=body, timeout=timeout)
    res.raise_for_status()
    return (res.json().get("response") or "").strip()