import os
import re
import math
import logging
import requests
from collections import Counter
from backend.services.vector_service import search_similar_chunks
from backend.database import SessionLocal
from backend.models import Paper

logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
# Mistral on CPU often needs far more than 5s; the old timeout made Ollama
# fail silently and forced every question into the fallback.
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "180"))

STOPWORDS = {
    "a", "an", "the", "of", "in", "on", "for", "to", "and", "or", "is", "are", "was",
    "were", "be", "been", "this", "that", "these", "those", "with", "by", "as", "at",
    "from", "it", "its", "what", "which", "who", "how", "why", "when", "where", "does",
    "do", "did", "used", "use", "paper", "key", "main", "pretrained", "can", "has", "have",
}


# --------------------------------------------------------------------------- #
# Retrieval
# --------------------------------------------------------------------------- #
def retrieve_context_for_query(project_id: int, query: str, top_k: int = 6):
    try:
        proj_id_int = int(project_id)
    except (ValueError, TypeError):
        proj_id_int = project_id

    # If the question names a paper ("the FakeNewsNet paper ..."), search only that paper
    named_ids = _papers_named_in_query(proj_id_int, query)
    scopes = named_ids if named_ids else [None]

    # Multi-part questions ("X, Y, and Z?") retrieve better when each part is
    # searched separately and the results are merged.
    sub_queries = _split_query(query)
    per_query_k = max(top_k // len(sub_queries), 3) if len(sub_queries) > 1 else top_k

    by_scope, seen = {}, set()
    for pid in scopes:
        found = []
        for q in [query] + (sub_queries if len(sub_queries) > 1 else []):
            # Fetch a few extra chunks, because low-value chunks are dropped below
            results = search_similar_chunks(
                project_id=proj_id_int, query=q, top_k=per_query_k + 2, paper_id_filter=pid
            )
            for item in _parse_results(results):
                key = item["text"].strip()[:100]
                if key in seen:
                    continue
                seen.add(key)
                found.append(item)
        # Lowest distance (most similar) first
        found.sort(key=lambda e: e["distance"] if e["distance"] is not None else 1e9)
        by_scope[pid] = found

    # When several papers are named, give each one an equal share of the evidence
    if len(scopes) > 1:
        cap = max(2, (top_k + 2) // len(scopes))
        evidence = [e for pid in scopes for e in by_scope[pid][:cap]]
        limit = max(top_k + 2, cap * len(scopes))
    else:
        evidence = by_scope[scopes[0]]
        limit = top_k + 2
    evidence.sort(key=lambda e: e["distance"] if e["distance"] is not None else 1e9)

    # Drop table-number dumps, and remove figure-panel labels like (a) (b) (c),
    # which mislead the model into treating them as answers
    useful = [e for e in evidence if not _is_low_value(e["text"])]
    if useful:
        evidence = useful
    for e in evidence:
        e["text"] = _strip_panel_labels(e["text"])
    return evidence[:limit]


_PAPER_WORDS = ("paper", "article", "study", "survey", "work", "authors", "repository")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", (text or "").lower())).strip()


def _papers_named_in_query(project_id: int, query: str):
    """
    IDs of papers in the project whose title is named in the question.
    A title counts when it appears in the question together with a word like
    'paper' or 'survey' (a single-word title such as 'FakeNewsNet' is enough alone).
    """
    q = _norm(query)
    if not q:
        return []
    try:
        db = SessionLocal()
        try:
            titles = [(p.id, p.title) for p in db.query(Paper).filter(Paper.project_id == project_id).all() if p.title]
        finally:
            db.close()
    except Exception as exc:
        logger.warning("Could not look up paper titles: %s", exc)
        return []

    mentions_paper = any(re.search(rf"\b{w}\b", q) for w in _PAPER_WORDS)
    ids = []
    for pid, title in titles:
        core = _norm(title.split(":")[0])   # the part before the subtitle
        if len(core) < 8:
            continue
        if re.search(rf"\b{re.escape(core)}\b", q) and (" " not in core or mentions_paper):
            ids.append(pid)
    return ids


def _is_low_value(text: str) -> bool:
    """True for chunks that are mostly numbers (table dumps)."""
    words = text.split()
    if len(words) < 8:
        return False
    numeric = sum(1 for w in words if re.fullmatch(r"[\d.,%()\-±/:+]+", w))
    return numeric / len(words) > 0.5


def _strip_panel_labels(text: str) -> str:
    """Remove figure panel markers such as (a) (b) (c) when a chunk has several of them."""
    if len(re.findall(r"\([a-h]\)", text)) >= 3:
        return re.sub(r"\s*\([a-h]\)\s*", " ", text).strip()
    return text


def _split_query(query: str):
    parts = re.split(r",|\band\b|;|\?", query)
    parts = [p.strip() for p in parts if len(p.strip().split()) >= 2]
    return parts if len(parts) > 1 else [query]


def _parse_results(search_results):
    out = []
    if not (isinstance(search_results, dict) and search_results.get("documents")):
        return out
    docs_list = search_results["documents"]
    metas_list = search_results.get("metadatas", [])
    dists_list = search_results.get("distances", [])
    if not docs_list or not isinstance(docs_list[0], list):
        return out
    docs = docs_list[0]
    metas = metas_list[0] if metas_list and isinstance(metas_list[0], list) else []
    dists = dists_list[0] if dists_list and isinstance(dists_list[0], list) else []
    for i, doc in enumerate(docs):
        meta = metas[i] if i < len(metas) and isinstance(metas[i], dict) else {}
        out.append({
            "paper_id": meta.get("paper_id", 0),
            "page": meta.get("page", 1),
            "distance": dists[i] if i < len(dists) else None,
            "text": doc,
        })
    return out


# --------------------------------------------------------------------------- #
# Prompt + LLM
# --------------------------------------------------------------------------- #
def generate_rag_prompt(query: str, evidence_chunks: list) -> str:
    if not evidence_chunks:
        return f"No relevant evidence found for query: '{query}'."

    context_str = ""
    for idx, item in enumerate(evidence_chunks, start=1):
        context_str += f"\n--- EVIDENCE BLOCK {idx} (Paper ID: {item['paper_id']}, Page: {item['page']}) ---\n"
        context_str += f"{item['text']}\n"

    return f"""You are an evidence-traceable research assistant. Answer the user's question using ONLY the provided evidence blocks.

STRICT RULES:
1. Answer exactly what the question asks. Do not describe unrelated topics found in the evidence.
2. Use a short bulleted response.
3. Cite sources as [Paper <ID>, Page X] after each point.
4. If the answer cannot be found in the evidence, say: "Insufficient evidence in the uploaded documents."
5. Only describe what the evidence blocks say. Never claim that a paper does not discuss something; say only that the provided evidence does not mention it.
6. Ignore figure or chart labels such as (a) (b) (c), table numbers, and reference lists. Use only full explanatory sentences.
7. When evidence comes from different papers, say which paper (by Paper ID) each point comes from.

USER QUESTION:
{query}

PROVIDED EVIDENCE:
{context_str}

ANSWER:"""


def generate_answer_with_llm(prompt: str, evidence_chunks: list, query: str = "") -> str:
    if not evidence_chunks:
        return "Insufficient evidence in the uploaded documents."

    # Recover the question from the prompt if the caller didn't pass it
    if not query:
        m = re.search(r"USER QUESTION:\s*(.*?)\s*PROVIDED EVIDENCE:", prompt, re.S)
        query = m.group(1).strip() if m else ""

    try:
        res = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=OLLAMA_TIMEOUT,
        )
        if res.status_code == 200:
            text = res.json().get("response", "").strip()
            if text:
                return text
        logger.warning("Ollama returned status %s: %s", res.status_code, res.text[:200])
    except Exception as exc:
        logger.warning("Ollama call failed, using extractive fallback: %s", exc)

    return extractive_answer(query, evidence_chunks)


# --------------------------------------------------------------------------- #
# Question-aware fallback (no LLM needed)
# --------------------------------------------------------------------------- #
def _tokens(text: str):
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9\-]+", text.lower())
    return [_stem(w) for w in words if w not in STOPWORDS]


def _stem(w: str) -> str:
    for suf in ("ing", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: -len(suf)]
    return w


def extractive_answer(query: str, evidence_chunks: list, max_sentences: int = 6) -> str:
    q_tokens = set(_tokens(query))
    if not q_tokens:
        return "Insufficient evidence in the uploaded documents."

    # Split every chunk into sentences, remembering where each came from
    sentences = []
    for chunk in evidence_chunks:
        text = re.sub(r"\s+", " ", chunk["text"])
        for s in re.split(r"(?<=[.!?])\s+", text):
            if len(s.split()) >= 5:
                sentences.append((s.strip(), chunk["paper_id"], chunk["page"]))

    if not sentences:
        return "Insufficient evidence in the uploaded documents."

    # IDF over sentences so rare query words (e.g. "RST", "GloVe") count more
    n = len(sentences)
    df = Counter()
    for s, _, _ in sentences:
        df.update(set(_tokens(s)))
    idf = {t: math.log((n + 1) / (df[t] + 1)) + 1 for t in q_tokens}

    scored = []
    for s, pid, page in sentences:
        s_tokens = set(_tokens(s))
        overlap = q_tokens & s_tokens
        if not overlap:
            continue
        score = sum(idf[t] for t in overlap) / (len(s.split()) ** 0.3)
        scored.append((score, s, pid, page))

    if not scored:
        return "Insufficient evidence in the uploaded documents."

    scored.sort(key=lambda x: x[0], reverse=True)
    best = scored[:max_sentences]

    lines = [f"* {s} [Paper {pid}, Page {page}]" for _, s, pid, page in best]
    return "**Most relevant passages for your question:**\n\n" + "\n\n".join(lines)