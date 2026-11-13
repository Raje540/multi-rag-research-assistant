"""
Step 4: Gap Validation.

For every gap found in Step 3 (a sentence from paper A) this looks in the OTHER papers for sentences about the
same topic and says what each one does to the gap:

  also open    paper B also says this is not done / still a limitation  -> supports the gap
  addresses    paper B says it built / proposed / collected something that deals with it -> challenges the gap
  related      same topic, but it does not say either

Verdict per gap (no model decides this, only visible word cues, so every verdict can be checked in the PDFs):
  CORROBORATED   another paper also reports it as open, and none claims to address it
  CHALLENGED     another paper reports doing something about it, and none reports it as open
  MIXED          both kinds of evidence exist
  STANDS         no counter-evidence found in the other papers (it is NOT proof that nobody solved it)
  NO_OTHER_PAPERS  nothing to compare with
"""
import re
import math
import logging
from datetime import datetime

from backend.services import evidence_service as ev
from backend.services import gap_service as gs

logger = logging.getLogger(__name__)

SIM_MIN = 0.30          # share of the gap's important words that the other sentence also uses
MIN_SHARED = 2          # ... and at least this many different words
SEMANTIC_TOP = 3        # a sentence in one of the 3 best chunks of the embedding search gets the larger bonus ...
SEMANTIC_BONUS = (0.20, 0.12)   # ... (top 3, then the rest of the top 8)
PER_GAP = 4             # evidence sentences shown per gap

_STOP = set("""
a about above after again all also although am an and any are as at be because been before being below between both but by can
could did do does doing down during each few for from further had has have having he her here hers him his how however i if in
into is it its itself just may me might more most must my no nor not now of off on once only or other our ours out over own
same she should so some such than that the their theirs them then there these they this those through to too under until up very
was we were what when where which while who whom why will with would you your thus per via et al
fake news social media paper papers author authors work works approach approaches method methods detection detect detecting
research study studies propose proposed present presented shown show shows used using use based number different various several
many well further first second third new
""".split())

# What another paper must say for a sentence to count as "addresses" / "also open"
_ADDRESSES = re.compile(
    r"\b(?:we|our|this (?:paper|article|work|survey))\b[^.]{0,50}?\b(?:construct|build|built|introduce|present|propose|develop|"
    r"create|collect|provide|release|publicize|design|implement|address|overcome|solve|contribute)\w*", re.I)
_FUTURE = re.compile(r"\bwe (?:will|plan|intend)\b|\bin the future\b|\bfuture (?:work|research)\b|\bplan to\b", re.I)
_ALSO_OPEN = re.compile(
    r"\bno (?:agreed|existing|standard|benchmark|publicly)\b|\bthere (?:is|are) no\b|\black(?:s|ed|ing)? (?:of)?\b|\bnot (?:yet|been)\b|"
    r"\blimitations?\b|\bremain(?:s)? (?:open|unsolved|unclear|a challenge)\b|\bunsolved\b|\bopen (?:issue|problem|question)|"
    r"\b(?:very|rather) limited\b|\b(?:is|are) limited\b|\bonly (?:cover|contain|include)s?\b|"
    r"\bthe majority of (?:them|these|existing)\b[^.]{0,40}\bonly\b|\bfuture (?:work|research|direction)", re.I)
_LACK = re.compile(r"\black(?:s|ed|ing)? of\b|\bno (?:agreed|existing|standard|benchmark|publicly)\b|\bthere (?:is|are) no\b|"
                   r"\bnot (?:yet|been)\b|\bonly (?:cover|contain|include)s?\b|\b(?:very|rather) limited\b", re.I)


def _stem(w: str) -> str:
    w = w.lower()
    if len(w) > 5 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 6 and w.endswith("ing"):
        return w[:-3]
    if len(w) > 5 and w.endswith("ed"):
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def _terms(text: str) -> set:
    return {_stem(w) for w in re.findall(r"[A-Za-z]{3,}", text) if w.lower() not in _STOP}


def _corpus(project_id: int):
    """All chunks of the project except reference lists, plus document frequencies of every word."""
    got = ev.get_or_create_collection(project_id).get(include=["documents", "metadatas"])
    chunks = []
    for doc, meta in zip(got.get("documents") or [], got.get("metadatas") or []):
        if meta.get("category") == "Citation" or ev.looks_like_references(doc):
            continue
        chunks.append({"paper_id": int(meta.get("paper_id", 0)), "page": int(meta.get("page", 0)),
                       "section": meta.get("section", ""), "category": meta.get("category", ""),
                       "text": ev._strip_urls(ev._dehyphenate(doc)), "paper_title": meta.get("paper_title", "")})
    df = {}
    for c in chunks:
        for t in _terms(c["text"]):
            df[t] = df.get(t, 0) + 1
    return chunks, df, max(len(chunks), 1)


def _idf(term: str, df: dict, n: int) -> float:
    return math.log((n + 1) / (df.get(term, 0) + 1)) + 1.0


def _similarity(gap_terms: set, sent_terms: set, df: dict, n: int):
    shared = gap_terms & sent_terms
    if not gap_terms:
        return 0.0, shared
    total = sum(_idf(t, df, n) for t in gap_terms)
    return sum(_idf(t, df, n) for t in shared) / total, shared


# "Fake News Detection One of the challenges ..." : a heading glued to the first sentence
_GLUED_HEADING = re.compile(r"^(?:[A-Z][a-z]+\s+){2,4}(?=(?:One|The|In|We|This|There|It|A|An)\s)")


def _relation(sentence: str) -> str:
    if _FUTURE.search(sentence):
        return "also_open"                      # "we will extend the repository": still planned, so not done
    if _LACK.search(sentence):
        return "also_open"                      # "the lack of a benchmark dataset ..." beats a later "we provide"
    if _ADDRESSES.search(sentence):
        return "addresses"
    if _ALSO_OPEN.search(sentence):
        return "also_open"
    return "related"


_REASON = {
    "addresses": "this paper says it builds or proposes something about the same topic",
    "also_open": "this paper also describes this as missing, limited or still to do",
    "related": "same topic, but it does not say whether it is solved",
}


def _semantic_chunks(project_id: int, gap: dict) -> list:
    """Chunk texts the embedding search finds for the gap (a bonus only; the word match decides)."""
    try:
        res = ev.search_similar_chunks(project_id=project_id, query=gap["evidence_snippet"], top_k=8,
                                       exclude_paper_id=gap["paper_id"])
        return [re.sub(r"\s+", " ", d) for d in (res.get("documents") or [[]])[0]]
    except Exception as exc:
        logger.warning("Semantic search not available for validation (%s)", exc)
        return []


def validate_gap(project_id: int, gap: dict, chunks: list, df: dict, n: int, papers: dict) -> dict:
    others = [c for c in chunks if c["paper_id"] != gap["paper_id"]]
    if not others:
        return {"verdict": "NO_OTHER_PAPERS", "evidence": [], "checked_papers": []}
    gap_terms = _terms(gap["evidence_snippet"])
    sem = _semantic_chunks(project_id, gap)
    found = []
    for c in others:
        flat = re.sub(r"\s+", " ", c["text"])
        rank = next((i for i, d in enumerate(sem) if flat[:80] in d or d[:80] in flat), None)
        bonus = 0.0 if rank is None else SEMANTIC_BONUS[0 if rank < SEMANTIC_TOP else 1]
        for s in ev._sentences(flat):
            s = _GLUED_HEADING.sub("", s)
            if re.match(r"\d+(?:\.\d+)*\s", s) or s.count("•") or s.count("…"):
                continue                                          # "2 Background and Related Work Fake news ..." : heading glued on
            if not (8 <= len(s.split()) <= 60) or ev._is_table_sentence(s) or ev._TABLE_FRAGMENT.search(s) or ev._ROADMAP.search(s):
                continue
            sim, shared = _similarity(gap_terms, _terms(s), df, n)
            relation = _relation(s)
            # three shared topic words are strong even when the gap sentence is long (long sentences dilute the score);
            # two shared words need a higher score
            ok = (len(shared) >= 3 and sim + bonus >= 0.18) or (len(shared) >= MIN_SHARED and sim + bonus >= SIM_MIN)
            if not ok and relation == "addresses" and rank is not None and rank < SEMANTIC_TOP:
                # "we construct a data repository ..." in one of the 3 chunks the embedding search ranks closest:
                # one shared word is enough, because the clear own-work verb and the close chunk carry the match
                ok = len(shared) >= 1 and sim + bonus >= 0.25
            if ok:
                found.append({"paper_id": c["paper_id"], "paper_title": papers.get(c["paper_id"], f"Paper {c['paper_id']}"),
                              "page": c["page"], "section": c["section"], "sentence": s, "relation": relation,
                              "similarity": round(sim + bonus, 2), "shared_words": sorted(shared)[:6]})
    # best first; the same sentence can sit in two overlapping chunks
    found.sort(key=lambda e: -e["similarity"])
    seen, evidence = set(), []
    for e in found:
        key = re.sub(r"[^a-z0-9]", "", e["sentence"].lower())[:80]
        if key in seen:
            continue
        seen.add(key)
        e["reason"] = _REASON[e["relation"]]
        e["citation"] = f"[Paper {e['paper_id']}, Page {e['page']}]"
        evidence.append(e)
    # keep the strongest few of each kind, so one kind does not hide the other
    keep = []
    for rel in ("addresses", "also_open", "related"):
        keep += [e for e in evidence if e["relation"] == rel][: (PER_GAP if rel != "related" else 2)]
    keep.sort(key=lambda e: -e["similarity"])
    addresses = [e for e in keep if e["relation"] == "addresses"]
    opened = [e for e in keep if e["relation"] == "also_open"]
    if addresses and opened:
        verdict = "MIXED"
    elif addresses:
        verdict = "CHALLENGED"
    elif opened:
        verdict = "CORROBORATED"
    else:
        verdict = "STANDS"
    return {"verdict": verdict, "evidence": keep, "checked_papers": sorted({c["paper_id"] for c in others})}


VERDICT_TEXT = {
    "CORROBORATED": "Supported: another paper also reports this as open.",
    "CHALLENGED": "Possibly addressed: another paper reports work on it. Check the sentence to judge how far.",
    "MIXED": "Mixed: one paper reports it as open, another reports working on it.",
    "STANDS": "No counter-evidence found in the other papers.",
    "NO_OTHER_PAPERS": "There is no other paper to compare with.",
}


def validate_project(project_id: int, papers: list) -> dict:
    """papers: [{"id", "title"}]. Validates every saved gap and saves the result."""
    saved = gs.load_gaps(project_id)
    if not saved or not saved.get("gaps"):
        raise ValueError("No gaps found yet. Run Gap Detection first.")
    titles = {p["id"]: p.get("title") or f"Paper {p['id']}" for p in papers}
    chunks, df, n = _corpus(project_id)
    for gap in saved["gaps"]:
        result = validate_gap(project_id, gap, chunks, df, n, titles)
        gap["validation"] = {**result, "summary": VERDICT_TEXT[result["verdict"]],
                             "checked_at": datetime.utcnow().isoformat(timespec="seconds") + "Z"}
        gap["status"] = result["verdict"]
    saved["validated_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    gs._save(project_id, saved)
    return saved