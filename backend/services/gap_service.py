"""
Step 3: Gap Detection.

A research gap here is something the AUTHORS THEMSELVES say is still open: a stated limitation,
an open issue, or planned future work. Every gap is one sentence copied word for word from a paper,
with its page number, so it can always be traced back (and, in Step 4, checked against the other papers).

No model writes the gap itself, so a gap can never be invented. A small model is used only for a short
title, and the title is rejected if it uses words that are not in the sentence.
"""
import os
import re
import json
import logging
import tempfile
from datetime import datetime

import requests

from backend.services import evidence_service as ev

logger = logging.getLogger(__name__)

GAP_CODE_VERSION = "3"
GAPS_DIR = os.path.join("data", "gaps")
os.makedirs(GAPS_DIR, exist_ok=True)

MAX_PER_PAPER = 3
MAX_TOTAL = 20

# What the authors say they DID is not a gap
_RECAP = re.compile(
    r"\b(?:we|(?:this|the) (?:paper|article|survey))\s+(?:also\s+|further\s+)*(?:will\s+)?"
    r"(?:discuss|discussed|review|reviewed|present|presented|introduce|introduced|explore|explored|"
    r"summari[sz]e[ds]?|provide|provided|describe|described|outlines?|outlined)\b", re.I)
# A limitation the paper says it SOLVES is not an open gap
_SOLVED = re.compile(r"\b(?:we|our)\b[^.]{0,60}\b(?:try|tries|aim|aims|attempt|attempts)\s+to\s+(?:address|overcome|solve|tackle)\b"
                     r"|\bwe (?:address|overcome|solve|tackle)\b", re.I)

_FUTURE_WORDS = ("we will", "we plan", "plan to", "future work", "future research", "future direction",
                 "future stud", "in the future", "could be extended", "can be extended", "left for future",
                 "promising direction", "important to explore", "worth exploring", "worth to explore", "interesting problem")
_OPEN_WORDS = ("open issue", "open problem", "open question", "remain open", "remains open", "unsolved",
               "yet to", "remains to be", "not yet", "beyond the scope")


def gap_type(sentence: str) -> str:
    low = sentence.lower()
    if any(w in low for w in _FUTURE_WORDS):
        return "Future work"
    if any(w in low for w in _OPEN_WORDS):
        return "Open issue"
    return "Limitation"


_LEAD = re.compile(r"^(?:first|second|third|finally|moreover|however|in addition|also|note that|thus|therefore|in this sense)[,\s]+", re.I)
_LEAD_VERB = re.compile(r"^(?:we|the authors)\s+(?:also\s+)?(?:demonstrated|showed|show|found|note|noted|believe|argue)\s+that\s+", re.I)
_CLAUSE = re.compile(r"[,;:]| such as | since | because | which ")


def _fallback_title(sentence: str, kind: str) -> str:
    s = _LEAD.sub("", sentence).strip()
    head, _, rest = s.partition(",")
    if rest and len(head.split()) <= 6:                  # "From a dataset perspective, ..." / "As outlined in the following, ..."
        s = rest.strip()
    s = _LEAD_VERB.sub("", s)
    first = _CLAUSE.split(s, maxsplit=1)[0]
    if len(first.split()) >= 4:
        s = first
    words = s.split()
    s = " ".join(words[:12]).rstrip(".")
    s = s[:1].upper() + s[1:]
    return s + ("…" if len(words) > 12 else "")


_DANGLING = {"us", "the", "a", "an", "of", "in", "to", "for", "with", "on", "and", "or", "by", "at", "from", "using",
             "as", "is", "are", "that", "which", "its", "their", "our", "than", "into", "over", "via", "be"}


def _llm_title(sentence: str):
    prompt = ("Write a short title (4 to 10 words) for the research gap in this sentence. "
              "Use only words from the sentence. No quotes, no full stop, no introduction.\n\n"
              f"Sentence: {sentence}\n\nTitle:")
    res = requests.post(
        ev.OLLAMA_URL,
        json={"model": ev.OLLAMA_MODEL, "prompt": prompt, "stream": False, "keep_alive": "10m",
              "options": {"temperature": 0.1, "num_predict": 30, "num_ctx": 1024}},
        timeout=min(ev.OLLAMA_TIMEOUT, 90),
    )
    res.raise_for_status()
    title = (res.json().get("response") or "").strip().split("\n")[0]
    title = re.sub(r"^(?:title\s*:\s*)", "", title, flags=re.I).strip(" \"'*-•.")
    words = title.split()
    if not (3 <= len(words) <= 12):
        return None
    low = sentence.lower()
    # "there is no existing benchmark dataset ..." must not become the title "Existing benchmark dataset ..."
    if re.search(r"\b(?:there (?:is|are) no|no existing|no [a-z]+ (?:that|which)|lack(?:s|ing)?)\b", low) \
            and not re.search(r"\b(?:no|not|lack|lacks|lacking|without|missing|absence|absent)\b", title.lower()):
        return None
    if title.lower().split()[-1].strip(".,;:") in _DANGLING:
        return None                                  # the title was cut off in the middle of a phrase
    content = [w for w in re.findall(r"[a-z]{4,}", title.lower())]
    if content and sum(1 for w in content if w[:5] in low) / len(content) < 0.7:
        return None                                  # the model used words that are not in the sentence
    return title[:1].upper() + title[1:]


def _title(sentence: str, kind: str, use_llm: bool, state: dict) -> str:
    if use_llm and state.get("llm_ok", True):
        try:
            t = _llm_title(sentence)
            if t:
                return t
        except Exception as exc:
            logger.warning("Title model not available (%s); using plain titles.", exc)
            state["llm_ok"] = False
    return _fallback_title(sentence, kind)


def _similar(a: str, b: str) -> bool:
    wa, wb = set(re.findall(r"[a-z]{4,}", a.lower())), set(re.findall(r"[a-z]{4,}", b.lower()))
    return bool(wa and wb) and len(wa & wb) / min(len(wa), len(wb)) >= 0.6


_CAPTION = re.compile(r"(?:figure|fig\.|table)\s*\d", re.I)       # "Figure 2: Future directions and open issues ..."
MIN_SCORE = 1.5          # one weak cue alone ("has yet to ...") is not enough
_OWN = re.compile(r"\b(?:we|our|this (?:paper|work|study|article|survey|benchmark))\b", re.I)
_STRONG_SECTION = re.compile(r"limitation|future|open (?:issue|problem|question)|challenge", re.I)
_WEAK_SECTION = re.compile(r"discussion|conclusion", re.I)


def _all_text(project_id: int, paper_id: int) -> list:
    """Every chunk of the paper except related work and reference lists, cleaned the same way as the evidence text.
    Gap detection reads the whole paper, so it does not depend on what a search happens to return."""
    got = ev.get_or_create_collection(project_id).get(where={"paper_id": int(paper_id)}, include=["documents", "metadatas"])
    pairs = [(d, m) for d, m in zip(got.get("documents") or [], got.get("metadatas") or [])
             if m.get("category") not in ("Related Work", "Citation")]
    pairs.sort(key=lambda dm: (int(dm[1].get("page", 0)), int(dm[1].get("chunk_index", 0))))
    return ev._parse({"documents": [[d for d, _ in pairs]], "metadatas": [[m for _, m in pairs]]})


def _score(c: dict) -> float:
    """How clearly the sentence is a stated gap: cue words, plus where it stands and who is speaking."""
    sec = str(c.get("section", ""))
    score = float(c["hits"])
    if _STRONG_SECTION.search(sec):
        score += 1.0
    elif _WEAK_SECTION.search(sec):
        score += 0.5
    if _OWN.search(c["sentence"]):
        score += 0.5
    return score


def paper_gaps(project_id: int, paper_id: int) -> list:
    """The best gap sentences of one paper, each with its page."""
    evidence = _all_text(project_id, paper_id)
    cands = sorted(ev.limitation_candidates(evidence), key=lambda c: (-_score(c), c["order"]))
    picked = []
    for c in cands:
        s = c["sentence"]
        if _score(c) < MIN_SCORE or _CAPTION.match(s):
            continue
        if _RECAP.search(s) or _SOLVED.search(s):
            continue
        if any(_similar(s, p["sentence"]) for p in picked):
            continue
        picked.append(c)
        if len(picked) == MAX_PER_PAPER:
            break
    picked.sort(key=lambda c: (c["page"], c["order"]))
    return picked


def detect_gaps(project_id: int, papers: list, use_llm: bool = True) -> dict:
    """papers: [{"id": int, "title": str}, ...]  (indexed papers of the project)."""
    state, gaps, without = {"llm_ok": use_llm}, [], []
    for p in papers:
        found = paper_gaps(project_id, p["id"])
        if not found:
            without.append(p["id"])
        for c in found:
            kind = gap_type(c["sentence"])
            gaps.append({
                "paper_id": p["id"],
                "paper_title": p.get("title") or f"Paper {p['id']}",
                "type": kind,
                "title": _title(c["sentence"], kind, use_llm, state),
                "evidence_snippet": c["sentence"],
                "page": c["page"],
                "section": c["section"],
                "citation": f"[Paper {p['id']}, Page {c['page']}]",
                "status": "DETECTED",
            })
    gaps = gaps[:MAX_TOTAL] if len(gaps) > MAX_TOTAL else gaps
    for i, g in enumerate(gaps, 1):
        g["gap_id"] = f"GAP-{i}"
        g["description"] = (f"{g['type']} stated by the authors of \"{g['paper_title']}\" "
                            f"on page {g['page']}.")
    result = {
        "project_id": project_id,
        "code_version": GAP_CODE_VERSION,
        "detected_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "total_papers": len(papers),
        "papers_without_gaps": without,
        "gaps": gaps,
    }
    _save(project_id, result)
    return result


def _path(project_id: int) -> str:
    return os.path.join(GAPS_DIR, f"project_{int(project_id)}.json")


def _save(project_id: int, result: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=GAPS_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        os.replace(tmp, _path(project_id))
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def load_gaps(project_id: int):
    try:
        with open(_path(project_id), encoding="utf-8") as f:
            data = json.load(f)
        return data if data.get("code_version") == GAP_CODE_VERSION else None
    except (OSError, ValueError):
        return None