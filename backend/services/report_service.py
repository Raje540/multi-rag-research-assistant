"""
Final Report: builds the research report from the SAVED results of the earlier steps.

No model is used here. Every sentence in the report is either
  - copied from the saved Evidence Analysis (each cell already carries its [Paper, Page] citation),
  - copied from the saved Gap Detection / Gap Validation (word-for-word quotes with page), or
  - a fixed sentence or a count written by this file.
So the report can never contain a claim that the earlier steps did not already trace to a page.
"""
import html as _html
import re
from datetime import datetime

from backend.services import evidence_service as ev
from backend.services.gap_service import load_gaps

VERDICT_LABEL = {
    "CORROBORATED": "Supported: another paper also reports this as open",
    "CHALLENGED": "Possibly addressed: another paper reports work on it (check the sentence)",
    "MIXED": "Mixed: evidence for and against",
    "STANDS": "No counter-evidence found in the other papers",
    "NO_OTHER_PAPERS": "No other paper to compare with",
    "DETECTED": "Not validated yet",
}
VERDICT_SHORT = {
    "CORROBORATED": "Supported", "CHALLENGED": "Possibly addressed", "MIXED": "Mixed",
    "STANDS": "No counter-evidence", "NO_OTHER_PAPERS": "No other paper", "DETECTED": "Not validated",
}
VERDICT_ORDER = ["CORROBORATED", "MIXED", "CHALLENGED", "STANDS", "NO_OTHER_PAPERS", "DETECTED"]
RELATION_LABEL = [
    ("also_open", "Other papers that also describe this as open or missing"),
    ("addresses", "Other papers that say they work on it"),
    ("related", "Related passages (same topic, no clear statement)"),
]
_EMPTY = {"", "not stated", "not found", "no relevant text found in this paper."}


def _clean(text) -> str:
    text = str(text or "")
    text = text.replace("\ufb01", "fi").replace("\ufb02", "fl").replace("\ufb00", "ff").replace("\ufb03", "ffi").replace("\ufb04", "ffl")
    return re.sub(r"\s+", " ", text).strip()


def _cell(dim_result) -> tuple:
    """(text, citation, how) for one Evidence Analysis cell."""
    if not dim_result:
        return "Not analysed yet", "", ""
    text = _clean(dim_result.get("summary"))
    if text.lower() in _EMPTY:
        return "Not stated in this paper", "", ""
    how = "summarised by the local model and checked against the text" if dim_result.get("method") == "llm" else "sentences taken from the paper"
    return text, _clean(dim_result.get("citation")), how


def _collect(project_id: int, papers: list) -> dict:
    evidence = {p["id"]: ev.load_cached(p["id"]) for p in papers}
    saved = load_gaps(project_id) or {}
    gaps = saved.get("gaps") or []
    return {"evidence": evidence, "gaps": gaps, "papers_without_gaps": saved.get("papers_without_gaps") or []}


def build_blocks(project: dict, papers: list) -> tuple:
    """Returns (blocks, info). A block is a tuple: (kind, ...)."""
    data = _collect(project["id"], papers)
    evidence, gaps = data["evidence"], data["gaps"]
    n = len(papers)
    analysed = [p for p in papers if evidence.get(p["id"])]
    missing_evidence = [p["id"] for p in papers if not evidence.get(p["id"])]
    counts = {k: 0 for k in VERDICT_ORDER}
    for g in gaps:
        counts[g.get("status") if g.get("status") in counts else "DETECTED"] += 1
    not_validated = counts["DETECTED"]
    model = next((r.get("model") for r in evidence.values() if r and r.get("model")), None)

    B = []
    name = project.get("name") or f"Project {project['id']}"
    B.append(("h1", f"Research Report: {name}"))
    meta = [f"Domain: {project.get('domain') or 'not given'}", f"Papers reviewed: {n}",
            f"Generated: {datetime.now().strftime('%d %B %Y')}"]
    B.append(("sub", " · ".join(meta)))
    if project.get("description"):
        B.append(("p", _clean(project["description"])))

    # 1. Executive summary ------------------------------------------------------------------
    B.append(("h2", "1. Executive summary"))
    B.append(("p", f"This report compares {n} research paper{'s' if n != 1 else ''} in the {project.get('domain') or 'selected'} domain. "
                   "It is built only from the saved results of Evidence Analysis, Gap Detection and Gap Validation. "
                   "Each statement carries a [Paper, Page] citation so it can be checked in the PDF."))
    bullets = [f"Evidence Analysis: {len(analysed)} of {n} papers analysed."]
    if gaps:
        parts = [f"{counts[k]} {VERDICT_SHORT[k].lower()}" for k in VERDICT_ORDER if counts[k]]
        bullets.append(f"Research gaps: {len(gaps)} found ({', '.join(parts)}).")
    else:
        bullets.append("Research gaps: none saved yet. Run Gap Detection first.")
    B.append(("bullets", bullets))
    key = []
    for status, lead in (("CORROBORATED", "Supported by another paper"), ("MIXED", "Mixed evidence"),
                         ("CHALLENGED", "Possibly addressed by another paper"), ("STANDS", "No counter-evidence found")):
        ids = [f"{g['gap_id']} ({_clean(g['title'])})" for g in gaps if g.get("status") == status]
        if ids:
            key.append(f"{lead}: " + "; ".join(ids) + ".")
    if key:
        B.append(("h3", "Gap results at a glance"))
        B.append(("bullets", key))

    # 2. Papers ---------------------------------------------------------------------------------
    B.append(("h2", "2. Papers reviewed"))
    B.append(("table", ["Paper", "Title"], [[f"Paper {p['id']}", _clean(p["title"])] for p in papers]))

    # 3. Comparison -----------------------------------------------------------------------------
    B.append(("h2", "3. Cross-paper comparison"))
    if missing_evidence:
        B.append(("note", "Evidence Analysis has not been run for: " + ", ".join(f"Paper {i}" for i in missing_evidence)
                  + ". Run it on the Evidence Analysis page, then generate the report again."))
    for dim in ev.DIMENSIONS:
        B.append(("h3", dim))
        rows = []
        for p in papers:
            text, cite, how = _cell((evidence.get(p["id"]) or {}).get("dimensions", {}).get(dim))
            rows.append([f"Paper {p['id']}", text, cite, how])
        B.append(("table", ["Paper", "Finding", "Citation", "How it was made"], rows))

    # 4. Gaps -------------------------------------------------------------------------------------
    B.append(("h2", "4. Research gaps and their validation"))
    if not gaps:
        B.append(("note", "No gaps are saved for this project. Run Gap Detection and Gap Validation, then generate the report again."))
    else:
        if not_validated:
            B.append(("note", f"{not_validated} gap(s) have not been validated yet. Run Gap Validation, then generate the report again."))
        B.append(("p", "A gap is a sentence copied word for word from a paper (a limitation, an open issue or future work). "
                       "Validation then searches the other papers for sentences that support the gap or say it is being worked on."))
        B.append(("table", ["Gap", "Title", "Stated in", "Verdict"],
                  [[g["gap_id"], _clean(g["title"]), g.get("citation", ""), VERDICT_SHORT.get(g.get("status"), "Not validated")] for g in gaps]))
        for g in gaps:
            B.append(("h3", f"{g['gap_id']} · {_clean(g['title'])}"))
            B.append(("p", f"**Type:** {g.get('type', 'Gap')} · **Stated in:** {g.get('citation', '')} ({_clean(g.get('paper_title'))})"))
            B.append(("quote", _clean(g["evidence_snippet"])))
            B.append(("p", f"**Verdict:** {VERDICT_LABEL.get(g.get('status'), VERDICT_LABEL['DETECTED'])}"))
            ev_list = (g.get("validation") or {}).get("evidence", [])
            for rel, label in RELATION_LABEL:
                items = [e for e in ev_list if e.get("relation") == rel]
                if not items:
                    continue
                B.append(("p", f"**{label}**"))
                B.append(("bullets", [f"{e['citation']} “{_clean(e['sentence'])}”" for e in items]))
            if g.get("status") == "STANDS":
                B.append(("note", "This means none of the other papers says it is solved. It does not prove that nobody solved it."))
        for pid in data["papers_without_gaps"]:
            B.append(("p", f"Paper {pid}: the authors do not state any limitation or future work in the text, so no gap was taken from it."))

    # 5. Limits -------------------------------------------------------------------------------------
    B.append(("h2", "5. How to read this report"))
    lim = [
        "Every finding is built from the text of the uploaded papers and has a page citation. Page numbers are PDF page numbers.",
        "“Not stated in this paper” means the system found no such statement. It does not mean the paper lacks it.",
        "Gap validation compares words and cue phrases, not meaning. A paper that says the same thing in very different words can be missed.",
        "“No counter-evidence found” is not proof that a gap is unsolved. It only means the other papers in this project do not say it is solved.",
        f"Only the {n} papers in this project were compared. Other literature was not searched.",
    ]
    if model:
        lim.append(f"Some summaries were written by a small local model ({model}). Each one was checked against the paper text; if the check failed, sentences from the paper were used instead.")
    B.append(("bullets", lim))

    info = {
        "papers": n, "analysed": len(analysed), "missing_evidence": missing_evidence,
        "gaps": len(gaps), "not_validated": not_validated, "verdicts": {k: v for k, v in counts.items() if v},
    }
    return B, info


# ---------------------------------------------------------------- renderers
def _md_escape_cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def to_markdown(blocks: list) -> str:
    out = []
    for b in blocks:
        kind = b[0]
        if kind == "h1":
            out.append(f"# {b[1]}")
        elif kind == "sub":
            out.append(f"*{b[1]}*")
        elif kind == "h2":
            out.append(f"## {b[1]}")
        elif kind == "h3":
            out.append(f"### {b[1]}")
        elif kind == "p":
            out.append(b[1])
        elif kind == "note":
            out.append(f"> ℹ️ {b[1]}")
        elif kind == "quote":
            out.append(f"> “{b[1]}”")
        elif kind == "bullets":
            out.append("\n".join(f"- {x}" for x in b[1]))
        elif kind == "table":
            head, rows = b[1], b[2]
            lines = ["| " + " | ".join(head) + " |", "|" + "|".join(["---"] * len(head)) + "|"]
            lines += ["| " + " | ".join(_md_escape_cell(c) for c in r) + " |" for r in rows]
            out.append("\n".join(lines))
    return "\n\n".join(out) + "\n"


def _h(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", _html.escape(str(text)))


_CSS = """
body{font-family:Georgia,'Times New Roman',serif;color:#1f2937;max-width:900px;margin:32px auto;padding:0 20px;line-height:1.55}
h1{font-size:28px;margin-bottom:4px} h2{font-size:21px;margin-top:34px;border-bottom:2px solid #0e7c70;padding-bottom:4px}
h3{font-size:17px;margin-top:22px} .sub{color:#6b7280;margin-top:0}
table{border-collapse:collapse;width:100%;margin:10px 0;font-size:14px} th,td{border:1px solid #d1d5db;padding:6px 8px;vertical-align:top;text-align:left}
th{background:#f3f4f6} blockquote{margin:10px 0;padding:8px 14px;background:#f3f6f5;border-left:4px solid #0e7c70}
.note{background:#fff7e6;border-left:4px solid #d69e2e;padding:8px 14px;margin:10px 0}
@media print{body{margin:0;max-width:none} h2,h3{page-break-after:avoid} tr,blockquote{page-break-inside:avoid}}
"""


def to_html(blocks: list, title: str) -> str:
    out = []
    for b in blocks:
        kind = b[0]
        if kind == "h1":
            out.append(f"<h1>{_h(b[1])}</h1>")
        elif kind == "sub":
            out.append(f"<p class='sub'>{_h(b[1])}</p>")
        elif kind in ("h2", "h3"):
            out.append(f"<{kind}>{_h(b[1])}</{kind}>")
        elif kind == "p":
            out.append(f"<p>{_h(b[1])}</p>")
        elif kind == "note":
            out.append(f"<div class='note'>{_h(b[1])}</div>")
        elif kind == "quote":
            out.append(f"<blockquote>“{_h(b[1])}”</blockquote>")
        elif kind == "bullets":
            out.append("<ul>" + "".join(f"<li>{_h(x)}</li>" for x in b[1]) + "</ul>")
        elif kind == "table":
            head = "".join(f"<th>{_h(c)}</th>" for c in b[1])
            rows = "".join("<tr>" + "".join(f"<td>{_h(c)}</td>" for c in r) + "</tr>" for r in b[2])
            out.append(f"<table><tr>{head}</tr>{rows}</table>")
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>{_html.escape(title)}</title>"
            f"<style>{_CSS}</style></head><body>{''.join(out)}</body></html>")


def build_report(project: dict, papers: list) -> dict:
    """project: {id, name, domain, description}; papers: [{id, title}] (indexed papers, in order)."""
    blocks, info = build_blocks(project, papers)
    title = f"Research Report: {project.get('name') or project['id']}"
    return {"project_id": project["id"], "title": title, "markdown": to_markdown(blocks),
            "html": to_html(blocks, title), "info": info}