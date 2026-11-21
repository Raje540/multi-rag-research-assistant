"""
Embeddings from a hosted API, so a small server does not have to load an embedding model.

Works with any OpenAI-compatible "/embeddings" endpoint. Set on the server:

    EMBED_BASE_URL = https://<provider>/v1            (the address that ends before /embeddings)
    EMBED_API_KEY  = <your key>
    EMBED_MODEL    = <embedding model name from the provider>

Optional:
    EMBED_API_BATCH = 16     texts sent per request
"""
import os
import time

import requests
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

try:                                    # lets Chroma rebuild this function when it reopens a collection
    from chromadb.utils.embedding_functions import register_embedding_function
except Exception:                       # older / newer Chroma without the decorator
    def register_embedding_function(cls):
        return cls


@register_embedding_function
class HostedEmbeddingFunction(EmbeddingFunction[Documents]):
    def __init__(self, base_url: str = "", api_key: str = "", model: str = "", batch: int = 0):
        self.base_url = (base_url or os.getenv("EMBED_BASE_URL", "")).strip().rstrip("/")
        self.api_key = (api_key or os.getenv("EMBED_API_KEY", "")).strip()
        self.model = (model or os.getenv("EMBED_MODEL", "")).strip()
        self.batch = int(batch or os.getenv("EMBED_API_BATCH", "16"))

    # ---- one request, with a few retries when the free API says "too many requests" ----
    def _post(self, texts):
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        body = {"model": self.model, "input": texts}
        last = None
        for attempt in range(6):
            try:
                res = requests.post(f"{self.base_url}/embeddings", json=body, headers=headers, timeout=60)
                if res.status_code in (429, 500, 502, 503, 504):
                    last = RuntimeError(f"embedding API returned {res.status_code}: {res.text[:200]}")
                    time.sleep(min(2 ** attempt, 20))
                    continue
                res.raise_for_status()
                data = sorted(res.json()["data"], key=lambda d: d.get("index", 0))
                return [d["embedding"] for d in data]
            except requests.RequestException as exc:
                last = exc
                time.sleep(min(2 ** attempt, 20))
        raise RuntimeError(f"Hosted embedding request failed: {last}")

    def __call__(self, input: Documents) -> Embeddings:
        texts = [t if t else " " for t in input]
        out = []
        for i in range(0, len(texts), self.batch):
            out.extend(self._post(texts[i:i + self.batch]))
        return out

    # ---- what Chroma needs to store / rebuild the function (the key is never stored) ----
    @staticmethod
    def name() -> str:
        return "hosted-openai-compatible"

    def get_config(self):
        return {"base_url": self.base_url, "model": self.model, "batch": self.batch}

    @staticmethod
    def build_from_config(config):
        return HostedEmbeddingFunction(base_url=config.get("base_url", ""), model=config.get("model", ""),
                                       batch=config.get("batch", 0))