"""
Evidence Analysis agent.

For every paper it builds one short, cited summary for each dimension
(Methodology, Dataset, Results, Limitations) using only that paper's own
indexed chunks. The summaries are saved as small JSON files so the analysis
is not recomputed every time (the local model is slow on a laptop).
"""
import os
import re
import json
import logging
import tempfile
from datetime import datetime

import requests

from backend.services.vector_service import search_similar_chunks, get_or_create_collection
from backend.services.rag_service import _is_low_value, _strip_panel_labels
from backend.services.pdf_service import looks_like_references

logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "180"))

# Bump this whenever the analysis logic changes: results saved by an older version are ignored
CODE_VERSION = "18"

ANALYSIS_DIR = os.path.join("data", "analysis")
os.makedirs(ANALYSIS_DIR, exist_ok=True)

# What to look for in each paper
DIMENSIONS = {
    "Novelty": {
        "category": "Other",       # abstracts, introductions and conclusions are tagged "Other"
        "query": "abstract: in this paper we propose, we present a novel approach; main contributions of this paper; to the best of our knowledge; unlike previous work",
        "meaning": "what is new in this paper: the contribution the authors claim",
        "keywords": ["novel", "propose", "contribution", "first", "introduce", "present"],
        "rule": "Report only what the authors themselves claim as new.",
        "cues": ["novel", "we propose", "we introduce", "we present", "we develop", "we construct", "contribution",
                 "to the best of our knowledge", "for the first time", "in this paper", "in this article", "in this survey"],
        "sections": ["abstract", "introduction", "conclusion"],
        "extra_queries": ["In this paper, we present", "The main contributions of this work are",
                          "In conclusion, this paper has proposed and shown"],
        "first_pages": 2,
        "top_k": 14,
    },
    "Methodology": {
        "category": "Methodology",
        "query": "in this paper we propose present develop our approach method, this survey reviews, main contribution of this work",
        "meaning": "the approach, model, method or resource (for example a data repository) that the paper itself proposes or builds. Not future work, not related work",
        "keywords": ["propose", "method", "approach", "model", "framework", "algorithm", "architecture", "survey", "review"],
        "rule": ("Name the technique, model or features THIS paper uses (for example SVM, CNN, LIWC features). "
                 "If the paper is a survey or review, say what it reviews and how it organizes the topic. "
                 "Use only sentences where the authors talk about their OWN work (we propose, in this paper, in this article). "
                 "Never describe other researchers' methods as this paper's method."),
        "cues": ["we propose", "we present", "our approach", "our method", "strategy", "pipeline",
                 "in this survey", "in this article", "in this paper", "we review", "reviewing", "we explored", "we develop"],
        "sections": ["methodology"],
    },
    "Dataset": {
        "category": "Dataset",
        "query": "datasets used data collection corpus data sources",
        "meaning": "the datasets or data sources the paper uses, builds or describes",
        "keywords": ["dataset", "data set", "corpus", "collected", "data", "benchmark", "annotated"],
        "rule": ("Name the datasets using the exact names written in the evidence (for example PolitiFact, GossipCop), "
                 "and say how they were collected if the evidence says so. Do not invent dataset names. "
                 "If the paper is a survey, say that it lists or reviews these datasets instead of saying it uses them."),
        "cues": ["dataset", "data set", "corpus", "collected", "crawl", "annotated", "repository"],
        "sections": ["dataset"],
    },
    "Results": {
        "category": "Results",
        "query": "results accuracy performance evaluation findings",
        "meaning": "the main experimental findings or performance numbers",
        "keywords": ["accuracy", "result", "performance", "outperform", "f1", "precision", "recall", "achieve", "show"],
        "rule": ("Prefer numbers that are written in sentences (for example 'SAF/A provides 66.7% accuracy'). "
                 "Never read a number out of a table with several columns, because the columns get mixed up; "
                 "if only a table is available, say in words which model performed best, without numbers. "
                 "Do not explain metric formulas. If the paper reports no experiments (for example a survey), answer: Not stated"),
        "cues": ["accuracy", "outperform", "perform better", "results are shown", "f1", "precision", "recall"],
        "sections": ["results", "experiments", "discussion"],
    },
    "Limitations": {
        "category": "Limitations",
        "query": "limitations future work challenges open issues",
        "meaning": "stated limitations, open challenges or future work",
        "keywords": ["limitation", "future", "challenge", "open", "plan", "however", "remain"],
        "rule": ("Report a limitation ONLY if the evidence explicitly says something is a limitation, weakness, "
                 "challenge, open problem or future work. Describing how data was collected or how the method works "
                 "is NOT a limitation. If nothing is explicit, answer: Not stated"),
        "cues": ["limitation", "future work", "future research", "future direction", "open issue", "open problem",
                 "challenge", "we will", "we plan", "remain"],
        "sections": ["limitations", "conclusion", "discussion"],
        "section_read": r"open|future|limitation|discussion|conclusion|challenge",
        "top_k": 14,
    },
}


# --------------------------------------------------------------------------- #
# Text helpers
# --------------------------------------------------------------------------- #
# Rows of table numbers ("0.580 0.611 0.717 0.659 ...") get their columns mixed up by a small
# model, so the numbers are removed and only the sentences around the table are kept.
_NUM_RUN = re.compile(r"(?:[-+]?\d*\.\d+%?\s+){4,}[-+]?\d*\.\d+%?"          # table rows: 0.580 0.611 0.717 ...
                      r"|(?:[-+]?\d*\.?\d+%?\s+){5,}[-+]?\d*\.?\d+%?")       # chart axes: 20 40 60 80 100 0.4 0.6
# Split into sentences, but not after "et al."
_SENT_SPLIT = re.compile(r"(?<=[.!?])(?<!et al\.)\s+")
# A citation marker: [37]  [76; 77]  et al.  (Shu et al. 2017)  (Smith and Jones, 2016)
_CITE = re.compile(r"\[\d{1,3}(?:\s*[;,–-]\s*\d{1,3})*\]|\bet al\b|\([A-Z][A-Za-z]+(?: and [A-Z][A-Za-z]+)?,? \d{4}\)")
_FIRST_PERSON = re.compile(r"\b(?:we|our|this (?:paper|article|survey|work|study)|in this (?:paper|article|survey|work))\b", re.I)


def _strip_table_numbers(text: str) -> str:
    return _NUM_RUN.sub("[table values omitted]", text)


def _dehyphenate(text: str) -> str:
    """PDF line breaks leave 'se- lection' and 'Fak- eNewsNet'; join them back.
    Also drops footnote numbers glued to a name: 'FakeNewsNet20' -> 'FakeNewsNet'."""
    text = re.sub(r"(?<=[A-Za-z])- (?=[a-z])", "", text)
    text = re.sub(r"(?<=[A-Z]{3})- (?=[A-Z]{2,})", "", text)               # "CRED- BANK" -> "CREDBANK"
    text = re.sub(r"(?<=[a-z]{4})- (?=[A-Z][a-z]{2,}\b)", "", text)         # "Politi- Fact" -> "PolitiFact"
    text = re.sub(r"(?<=[a-z\)])\.(\d{1,2})(?=\s+[A-Z])", ".", text)      # footnote number after a full stop
    return re.sub(r"\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\d{1,2}\b", r"\1", text)


def _strip_urls(text: str) -> str:
    """Web addresses in footnotes ('github.com/KaiDMML/FakeNewsNet') make a small model invent facts."""
    return re.sub(r"(?:https?://|www\.)\S+|\b[\w-]+\.(?:com|org|net|edu)/\S+", " ", text)


def _strip_captions(text: str) -> str:
    """Figure and table captions ('Figure 1: Learning curves on ...') are not content for the model."""
    return re.sub(r"\b(?:Figure|Fig\.|Table)\s*\d+:[^.]{0,160}\.?", " ", text)


# "FAKE NEWS CHARACTERIZATION In this section ..." -> an ALL-CAPS heading stuck to the front of a sentence
_CAPS_HEADING = re.compile(r"^(?:\d+(?:\.\d+)*\s+)?(?:[A-Z][A-Z0-9 \-]{6,}?)\s+(?=[A-Z][a-z])")


def _own_work_text(text: str) -> str:
    """Drop sentences that describe OTHER authors' work (they cite someone and never say 'we')."""
    sents = _SENT_SPLIT.split(re.sub(r"\s+", " ", text))
    kept = [s for s in sents if _FIRST_PERSON.search(s) or not _CITE.search(s)]
    return " ".join(kept) if kept else text


_FUTURE = re.compile(r"\bwe (?:will|plan|intend|aim to)\b|\bplan to\b|\bin the future\b|\bfuture (?:work|research|directions?|studies)\b", re.I)


# "To date, approaches have relied on ... The Onion, PolitiFact and Snopes" describes OTHER people's data
_PRIOR_WORK = re.compile(r"\bto date\b|\bhave relied\b|\bhas relied\b|\bprevious (?:work|studies|research)\b|\bprior work\b|"
                         r"\bresearchers have\b|\bhave been used by\b|\bhas been used by\b", re.I)


def _drop_future_text(text: str) -> str:
    """Plans ('we will extend the repository to curated data collections') are not what the paper did,
    so they must not leak into the Dataset, Methodology or Results rows."""
    parts = _SENT_SPLIT.split(re.sub(r"\s+", " ", text).strip())
    parts = [x for x in parts if not _PRIOR_WORK.search(x)]
    if len(parts) > 1 and not (parts[0][:1].isupper() or parts[0][:1].isdigit() or parts[0][:1] in "\"'“‘("):
        parts = parts[1:]                              # the chunk starts in the middle of a sentence ("or curated data collections.")
    kept = [x for x in parts if not _FUTURE.search(x)]
    return " ".join(kept)


# --------------------------------------------------------------------------- #
# Gathering evidence
# --------------------------------------------------------------------------- #
def _parse(results):
    out = []
    if not (isinstance(results, dict) and results.get("documents") and results["documents"][0]):
        return out
    docs = results["documents"][0]
    metas = results["metadatas"][0] if results.get("metadatas") else []
    dists = results["distances"][0] if results.get("distances") else []
    for i, doc in enumerate(docs):
        meta = metas[i] if i < len(metas) and isinstance(metas[i], dict) else {}
        out.append({
            "distance": dists[i] if i < len(dists) else None,
            "page": meta.get("page", 1),
            "section": meta.get("section", "unknown"),
            "category": meta.get("category", "Other"),
            "text": _strip_panel_labels(_strip_table_numbers(_strip_captions(_strip_urls(_dehyphenate(doc))))),
            "_raw": doc,
        })
    # Drop table-number dumps and bibliography text (references are never evidence)
    return [e for e in out if not _is_low_value(e["_raw"]) and not looks_like_references(e["_raw"])]


# Metric definitions such as "Precision = |TP| / (|TP| + |FP|)" are not results
_FORMULA = re.compile(r"\b(precision|recall|accuracy|f1|f-measure)\b\s*=|\|\s*T[PN]\s*\||\|\s*F[PN]\s*\|", re.I)


def _drop_formula_chunks(items: list) -> list:
    kept = [e for e in items if not _FORMULA.search(e["_raw"])]
    return kept or items          # if everything is a formula, keep what we have


def _first_pages(project_id: int, paper_id: int, max_page: int):
    """All chunks of the paper's first pages (abstract + introduction), read directly from the store."""
    try:
        got = get_or_create_collection(project_id).get(
            where={"$and": [{"paper_id": int(paper_id)}, {"page": {"$lte": int(max_page)}}]},
            include=["documents", "metadatas"],
        )
        docs, metas = got.get("documents") or [], got.get("metadatas") or []
        if not docs:
            return []
        order = sorted(range(len(docs)), key=lambda i: (metas[i].get("page", 1), metas[i].get("chunk_index", 0)))
        return _parse({"documents": [[docs[i] for i in order]], "metadatas": [[metas[i] for i in order]]})
    except Exception as exc:
        logger.warning("Could not read the first pages of paper %s: %s", paper_id, exc)
        return []


_HEADING_TEXT = re.compile(r"\b(?:OPEN ISSUES|FUTURE WORK|FUTURE RESEARCH|LIMITATIONS)\b")


def _section_chunks(project_id: int, paper_id: int, category: str, section_pattern: str):
    """Chunks of a paper whose SECTION HEADING matches (e.g. 'Open Issues and Future Research'),
    read directly from the store. A semantic search alone can miss them."""
    try:
        got = get_or_create_collection(project_id).get(
            where={"paper_id": int(paper_id)},               # any category: stored tags can be out of date
            include=["documents", "metadatas"],
        )
        docs, metas = got.get("documents") or [], got.get("metadatas") or []
        keep = [i for i in range(len(docs))
                if re.search(section_pattern, str(metas[i].get("section", "")), re.I) or _HEADING_TEXT.search(docs[i])]
        keep.sort(key=lambda i: (metas[i].get("page", 1), metas[i].get("chunk_index", 0)))
        items = _parse({"documents": [[docs[i] for i in keep]], "metadatas": [[metas[i] for i in keep]]})
        for e in items:
            e["distance"] = 0.30                      # found by its heading, so rank it high
        return items
    except Exception as exc:
        logger.warning("Could not read sections of paper %s: %s", paper_id, exc)
        return []


def _gather_evidence(project_id: int, paper_id: int, dimension: str, top_k: int = 3):
    """Best chunks of ONE paper for a dimension. Prefers chunks tagged with the matching category."""
    cfg = DIMENSIONS[dimension]
    extra = top_k + 3          # ask for more than needed, because some chunks are dropped or re-ranked
    tagged_items = _parse(search_similar_chunks(
        project_id=project_id, query=cfg["query"], top_k=extra,
        paper_id_filter=paper_id, category_filter=cfg["category"],
    ))
    # Section tags are not always right, so also look at the paper's closest text of any category
    any_items = _parse(search_similar_chunks(
        project_id=project_id, query=cfg["query"], top_k=extra, paper_id_filter=paper_id,
    ))
    for q in cfg.get("extra_queries", []):      # a few more phrasings (Novelty) so the key sentence is not missed
        any_items += _parse(search_similar_chunks(
            project_id=project_id, query=q, top_k=extra, paper_id_filter=paper_id,
        ))
    if cfg.get("first_pages"):                  # Novelty: the abstract and introduction, read directly
        any_items += _first_pages(project_id, paper_id, cfg["first_pages"])
    if cfg.get("section_read"):                 # Limitations: the "Open issues / Future work" section itself
        any_items += _section_chunks(project_id, paper_id, cfg["category"], cfg["section_read"])

    pool, seen = [], set()
    for e in tagged_items + any_items:
        key = e["_raw"].strip()[:100]
        if key not in seen:
            seen.add(key)
            pool.append(e)

    # Related Work describes OTHER papers, so it is not evidence about this one
    pool = [e for e in pool if e["category"] != "Related Work"] or pool
    if dimension == "Results":
        pool = _drop_formula_chunks(pool)
        # Keep only chunks that talk about results, when there are any (drops future-work text)
        with_cues = [e for e in pool if any(c in e["_raw"].lower() for c in cfg["cues"])]
        pool = with_cues or pool

    pool.sort(key=lambda e: _score(e, cfg))
    chosen = pool[:top_k]
    if dimension in ("Methodology", "Novelty"):
        for e in chosen:                      # what the model sees = what the user sees
            e["text"] = _own_work_text(e["text"])
    if dimension in ("Methodology", "Dataset", "Results"):
        cleaned = [(e, _drop_future_text(e["text"])) for e in chosen]
        if any(t.strip() for _, t in cleaned):             # a chunk that was only future plans is left out
            for e, t in cleaned:
                e["text"] = t
            chosen = [e for e, t in cleaned if t.strip()]
    tagged = any(e["category"] == cfg["category"] for e in chosen)
    return chosen, tagged


_RESULT_WORDS = ("accuracy", "precision", "recall", "f1")


def _score(e: dict, cfg: dict) -> float:
    """Lower is better: similarity distance, adjusted by what the chunk actually says."""
    s = e["distance"] if e.get("distance") is not None else 1.0
    low = e["_raw"].lower()
    if e["category"] == cfg["category"]:
        s -= 0.05                                   # tags help a little, but are sometimes wrong
    if e["section"] in cfg["sections"]:
        s -= 0.04
    s -= 0.04 * min(sum(1 for c in cfg["cues"] if c in low), 4)   # the wording matters most
    # A results table is not a description of the method
    if cfg["category"] == "Methodology" and sum(low.count(w) for w in _RESULT_WORDS) >= 4:
        s += 0.25
    # Contribution claims sit in the abstract and the start of the introduction
    if cfg["category"] == "Other" and int(e.get("page") or 99) <= 2:
        s -= 0.08
    # Text that names datasets ("PolitiFact dataset", "CREDBANK dataset") is the best Dataset evidence
    if cfg["category"] == "Dataset":
        s -= 0.08 * min(len(_DATASET_NAME.findall(e["_raw"])), 2)
    return s


_DATASET_NAME = re.compile(r"\b(?:[A-Z][a-z]+[A-Z][A-Za-z0-9]*|[A-Z]{3,}[A-Za-z0-9]*)\s+(?:dataset|data set|corpus)\b")


# --------------------------------------------------------------------------- #
# Summaries: local LLM, with a no-LLM fallback
# --------------------------------------------------------------------------- #
def _llm_summary(title: str, dimension: str, evidence: list) -> str:
    meaning = DIMENSIONS[dimension]["meaning"]
    rule = DIMENSIONS[dimension]["rule"]
    blocks ="\n".join(
        f"[Page {e['page']}, section: {e['section']}] {e['text'][:700]}" for e in evidence
    )
    prompt = f"""You are filling one cell of a comparison table about a research paper.

Paper: {title}
Dimension: {dimension} = {meaning}

Rules:
- Use ONLY the evidence below. Do not add anything that is not in it.
- Describe only what THIS paper itself does, builds or finds (not future work, not other papers' work).
- Start directly with the answer. No introduction such as "Here is the answer", and do not repeat the dimension name.
- Answer in at most 2 short sentences (under 45 words).
- Ignore formulas and metric definitions. For Results, give concrete findings or numbers.
- If the evidence does not state it, answer with exactly these two words and nothing else: Not stated
- Never write "Not stated" after other text.
- {rule}

EVIDENCE:
{blocks}

ANSWER:"""
    res = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "10m",
            "options": {"temperature": 0.1, "num_predict": 120, "num_ctx": 2048},
        },
        timeout=OLLAMA_TIMEOUT,
    )
    res.raise_for_status()
    text = (res.json().get("response") or "").strip()
    text = re.sub(r"^[\s\-\*•]+", "", text)          # drop leading bullets
    if not text:
        raise ValueError("empty answer from the model")
    return _clean_summary(text)


def _clean_summary(text: str) -> str:
    """Remove the chatty parts a small model adds, so each table cell is a clean sentence."""
    text = re.sub(r"\s+", " ", (text or "").replace("[table values omitted]", "")).strip()
    # "Here is the answer in 2 short sentences:"
    text = re.sub(r"^here(?:'s| is| are)\b[^:.]{0,80}:\s*", "", text, flags=re.I)
    text = re.sub(r"^(?:answer|response)\s*:\s*", "", text, flags=re.I)
    # "Methodology: ..." (the table row already says it)
    text = re.sub(r"^(?:methodology|dataset|results|limitations)\s*:\s*", "", text, flags=re.I)
    # "Precision: Not stated" / "Open challenges: Not stated"
    text = re.sub(r"[A-Za-z][A-Za-z /-]{0,50}:\s*Not stated\.?", "", text, flags=re.I)
    # "... Not stated" added after a real answer
    text = re.sub(r"\bNot stated\b\.?", "", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip(" :;-")
    if _FORMULA.search(text):          # a metric definition is not a finding
        return "Not stated"
    if len(text.split()) >= 3 or re.search(r"\d", text):
        return text
    return "Not stated"


_TABLE_FRAGMENT = re.compile(r"\[table values omitted\]|^(?:table|figure|fig\.)\s*\d+", re.I)


_BULLET = re.compile(r"\s*[•●▪■]\s*")
_ENDS_OK = re.compile(r"[.!?][\"'”’)\]]?\d{0,2}$")


def _sentences(text: str) -> list:
    """Split text into COMPLETE sentences only.
    A chunk can start or end in the middle of a sentence ("... definitions in" / "of the paper ...").
    Such pieces are dropped: they must start with a capital letter and end with . ! or ?"""
    out = []
    for part in _BULLET.split(re.sub(r"\s+", " ", text).strip()):
        for s in _SENT_SPLIT.split(part):
            s = s.strip()
            if not s or not _ENDS_OK.search(s):
                continue
            if not (s[0].isupper() or s[0].isdigit() or s[0] in "\"'“‘("):
                continue
            out.append(s)
    return out


def _is_table_sentence(s: str) -> bool:
    """A 'sentence' made mostly of numbers (e.g. 'Complete LIWC 0.60 0.62 0.57 Readability 0.61 ...')."""
    numbers = len(re.findall(r"(?<![A-Za-z\d.])\d+(?:\.\d+)?", s))
    return numbers >= 5 and numbers / max(len(s.split()), 1) >= 0.2


def _used_chunks(evidence: list, summary: str) -> list:
    """The chunks that really contain the copied sentences, so the citation points at the right pages."""
    used = []
    for s in _SENT_SPLIT.split(summary):
        key = re.sub(r"\s+", " ", s).strip()[:50]
        if len(key) < 20:
            continue
        for e in evidence:
            if key in re.sub(r"\s+", " ", e["text"]) and e not in used:
                used.append(e)
                break
    return used


_METRIC_WORD = re.compile(r"\b(?:accuracy|precision|recall|f1|f-measure|auc)\b", re.I)


def _has_metric_value(text: str) -> bool:
    """'Accuracy: 0.55' / 'F1 of 71%': a measured score, which belongs in the Results row only."""
    return bool(_METRIC_WORD.search(text) and re.search(r"(?<![A-Za-z\d.])(?:\d{1,3}(?:\.\d+)?\s?%|\d?\.\d+)", text))


# "4.1 Datasets Online news can be ..." : a section heading glued to the first sentence
_LEAD_HEADING = re.compile(
    r"^(?:\d+(?:\.\d+)*\s+)?(?:Datasets?|Data collection|Methodology|Methods?|Experiments?|Experimental setup|Evaluation|Results|Discussion)\s+(?=[A-Z][a-z])")
_DATASET_TOKEN = re.compile(r"\b(?:[A-Z]{3,}[A-Za-z0-9]*|[A-Z][a-z]+[A-Z][A-Za-z0-9]*)\b")   # CREDBANK, FakeNewsNet, PolitiFact
_OWN_METHOD = re.compile(r"\bwe (?:use|used|train|trained|apply|applied|employ|employed|implement|implemented|build|built|"
                         r"extract|extracted|compute|computed|propose|proposed)\b", re.I)


def _tidy_cell(text: str, limit: int = 450) -> str:
    """Last step for EVERY cell (model-written or copied): no leftover heading, never cut in the middle of a word."""
    text = _LEAD_HEADING.sub("", re.sub(r"\s+", " ", text or "").strip())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    ends = [m.end() for m in re.finditer(r"[.!?](?=\s|$)", cut)]
    if ends and ends[-1] >= limit * 0.4:
        return cut[:ends[-1]].strip()                          # back to the last full sentence
    return cut.rsplit(" ", 1)[0].rstrip(",;:") + "…"


def _extractive_summary(dimension: str, evidence: list) -> str:
    """Pick the 1-2 sentences that best match the dimension's keywords."""
    keywords = DIMENSIONS[dimension]["keywords"]
    scored = []
    for e in evidence:
        clean = _HEADING_START.sub("", re.sub(r"\s+", " ", e["text"]).strip())   # drop a leading "CONCLUSION"
        for s in _sentences(clean):
            s = _LEAD_HEADING.sub("", s)
            if len(s.split()) < 6 or _TABLE_FRAGMENT.search(s) or _is_table_sentence(s):   # skip table pieces
                continue
            low = s.lower()
            if dimension in ("Methodology", "Dataset") and _has_metric_value(s):
                continue                                              # a score belongs to Results, not here
            if dimension == "Results" and not any(w in low for w in _RESULT_WORDS_ANY):
                continue                                              # a result must talk about a metric
            score = sum(1 for k in keywords if k in low)
            if dimension == "Methodology":
                if re.search(r"\b(?:we|our)\b", low):
                    score += 2                                        # the authors' own method first
                if _OWN_METHOD.search(s):
                    score += 2                                        # "We use a linear SVM classifier ..."
                if re.match(r"we also\b|also\b|additionally\b", low) or "to test this idea" in low:
                    score -= 2                                        # a side experiment, not the main method
            if dimension == "Dataset" and _DATASET_TOKEN.search(s):
                score += 2                                            # a sentence that names a dataset
            scored.append((score, s.strip()))
    if not scored:
        return "Not stated"
    scored.sort(key=lambda x: x[0], reverse=True)
    return _join_capped([s for _, s in scored[:2]], 450)


# Limitations are copied from the paper's own sentences. A small model tends to summarise
# the conclusion instead, and an extracted sentence can be checked word for word.
_LIMIT_CUES = [
    "limitation", "future work", "future research", "future direction", "in the future",
    "we plan", "plan to", "future development", "will be crucial", "still needs to be", "still need to be", "open issue", "open problem", "open question", "not yet", "remains to be",
    "remain open", "remains open", "unsolved", "beyond the scope", "left for future",
    "challenging issues", "remain challenging", "remains a challenge", "remains challenging", "have yet to",
    "has yet to", "future studies", "future investigation", "could be extended", "can be extended",
]
# Inside a section called "Open issues" / "Future work" / "Limitations", plainer wording also counts
_LIMIT_SECTION = re.compile(r"open|future|limitation|discussion|conclusion|challenge", re.I)
# "we will extend X" is a plan; "we will discuss / describe / use ..." only walks the reader through the paper
_WILL_PLAN = re.compile(r"\bwe will (?!(?:also |then |first |next |now )?(?:discuss|describe|present|show|see|use|introduce|explain|"
                        r"provide|give|report|review|cover|define|detail|refer|denote|call|elaborate|focus|begin|start|assume|"
                        r"write|let|follow|derive|summari[sz]e|illustrate|highlight|take|cite|mention|note)\b)", re.I)
# The word "limitation" alone is weak: it also appears in background ("ChatGPT ... limitations of pretraining data")
# and in findings ("we found that LLMs have limitations"). It counts only for the authors' own work.
_OWN_WORK = re.compile(r"\b(?:we|our|this (?:paper|work|study|article|survey|benchmark))\b", re.I)
_LIMIT_NAMED_SECTION = re.compile(r"limitation|future|open (?:issue|problem|question)|challenge", re.I)
_FINDING = re.compile(r"\b(?:we|(?:the |our )?(?:experimental |empirical )?(?:results?|experiments?|analysis|evaluation|findings?))\b"
                      r"[^.]{0,60}\b(?:found|find|finds|identified|observed|observe|suggests?|shows?|showed|reveals?|revealed|"
                      r"indicates?|demonstrates?|demonstrated)\b", re.I)
_LIMIT_CUES_SECTION = [
    "no existing", "there is no", "there are no", "rather limited", "very limited", "is limited", "but limited",
    "not been fully", "have not been", "has not been", "lack", "is needed", "are needed", "worth", "promising direction",
    "interesting problem", "interesting investigation", "is important to", "not yet",
]
_CITE_NAME = re.compile(r"\bet al\b|\([A-Z][A-Za-z]+(?: and [A-Z][A-Za-z]+)?,? \d{4}\)")
_HEADING_START = re.compile(
    r"^\W*(?:\d+(?:\.\d+)*\s+)?(?:conclusions?\s+and\s+future\s+work|future\s+work|conclusions?|abstract|introduction)[\s—–:.\-]+(?=[A-Z])", re.I)


def _cue_in(cue: str, low: str) -> bool:
    """The cue must start at a word start: "lack" must not match inside "black"."""
    return re.search(r"\b" + re.escape(cue), low) is not None


# A survey describing itself ("This paper sorts out ... It also looks forward to ...", "Chapter 7 will introduce ...") is an outline
_SELF_DESCRIPTION = re.compile(r"\b(?:this|the) (?:paper|article|survey)\b[^.]{0,60}\b(?:sorts? out|summari[sz]es|aims? to|looks? forward|outlines?|provides?|presents?)\b"
                               r"|\blooks? forward to\b|\bchapters? \d", re.I)


def limitation_candidates(evidence: list) -> list:
    """Every sentence in the evidence where the authors state a limitation, open issue or plan.
    Returns dicts {sentence, page, section, hits}, best first. Used by the Limitations row and by Gap Detection."""
    scored = []
    order = 0
    for e in evidence:
        text = _HEADING_START.sub("", re.sub(r"\s+", " ", e["text"]).strip())   # drop "Conclusion and Future Work"
        section_name = str(e.get("section", ""))
        in_section = bool(_LIMIT_SECTION.search(section_name))
        prev = ""
        for s in _sentences(text):
            before, prev = prev, _CAPS_HEADING.sub("", s.strip())
            s = _CAPS_HEADING.sub("", s.strip())
            order += 1
            if len(s.split()) < 6 or _ROADMAP.search(s) or _SELF_DESCRIPTION.search(s):   # "In Section 6 we discuss ..." is an outline
                continue
            if in_section:
                # In an "Open issues" section the authors describe the field's gaps; numbered citations are fine there
                if _CITE_NAME.search(s) and not _FIRST_PERSON.search(s):
                    continue
            elif _CITE.search(s) and not _FIRST_PERSON.search(s):  # a limitation of someone else's work
                continue
            low = s.lower()
            if re.search(r"\b(?:we|this (?:paper|article|survey))\s+(?:also\s+)?(?:further\s+)?(?:discussed|reviewed|presented|introduced|explored|summari[sz]ed)\b", low):
                continue                                          # "We also discussed ... future directions": a recap
            if len(s.split()) <= 14 and re.match(r"(?:there (?:are|is)|here are)\b", low):
                continue                                          # "There are several options for future work." (lead-in)
            cues = [c for c in _LIMIT_CUES if _cue_in(c, low)]
            section_cues = [c for c in _LIMIT_CUES_SECTION if _cue_in(c, low)] if in_section else []
            hits = len(cues) + len(section_cues)
            planned = bool(_WILL_PLAN.search(low))
            if planned:
                hits += 1
            if hits and not planned and not section_cues and set(cues) <= {"limitation"}:
                # only the bare word "limitation": keep it if the authors speak about their own work and it is not a finding
                if not (_OWN_WORK.search(s) or _LIMIT_NAMED_SECTION.search(section_name)) or _FINDING.search(s):
                    continue
            if hits and (planned or re.search(r"\bwe (?:plan|intend)\b|\bplan to\b", low)):
                hits += 0.5                                       # a concrete plan beats a general remark
            if hits and len(s.split()) <= 10 and re.search(r"\b(?:this|these|that|it|them)\b", low) and len(before.split()) >= 6:
                s = before + " " + s                              # "We hope to address this in future work." needs the sentence before it
            if hits:
                scored.append({"hits": hits, "order": order, "sentence": s,
                               "page": int(e.get("page") or 0), "section": e.get("section", ""), "chunk": e})
    seen, out = set(), []
    for c in sorted(scored, key=lambda c: (-c["hits"], c["order"])):
        key = re.sub(r"[^a-z0-9]", "", c["sentence"].lower())[:80]
        if key not in seen:                                       # chunks overlap, so the same sentence can appear twice
            seen.add(key)
            out.append(c)
    return out


def _limitation_sentences(evidence: list) -> str:
    best = limitation_candidates(evidence)[:2]
    if not best:
        return "Not stated"
    best.sort(key=lambda c: c["order"])                             # back into reading order
    return _join_capped([c["sentence"] for c in best], 450)


# Novelty is also copied from the paper: the sentences where the authors say what is new.
_NOVELTY_STRONG = ["novel", "to the best of our knowledge", "for the first time", "we are the first", "the first to",
                   "main contribution", "our contribution", "key contribution", "contributions of this",
                   "new approach", "new method", "new dataset", "unlike", "in contrast to", "differs from"]
_NOVELTY_CLAIM = ["we propose", "we introduce", "we present", "we develop", "we construct", "we provide", "we design",
                  "we build", "this paper proposes", "this paper presents", "this paper introduces",
                  "in this survey", "in this article, we", "in this paper, we",
                  "we analyze", "we analyse", "we investigate", "we empirically", "introduces new", "provides a better understanding"]


# "In Section 2, we present ..." / "The rest of this paper is organized as follows" describe the outline, not the novelty
_ROADMAP = re.compile(
    r"\bin (?:section|sec\.)\s*\d|\bin the (?:previous|next|following|last) (?:section|subsection)|\bin this (?:sub)?section"
    r"|rest of (?:this|the) (?:paper|article|survey)|(?:is|are) organi[sz]ed as follows|\bsection \d+ (?:describes|presents|reviews|concludes)",
    re.I)


def _novelty_sentences(evidence: list) -> str:
    scored, seen, order = [], set(), 0
    for e in evidence:
        text = _HEADING_START.sub("", re.sub(r"\s+", " ", e["text"]).strip())
        for s in _sentences(text):
            s = _CAPS_HEADING.sub("", s.strip())
            order += 1
            n = len(s.split())
            if n < 8 or n > 55 or _ROADMAP.search(s):
                continue
            low = s.lower()
            if re.search(r"\(see (?:table|figure|fig)", low):       # detail lines, not the contribution
                continue
            # Must be the authors talking about their own work ("we", "our", "this paper") or a "contribution" statement
            if not (_FIRST_PERSON.search(s) or "contribution" in low):
                continue
            if _CITE.search(s) and not _FIRST_PERSON.search(s):      # about someone else's work
                continue
            weight = 2 * sum(1 for c in _NOVELTY_STRONG if c in low) + sum(1 for c in _NOVELTY_CLAIM if c in low)
            if not weight:
                continue
            # Contributions are stated in the abstract / start of the introduction and in the conclusion
            if int(e.get("page") or 99) <= 2:
                weight += 2
            if e.get("section") in ("abstract", "introduction", "conclusion"):
                weight += 1
            key = re.sub(r"[^a-z0-9]", "", low)[:80]                  # chunks overlap, so skip repeats
            if key in seen:
                continue
            seen.add(key)
            scored.append((-weight, order, int(e["page"]), s))
    if not scored:
        return "Not stated"
    ranked = sorted(scored)
    top = -ranked[0][0]
    best = [x for x in ranked[:3] if -x[0] >= 0.5 * top]               # drop weak detail sentences
    best.sort(key=lambda x: (x[2], x[1]))                              # reading order: page, then position
    return _join_capped([s for _, _, _, s in best], 600)


def _join_capped(sentences: list, limit: int) -> str:
    """Join whole sentences up to a length limit, so a sentence is never cut in half."""
    out = ""
    for s in sentences:
        if s and s in out:                                # the same sentence can arrive from a chunk and from the sentence reader
            continue
        if out and len(out) + 1 + len(s) > limit:
            break
        out = (out + " " + s).strip()
    if len(out) > limit:                                  # one very long sentence: cut at a word, not in the middle of one
        out = out[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return out


_RESULT_WORDS_ANY = ("accuracy", "f1", "precision", "recall", "outperform", "perform better", "error rate", "auc")
# A real measured value: 66.7%  5.65%  0.73  .497   (not "F1", not "Table 4")
_VALUE = re.compile(r"(?<![A-Za-z\d.])(?:\d{1,3}(?:\.\d+)?\s?%|\d?\.\d+)")
_NUMBER = re.compile(r"(?<![A-Za-z\d.])\d+(?:\.\d+)?")


def _prose_numbers(evidence: list) -> tuple:
    """
    Numbers that are written in ordinary sentences next to a metric word.
    Sentences stuffed with numbers are table fragments, whose columns a small model mixes up.
    Returns (set of numbers, True if at least one real measured value was found).
    """
    numbers, found_value = set(), False
    for e in evidence:
        for s in _SENT_SPLIT.split(re.sub(r"\s+", " ", e["text"])):
            low = s.lower()
            if len(_NUMBER.findall(s)) > 4 or not any(w in low for w in _RESULT_WORDS_ANY):
                continue
            numbers.update(_NUMBER.findall(s))
            if _VALUE.search(s):
                found_value = True
    return numbers, found_value


def _has_result_evidence(evidence: list) -> bool:
    """Results need a sentence with a measured value AND a metric word. A caption or a definition is not a result."""
    return _prose_numbers(evidence)[1]


_GENERIC_WORDS = {"paper", "papers", "using", "which", "their", "these", "those", "provides", "includes",
                  "including", "contains", "proposes", "describes", "presents", "uses", "used", "based", "approach",
                  "achieves", "achieved", "achieve", "shows", "shown", "reaches", "reached", "reports", "reported",
                  "results", "result", "method", "methods", "compared", "provide", "provided", "while", "about",
                  "around", "between", "several", "overall", "terms"}
# Proper names: FakeNewsNet, PolitiFact, LIWC, NLP, F1 ... (internal capital, 2+ capitals, or letter+digit)
_NAME = re.compile(r"\b(?:[A-Z][a-z]+[A-Z][A-Za-z0-9]*|[A-Z]{2,}[A-Za-z0-9]*|[A-Za-z]+\d[A-Za-z0-9]*)\b")


def _grounded(summary: str, evidence: list, dimension: str = "") -> bool:
    """True when the summary's numbers, names and most content words all come from the evidence."""
    ev = " ".join(e["text"] for e in evidence).lower()
    numbers_in_summary = re.findall(r"\d+(?:\.\d+)?", summary)
    if dimension == "Results":
        allowed = _prose_numbers(evidence)[0]          # table numbers are not trusted
        if any(n not in allowed for n in numbers_in_summary):
            return False
    elif any(n not in ev for n in numbers_in_summary):
        return False
    if any(name.lower() not in ev for name in _NAME.findall(summary)):
        return False                                    # a name that is not in the evidence was invented
    words = [w for w in re.findall(r"[a-z]{5,}", summary.lower()) if w not in _GENERIC_WORDS]
    if not words:
        return True
    return sum(1 for w in words if w[:5] in ev) / len(words) >= 0.6


# --------------------------------------------------------------------------- #
# Reading the WHOLE paper sentence by sentence (Results, Dataset and Methodology)
# A search returns only a few chunks and can miss the key sentence, so these rows also look at every sentence of the paper.
# --------------------------------------------------------------------------- #
_SURVEY_TITLE = re.compile(r"\b(?:survey|review|overview|systematic|literature|state of the art|taxonomy|tutorial)\b", re.I)
_SURVEY_TEXT = re.compile(r"\b(?:this|the present|our) (?:survey|review|article reviews|paper (?:reviews|surveys))\b|\bwe (?:survey|review)\b|"
                          r"\bliterature (?:review|survey)\b|\bsystematic (?:review|literature)\b", re.I)


_HEAD_FUNC = {"a", "an", "the", "of", "and", "in", "for", "on", "to", "with", "via", "by", "at", "from", "or"}


def _strip_numbered_heading(s: str) -> str:
    """'3.2 Building a Web Dataset We collected a second dataset ...' -> 'We collected a second dataset ...'"""
    m = re.match(r"^\d+(?:\.\d+)*\s+(.*)$", s)
    if not m:
        return s
    toks = m.group(1).split()
    j = 0
    while j < len(toks) and (toks[j][:1].isupper() or toks[j].lower() in _HEAD_FUNC or re.fullmatch(r"\d+(?:\.\d+)*", toks[j])):
        j += 1
    if j == 0 or j >= len(toks):
        return s
    start = j - 1 if toks[j - 1][:1].isupper() else j          # the last capital word starts the sentence ("We collected ...")
    if j >= 2 and re.fullmatch(r"\d+", toks[j - 1]) and toks[j - 2].lower() in ("table", "figure", "fig."):
        start = j - 2
    return " ".join(toks[start:])


def _paper_sentences(project_id: int, paper_id: int) -> list:
    """All complete sentences of the paper (no related work, no references), each with page and section."""
    try:
        got = get_or_create_collection(project_id).get(where={"paper_id": int(paper_id)}, include=["documents", "metadatas"])
    except Exception as exc:
        logger.warning("Could not read paper %s: %s", paper_id, exc)
        return []
    docs, metas = got.get("documents") or [], got.get("metadatas") or []
    order_ix = sorted(range(len(docs)), key=lambda i: (int(metas[i].get("page", 0)), int(metas[i].get("chunk_index", 0))))
    ref_pages = [int(metas[i].get("page", 0)) for i in order_ix if looks_like_references(docs[i])]
    ref_page = min(ref_pages) if ref_pages else None                  # what comes after the references is an appendix
    keep = [i for i in order_ix if metas[i].get("category") not in ("Related Work", "Citation")]
    items = _parse({"documents": [[docs[i] for i in keep]], "metadatas": [[metas[i] for i in keep]]})
    out, seen, order = [], set(), 0
    for e in items:
        text = _HEADING_START.sub("", re.sub(r"\s+", " ", e["text"]).strip())
        for sent in _sentences(text):
            sent = _strip_numbered_heading(_LEAD_HEADING.sub("", _CAPS_HEADING.sub("", sent.strip())))
            n = len(sent.split())
            if n < 7 or n > 70 or _TABLE_FRAGMENT.search(sent) or _is_table_sentence(sent) or _ROADMAP.search(sent):
                continue
            key = re.sub(r"[^a-z0-9]", "", sent.lower())
            if any(key in k or k in key for k in seen):                 # chunks overlap, so the same sentence (or half of it) can come twice
                continue
            seen.add(key)
            order += 1
            page = int(e.get("page") or 0)
            out.append({"sentence": sent, "page": page, "section": str(e.get("section", "")), "order": order,
                        "appendix": bool(ref_page and page >= ref_page)})
    return out


def _is_survey(title: str, sents: list) -> bool:
    """A survey or review reports no experiments and builds no dataset of its own."""
    early = [x["sentence"] for x in sents if x["page"] <= 2]
    return bool(_SURVEY_TITLE.search(title or "") and any(_SURVEY_TEXT.search(t) for t in early)) \
        or sum(1 for t in early if _SURVEY_TEXT.search(t)) >= 2


def _usable(x: dict) -> bool:
    """A sentence that speaks about this paper, not about other people's work or future plans."""
    s = x["sentence"]
    if _FUTURE.search(s) or _PRIOR_WORK.search(s) or _FORMULA.search(s) or s.endswith("?"):
        return False
    return not (_CITE.search(s) and not _FIRST_PERSON.search(s))


_FIND_VERB = re.compile(
    r"\b(?:outperform\w*|improv\w+|achiev\w+|obtain\w*|reach(?:es|ed)?|surpass\w*|exceed\w*|state-of-the-art|degrad\w+|struggl\w+|"
    r"better than|higher|lower|drops?|dropped|reduc\w+|gains?|best|significant\w*|substantial\w*|state of the art|"
    r"we (?:find|found|observe[d]?|show|showed|demonstrate[d]?|report)|(?:results?|experiments?|analysis|evaluation) "
    r"(?:show|suggest|indicate|reveal|demonstrate)\w*)\b", re.I)
_METRIC_ANY = re.compile(r"\b(?:accura(?:cy|cies)|f1|f-measure|precision|recall|exact match|em|top-\d+|bleu|rouge|auc|error rate|perplexity|"
                         r"performance|score|win rate|results?)\b", re.I)
_BUILD_RESULT = re.compile(r"\b(?:we (?:conduct|use|used|train|trained|evaluate|evaluated|collect|collected|describe)|are shown|is shown)\b", re.I)


def _result_items(sents: list, survey: bool) -> list:
    """The paper's own findings, copied word for word (abstract, results and conclusion sentences)."""
    if survey:
        return []
    scored = []
    for x in sents:
        s = x["sentence"]
        if not _usable(x) or not _FIND_VERB.search(s):
            continue
        if not _METRIC_ANY.search(s) and not re.search(r"\b(?:outperform\w*|state[- ]of[- ]the[- ]art|surpass\w*|beats?)\b", s, re.I):
            continue                                    # a result talks about a metric or a comparison
        if not _VALUE.search(s) and not re.search(r"\b(?:than|outperform\w*|state-of-the-art|degrad\w+|struggl\w+|highest|lowest|best)\b", s, re.I):
            continue                                    # a finding is a comparison or a measured value
        sec_l = x["section"].lower()
        own = bool(_FIRST_PERSON.search(s) or re.search(r"\b(?:our|this (?:paper|work|study))\b|\b(?:the|these) (?:results?|experiments?|analysis|evaluation|findings?)\b", s, re.I))
        if not own and not re.search(r"result|experiment|evaluation|analysis", sec_l):
            continue                                    # "Large language models have been shown to ..." is background
        score = 2.0 * bool(_VALUE.search(s)) + 1.0 * bool(_METRIC_ANY.search(s))
        score += min(len(_FIND_VERB.findall(s)), 2) * 1.0
        sec = x["section"].lower()
        if sec == "abstract":
            score += 1.5
        elif re.search(r"result|experiment|discussion|conclusion|evaluation|analysis", sec):
            score += 1.0
        elif sec == "introduction":
            score += 0.5
        if _FIRST_PERSON.search(s) or re.search(r"\b(?:our|the) (?:results?|experiments?|analysis)\b", s, re.I):
            score += 1.0
        if x["appendix"]:
            score -= 2.0
        if _BUILD_RESULT.search(s) and not _VALUE.search(s):
            score -= 1.0                                # "We train with mixed precision" is setup, not a finding
        scored.append((score, x))
    scored = [t for t in scored if t[0] >= 4.0]
    scored.sort(key=lambda t: (-t[0], t[1]["order"]))
    best = scored[:2]
    best.sort(key=lambda t: t[1]["order"])
    return [t[1] for t in best]


_DATA_WORD = re.compile(r"\b(?:data ?sets?|corpus|corpora|benchmarks?|collections?|questions|queries|articles|annotated|labell?ed|"
                        r"samples|instances|examples|documents|passages|training (?:set|data)|test set|splits?)\b", re.I)
_DATA_VERB = re.compile(r"\b(?:we|our)\b[^.]{0,40}\b(?:construct\w*|build\w*|built|creat\w+|collect\w*|use[ds]?|introduce[ds]?|releas\w+|"
                        r"crawl\w*|gather\w*|curat\w+|annotat\w+|evaluat\w+ on|experiment\w* on|train\w* on)\b", re.I)
_DATA_COUNT = re.compile(r"\b\d[\d,]*\s+(?:base |total |labeled |labelled |news |question |training |test )?(?:questions|articles|samples|"
                         r"instances|examples|documents|passages|queries|pairs|claims|posts|tweets|images|annotators)\b", re.I)


def _dataset_sentences(sents: list, survey: bool, limit: int = 4) -> list:
    """Sentences that say which data the paper uses or builds. A survey has none of its own."""
    scored = []
    for x in sents:
        s = x["sentence"]
        if not _usable(x) or not _DATA_WORD.search(s) or _has_metric_value(s):
            continue
        score = 0.0
        score += 2.0 * bool(_DATA_VERB.search(s))
        score += 1.5 * bool(_DATA_COUNT.search(s))
        score += 1.0 * min(len(_DATASET_TOKEN.findall(s)), 2)
        score += 1.0 * bool(re.search(r"\bdata ?sets?\b|\bcorpus\b|\bbenchmark\b", s, re.I))
        if re.search(r"dataset|data|experiment|setup|setting|evaluation|benchmark", x["section"], re.I):
            score += 1.0
        if x["appendix"]:
            score -= 1.0
        if re.search(r"\b(?:lack|lacks|no existing|limited|not available)\b", s, re.I):
            score -= 2.0                               # a gap in the field is not the paper's own data
        if re.search(r"\b(?:batch size|epochs?|learning rate|optimi[sz]er|gpus?|hyper-?parameters?|dropout|warm-?up|weight decay)\b", s, re.I):
            score -= 3.0                               # training settings, not the data itself
        scored.append((score, x))
    if survey:                                          # a survey lists datasets: keep only sentences that NAME one
        scored = [t for t in scored if _DATASET_TOKEN.search(t[1]["sentence"])
                  and re.search(r"\b(?:data ?sets?|corpus|corpora|benchmarks?)\b", t[1]["sentence"], re.I)
                  and not re.search(r"\bthis (?:section|chapter|paper|survey)\b", t[1]["sentence"], re.I)]
    scored = [t for t in scored if t[0] >= (2.0 if survey else 3.0)]
    scored.sort(key=lambda t: (-t[0], t[1]["order"]))
    return [t[1] for t in scored[:limit]]


_METHOD_VERB = re.compile(r"\b(?:we|this (?:paper|article|work|study|survey)|our (?:work|study|approach|method|model))\b[^.]{0,50}\b"
                          r"(?:propos\w+|present\w*|introduc\w+|develop\w*|build\w*|built|construct\w*|design\w*|analy[sz]\w+|stud(?:y|ies|ied)|"
                          r"investigat\w+|examin\w+|evaluat\w+|conduct\w*|survey\w*|review\w*|categori[sz]\w+|organi[sz]\w+|"
                          r"encompass\w*|cover\w*|train\w*|fine-?tun\w+|us(?:e|es|ed|ing)|apply|applied|employ\w*|implement\w*)\b", re.I)
_METHOD_FINDING = re.compile(r"\b(?:degrad\w+|struggl\w+|better than|outperform\w*|achiev\w+|higher|lower|suffer\w*|"
                             r"we (?:find|found|observe[d]?)|results? (?:show|suggest|indicate))\b", re.I)


def _method_sentences(sents: list, survey: bool, limit: int = 4) -> list:
    """Sentences where the authors say what THEY do or build: the first pages and the method section."""
    scored = []
    for x in sents:
        s = x["sentence"]
        if not _usable(x) or not _METHOD_VERB.search(s) or _has_metric_value(s):
            continue
        if _METHOD_FINDING.search(s):
            continue                                    # a finding, not the method
        score = 2.0
        sec = x["section"].lower()
        if sec in ("abstract", "introduction") or x["page"] <= 2:
            score += 1.5
        if re.search(r"method|approach|model|framework|design|setup|setting|architecture|survey|review", sec):
            score += 1.0
        if survey and re.search(r"\b(?:survey|review|encompass\w*|categori[sz]\w+|organi[sz]\w+|paradigms?|taxonomy)\b", s, re.I):
            score += 1.5
        if x["appendix"]:
            score -= 2.0
        scored.append((score, x))
    scored = [t for t in scored if t[0] >= 3.0]
    scored.sort(key=lambda t: (-t[0], t[1]["order"]))
    return [t[1] for t in scored[:limit]]


def _as_evidence(sents: list) -> list:
    """Whole sentences, in the same shape as a chunk, so the model and the page citation can use them."""
    return [{"distance": 0.1, "page": x["page"], "section": x["section"] or "unknown", "category": "Sentence",
             "text": x["sentence"], "_raw": x["sentence"]} for x in sents]


def _citation(paper_id: int, evidence: list) -> str:
    pages = sorted({int(e["page"]) for e in evidence})
    return f"[Paper {paper_id}, Page {', '.join(str(p) for p in pages)}]" if pages else ""


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def analyze_paper(project_id: int, paper_id: int, title: str, use_llm: bool = True) -> dict:
    """Analyze one paper and save the result. Runs one dimension at a time (RAM friendly)."""
    llm_ok = use_llm
    dimensions = {}
    sents = _paper_sentences(project_id, paper_id)
    survey = _is_survey(title, sents)

    for dim in DIMENSIONS:
        evidence, tagged = _gather_evidence(project_id, paper_id, dim, top_k=DIMENSIONS[dim].get("top_k", 3))
        dataset_items = _dataset_sentences(sents, survey) if dim == "Dataset" else []
        if dim == "Dataset":
            evidence = _as_evidence(dataset_items) + evidence
        elif dim == "Methodology":
            evidence = _as_evidence(_method_sentences(sents, survey)) + evidence
        result_items = _result_items(sents, survey) if dim == "Results" else []
        if dim == "Results" and result_items:
            evidence = _as_evidence(result_items)

        if not evidence:
            dimensions[dim] = {
                "summary": "No relevant text found in this paper.",
                "method": "none", "from_tagged_section": False,
                "citation": "", "evidence": [],
            }
            continue

        summary, method = None, "extractive"
        if dim == "Novelty":
            summary = _novelty_sentences(evidence)              # no model: the authors' own claims
        elif dim == "Limitations":
            summary = _limitation_sentences(evidence)           # no model: copied from the paper
        elif dim == "Results":
            summary = _join_capped([x["sentence"] for x in result_items], 450) if result_items else "Not stated"   # copied, never written by the model
        elif dim == "Dataset" and survey and not dataset_items:
            summary = "Not stated"                              # a survey that names no dataset of its own
        elif llm_ok:
            try:
                answer = _llm_summary(title, dim, evidence)
                leaks = dim in ("Methodology", "Dataset") and _has_metric_value(answer)   # a score in a method cell
                if answer == "Not stated" or (_grounded(answer, evidence, dim) and not leaks):
                    summary, method = answer, "llm"
                else:
                    logger.info("Ungrounded %s summary for paper %s; using extracted sentences.", dim, paper_id)
            except Exception as exc:
                logger.warning("LLM summary failed (%s). Using the no-LLM fallback.", exc)
                llm_ok = False  # do not wait for the model again for the rest of this paper
        if summary is None:
            summary = _extractive_summary(dim, evidence)
        if summary.strip() not in ("Not stated", ""):
            summary = _tidy_cell(summary)

        found = summary.strip() not in ("Not stated", "")
        if dim in ("Novelty", "Limitations"):
            # Cite only the chunks that contain the copied sentences (or a few, if nothing was found)
            evidence = _used_chunks(evidence, summary) or evidence[:3]
        elif method == "extractive" and found:
            evidence = _used_chunks(evidence, summary) or evidence

        dimensions[dim] = {
            "summary": summary,
            "method": method,
            "from_tagged_section": tagged,
            "citation": _citation(paper_id, evidence) if found else "",   # no page for "Not found"
            "evidence": [
                {"page": int(e["page"]), "section": e["section"],
                 "category": e["category"], "text": e["text"][:700]}   # the same 700 characters the model saw
                for e in evidence
            ],
        }

    result = {
        "paper_id": paper_id,
        "title": title,
        "code_version": CODE_VERSION,
        "analyzed_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "model": OLLAMA_MODEL if use_llm else None,
        "dimensions": dimensions,
    }
    _save(paper_id, result)
    return result


def debug_paper(project_id: int, paper_id: int, dimension: str) -> dict:
    """Read-only look at what the stored index holds for a paper and what a dimension would read."""
    if dimension not in DIMENSIONS:
        return {"error": f"dimension must be one of {list(DIMENSIONS)}"}
    got = get_or_create_collection(project_id).get(where={"paper_id": int(paper_id)}, include=["documents", "metadatas"])
    docs, metas = got.get("documents") or [], got.get("metadatas") or []
    order = sorted(range(len(docs)), key=lambda i: (metas[i].get("page", 1), metas[i].get("chunk_index", 0)))
    evidence, _ = _gather_evidence(project_id, paper_id, dimension, top_k=DIMENSIONS[dimension].get("top_k", 3))
    return {
        "code_version": CODE_VERSION,
        "dimension": dimension,
        "stored_chunks": len(docs),
        "stored_pages": sorted({int(m.get("page", 0)) for m in metas}),
        "chunks_by_category": {c: sum(1 for m in metas if m.get("category") == c) for c in sorted({m.get("category") for m in metas}, key=str)},
        "limitation_like_chunks": [
            {"page": metas[i].get("page"), "section": metas[i].get("section"), "category": metas[i].get("category"),
             "starts": re.sub(r"\s+", " ", docs[i])[:70]}
            for i in order
            if _LIMIT_SECTION.search(str(metas[i].get("section", ""))) or _HEADING_TEXT.search(docs[i])
        ],
        "chunks_read_for_this_dimension": [
            {"page": e["page"], "section": e["section"], "category": e["category"],
             "starts": re.sub(r"\s+", " ", e["text"])[:70]}
            for e in evidence
        ],
    }


def _path(paper_id: int) -> str:
    return os.path.join(ANALYSIS_DIR, f"paper_{int(paper_id)}.json")


def _save(paper_id: int, result: dict) -> None:
    # Write to a temp file first so a crash never leaves a half-written file
    fd, tmp = tempfile.mkstemp(dir=ANALYSIS_DIR, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _path(paper_id))


def load_cached(paper_id: int):
    try:
        with open(_path(paper_id), "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    # A result saved by an older version of the analysis is treated as "not analyzed yet"
    return data if data.get("code_version") == CODE_VERSION else None


def delete_cached(paper_id: int) -> None:
    try:
        os.remove(_path(paper_id))
    except FileNotFoundError:
        pass