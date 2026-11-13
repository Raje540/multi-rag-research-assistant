import fitz  # PyMuPDF
import os
import re
import gc

# --------------------------------------------------------------------------
# Section detection + evidence categories
# --------------------------------------------------------------------------
# Each rule: (section name, evidence category, heading regex)
# Evidence categories: Methodology, Dataset, Results, Limitations,
#                      Related Work, Citation, Other
_SECTION_RULES = [
    ("abstract", "Other", r"abstract"),
    ("introduction", "Other", r"introduction"),
    ("related work", "Related Work",
     r"related (?:work|works|studies)|background|literature review|prior work|previous work|state of the art"),
    ("dataset", "Dataset",
     r"data(?: ?sets?| collection| description)?|corpus|corpora|benchmarks?"),
    ("methodology", "Methodology",
     r"method(?:s|ology)?|approach|proposed [a-z\- ]+|model(?: architecture| overview)?|framework|architecture"
     r"|preliminaries|problem (?:formulation|definition|statement)|system (?:design|overview)"),
    ("experiments", "Results",
     r"experiment(?:s|al)?(?: setup| settings?| details| design)?|implementation details"
     r"|evaluation(?: metrics| setup)?|baselines?"),
    ("results", "Results",
     r"results?|findings|performance|analysis|ablation(?: stud(?:y|ies))?|error analysis|case stud(?:y|ies)"),
    ("discussion", "Results", r"discussion"),
    ("limitations", "Limitations",
     r"limitations?|threats to validity|future (?:work|directions?|research)|open (?:problems|challenges|issues|questions)|challenges"),
    ("conclusion", "Other", r"conclusions?|concluding remarks|summary"),
    ("references", "Citation", r"references|bibliography"),
    ("appendix", "Other", r"appendix|appendices|supplementary material"),
]

# "3 Method", "3.2. Setup", "IV. Results", "A. Dataset"
_NUM_PREFIX = re.compile(r"^(?:(\d{1,2}(?:\.\d{1,2})*)\.?|([IVX]{1,4})\.|([A-Z])\.)\s+(\S.*)$")

# Words that signal a category when the section alone is not enough
_CUES = {
    "Limitations": [
        "limitation", "future work", "future research", "future direction", "remains challenging",
        "remain challenging", "remains an open", "open problem", "unsolved", "does not handle",
        "cannot handle", "fails to", "drawback", "shortcoming", "we plan to", "not yet",
        "open issue", "open question", "research direction",
    ],
    "Dataset": [
        "dataset", "data set", "corpus", "corpora", "benchmark", "annotated", "training set",
        "test set", "validation set", "train/test", "samples", "split",
    ],
    "Methodology": [
        "we propose", "our model", "our method", "our approach", "architecture", "algorithm",
        "encoder", "decoder", "module", "layer", "framework", "pipeline",
    ],
    "Results": [
        "accuracy", "f1", "precision", "recall", "outperform", "baseline", "improvement",
        "state-of-the-art",
    ],
    "Related Work": [
        "prior work", "previous work", "existing work", "existing approaches", "et al.",
        "have been proposed", "literature",
    ],
}


def _infer_heading_category(heading: str) -> str:
    """Guess a category from the words of a heading we have no exact rule for."""
    h = heading.lower()
    if re.search(r"limitation|future work|future direction|open (?:issue|problem)", h):
        return "Limitations"
    if re.search(r"data ?sets?|corpus|corpora|data collection|benchmark", h):
        return "Dataset"
    if re.search(r"experiment|evaluation|result|performance|comparison|findings", h):
        return "Results"
    if re.search(r"method|model|approach|architecture|framework|algorithm|feature|detection|learning", h):
        return "Methodology"
    if re.search(r"related|background|literature", h):
        return "Related Work"
    return "Other"


# A section number that sits alone on its own line, e.g. "3" or "3.2." (common in two-column papers)
_NUM_ONLY = re.compile(r"^\s*([1-9]\d?(?:\.\d{1,2})*)\.?\s*$")


def _join_split_headings(lines: list) -> list:
    """
    In many PDFs the section number and the title are separate lines ("3" then
    "Fake News Datasets"). Join them so the heading can be recognised.
    """
    out = []
    i, n = 0, len(lines)
    while i < n:
        m = _NUM_ONLY.match(lines[i])
        if m:
            j = i + 1
            while j < n and not lines[j].strip():
                j += 1
            if j < n:
                nxt = lines[j].strip()
                candidate = f"{m.group(1)} {nxt}"
                if (len(nxt) <= 80 and len(nxt.split()) <= 8 and nxt[0].isupper()
                        and not nxt.endswith((".", ",", ";"))
                        and _match_heading(candidate) is not None):
                    out.append(candidate)
                    i = j + 1
                    continue
        out.append(lines[i])
        i += 1
    return out


def _heading_category(text: str, category: str) -> str:
    """Headings like 'Conclusion and Future Work' are limitation/future-work sections."""
    if re.search(r"future|limitation", text, re.I):
        return "Limitations"
    return category


def _match_heading(line: str):
    """Return (section_name, category) if the line looks like a section heading, else None."""
    s = line.strip().rstrip(":")
    if not s or len(s) > 80 or len(s.split()) > 9:
        return None

    m = _NUM_PREFIX.match(s)
    if m:
        rest = m.group(4).strip()
        if not rest or not rest[0].isalpha():
            return None
        for name, cat, pattern in _SECTION_RULES:
            if re.match(rf"(?:{pattern})\b", rest, re.I):
                return name, _heading_category(rest, cat)
        # Unknown top-level numbered heading (e.g. "3 Hierarchical Tree Construction")
        top_num = m.group(1)
        if (top_num and "." not in top_num and 1 <= int(top_num) <= 20
                and len(rest.split()) >= 2
                and rest[0].isupper() and not rest.endswith((".", ",", ";"))):
            return rest.lower(), _infer_heading_category(rest)
        return None

    # Un-numbered headings must be short and match a known heading exactly
    if not s[0].isupper():
        return None
    for name, cat, pattern in _SECTION_RULES:
        if re.fullmatch(
            rf"(?:{pattern})(?:\s+(?:and|&)\s+[A-Za-z ]+|\s+(?:results?|analysis|setup|details))?",
            s, re.I,
        ):
            return name, _heading_category(s, cat)
    return None


def _count(text_lower: str, cues: list) -> int:
    return sum(text_lower.count(c) for c in cues)


_REF_YEAR = re.compile(r"\b(?:19|20)\d{2}[a-z]?\b")
_REF_MARKER = re.compile(
    r"\bpages? \d+\s*[–—\-]\s*\d+|\bpp\. ?\d|proceedings|association for|\bdoi\b"
    r"|arxiv preprint|arxiv:\d|\bjournal\b|\bvol(?:ume|\.)? ?\d|\bconference on\b|https?://",
    re.I,
)
_REF_NAME = re.compile(r"\b[A-Z]\.(?: ?[A-Z]\.)? ?[A-Z][a-z]{2,}")   # "M. Newman", "J. T. Hancock"


_REF_ENTRY = re.compile(r"[A-Za-z\)]\.\s(?:19|20)\d{2}[a-z]?\.\s")       # "... Hancock. 2013. Title of paper"
_REF_BRACKET = re.compile(r"(?:^|\s)\[\d{1,3}\]\s+[A-Z]")                 # "[12] A. Author, ..."


def looks_like_references(text: str) -> bool:
    """
    True when a chunk is (part of) a bibliography: many years, author initials,
    'Proceedings of', page ranges, DOIs, "Author. 2016. Title" entries.
    Works even when the 'References' heading was not detected
    (e.g. a list that continues on the next page).
    """
    years = len(_REF_YEAR.findall(text))
    markers = len(_REF_MARKER.findall(text))
    names = len(_REF_NAME.findall(text))
    entries = len(_REF_ENTRY.findall(text))
    brackets = len(_REF_BRACKET.findall(text))
    return ((years >= 3 and markers >= 2) or markers >= 4 or (names >= 4 and years >= 2)
            or entries >= 2 or (entries >= 1 and markers >= 1) or brackets >= 3)


def _refine_category(section: str, category: str, text: str) -> str:
    """Use the chunk's own wording to fix or improve the section-based category."""
    low = text.lower()

    # Reference lists that were not under a 'References' heading
    if category != "Citation" and looks_like_references(text):
        return "Citation"

    # Results text that sits under a heading we could not read (it inherited 'Related Work')
    if (category == "Related Work"
            and _count(low, _CUES["Related Work"]) == 0
            and _count(low, _CUES["Results"] + ["table ", "acc."]) >= 2):
        return "Results"

    # A results table that landed under a 'Methodology'-looking heading
    if category == "Methodology" and sum(low.count(w) for w in ("accuracy", "precision", "recall", "f1")) >= 6:
        return "Results"

    if category in ("Citation", "Limitations"):
        return category

    # Limitation / future-work statements inside conclusion, discussion or results
    if section in ("conclusion", "discussion", "results", "experiments"):
        if _count(low, _CUES["Limitations"]) >= 1:
            return "Limitations"

    if category == "Other":
        scores = {c: _count(low, _CUES[c])
                  for c in ("Limitations", "Dataset", "Methodology", "Results", "Related Work")}
        best, hits = max(scores.items(), key=lambda kv: kv[1])
        if hits >= 2:
            return best
    elif category == "Results" and section == "experiments":
        if _count(low, _CUES["Dataset"]) >= 3:
            return "Dataset"

    return category


# --------------------------------------------------------------------------
# Paper title extraction
# --------------------------------------------------------------------------
def _looks_like_title(text: str) -> bool:
    if not text or not (10 <= len(text) <= 250):
        return False
    low = text.lower()
    bad = ("microsoft word", "untitled", ".doc", ".tex", ".pdf", "arxiv")
    return not any(b in low for b in bad)


def extract_paper_title(file_path: str) -> str:
    """
    Best-effort paper title: PDF metadata first, otherwise the largest-font
    text near the top of page 1. Falls back to the file name.
    """
    fallback = os.path.splitext(os.path.basename(file_path))[0]
    try:
        doc = fitz.open(file_path)
    except Exception:
        return fallback

    try:
        meta_title = " ".join(((doc.metadata or {}).get("title") or "").split())
        if _looks_like_title(meta_title):
            return meta_title

        if len(doc) == 0:
            return fallback

        page = doc.load_page(0)
        lines = []
        for block in page.get_text("dict").get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                txt = "".join(sp.get("text", "") for sp in spans).strip()
                if not txt or not spans:
                    continue
                # Skip rotated text (e.g. the arXiv stamp in the page margin)
                direction = line.get("dir", (1, 0))
                if abs(direction[1]) > 0.1 or direction[0] <= 0:
                    continue
                # Skip stamp / banner lines that are not part of the title
                if re.match(r"(?i)^\s*(arxiv|preprint|under review|published as|submitted)", txt):
                    continue
                size = max(sp.get("size", 0) for sp in spans)
                lines.append((size, line["bbox"][1], txt))

        if not lines:
            return fallback

        top_size = max(size for size, _, _ in lines)
        page_height = page.rect.height or 800
        title_lines = sorted(
            (y, txt) for size, y, txt in lines
            if size >= top_size - 1 and y < page_height * 0.5
        )
        title = " ".join(" ".join(txt for _, txt in title_lines).split())
        return title if _looks_like_title(title) else fallback
    except Exception:
        return fallback
    finally:
        doc.close()


# --------------------------------------------------------------------------
# Chunking
# --------------------------------------------------------------------------
def _chunk_segment(text: str, page: int, section: str, category: str,
                   chunk_size: int, overlap: int, out: list):
    """Sliding-window chunking of one section segment (never crosses a section or page)."""
    text_length = len(text)
    start = 0

    while start < text_length:
        end = min(start + chunk_size, text_length)

        # Look for word boundary if not at the end
        if end < text_length:
            last_space = text.rfind(" ", start, end)
            # Only advance end to space if it moves start forward
            if last_space > start:
                end = last_space

        chunk_text = text[start:end].strip()

        if len(chunk_text) > 50:  # Ignore tiny useless chunks
            out.append({
                "page": page,
                "text": chunk_text,
                "section": section,
                "category": _refine_category(section, category, chunk_text),
            })

        # Reached the end of the segment: stop (avoids a duplicate tail chunk)
        if end >= text_length:
            break

        # Explicit Progress Guarantee: Prevent Infinite Loops
        next_start = end - overlap
        if next_start <= start:
            start = end  # Force forward movement if overlap gets stuck
        else:
            start = next_start


def process_pdf_to_chunks(file_path: str, chunk_size: int = 1000, overlap: int = 200, max_pages: int = 30):
    """
    Extracts text from a PDF safely and splits it into overlapping chunks.
    Preserves page numbers for citation tracking and guards against RAM crashes.

    Each chunk is a dict: {"page", "text", "section", "category"}.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Cannot find PDF at: {file_path}")

    doc = fitz.open(file_path)

    # 1. Safety Guard: Prevent processing oversized PDFs on 8 GB RAM systems
    total_pages = len(doc)
    if total_pages > max_pages:
        doc.close()
        raise ValueError(f"Safety Limit Reached: PDF has {total_pages} pages. Maximum allowed is {max_pages} pages to prevent system crash.")

    chunks = []
    current_section, current_category = "unknown", "Other"  # carries across pages

    try:
        for page_num in range(total_pages):
            page = doc.load_page(page_num)
            raw_text = page.get_text("text")

            if not raw_text.strip():
                del page
                continue

            # 2. Split the page into segments, starting a new one at each section heading
            segments = []
            buf = []
            seg_section, seg_category = current_section, current_category
            for line in _join_split_headings(raw_text.splitlines()):
                heading = _match_heading(line)
                if heading:
                    if buf:
                        segments.append((seg_section, seg_category, buf))
                        buf = []
                    seg_section, seg_category = heading
                    current_section, current_category = heading
                buf.append(line)
            if buf:
                segments.append((seg_section, seg_category, buf))

            # 3. Crash-Proof Sliding Window Chunking inside each segment
            for sec, cat, lines in segments:
                text = " ".join(" ".join(lines).split())  # clean up whitespace
                _chunk_segment(text, page_num + 1, sec, cat, chunk_size, overlap, chunks)

            # Explicit memory cleanup per page
            del page
            del raw_text

        doc.close()
        gc.collect()  # Force garbage collection to free RAM immediately
        return chunks

    except Exception as e:
        doc.close()
        gc.collect()
        raise e