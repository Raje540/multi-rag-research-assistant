def validate_gap(gap_result, evidence_summary, total_project_papers=None):
    """
    Validate a detected research gap using cross-paper evidence.

    Confidence is calculated as:

        supporting papers / total relevant papers
    """

    if not gap_result.get("gap_detected"):
        return {
            "validated": False,
            "confidence": 0.0,
            "supporting_papers": 0,
            "total_relevant_papers": 0,
            "status": "No gap detected"
        }

    if total_project_papers is None:
        total_project_papers = evidence_summary.get("total_papers", 0)

    if total_project_papers == 0:
        return {
            "validated": False,
            "confidence": 0.0,
            "supporting_papers": 0,
            "total_relevant_papers": 0,
            "status": "Insufficient evidence"
        }

    supporting_papers = evidence_summary.get("total_papers", 0)

    confidence = supporting_papers / total_project_papers

    if confidence >= 0.8:
        status = "Validated"
    elif confidence >= 0.5:
        status = "Validated with caveats"
    else:
        status = "Weak evidence"

    return {
        "validated": confidence >= 0.5,
        "confidence": round(confidence, 2),
        "supporting_papers": supporting_papers,
        "total_relevant_papers": total_project_papers,
        "status": status,
        "gaps": gap_result.get("gaps", [])
    }


def find_counter_evidence(gap_result, retrieved_chunks):
    """
    Search retrieved evidence for content that may contradict
    the proposed research gap.
    """

    counter_evidence = []

    gaps = gap_result.get("gaps", [])

    if not gaps:
        return counter_evidence

    gap_text = " ".join(gaps).lower()

    for chunk in retrieved_chunks:
        text = chunk.get("text", "").lower()

        if "dataset" in gap_text and "dataset" in text:
            counter_evidence.append(chunk)

        elif "methodology" in gap_text and (
            "method" in text or "methodology" in text
        ):
            counter_evidence.append(chunk)

        elif "results" in gap_text and (
            "results" in text
            or "accuracy" in text
            or "performance" in text
        ):
            counter_evidence.append(chunk)

        elif "limitations" in gap_text and (
            "limitation" in text or "future work" in text
        ):
            counter_evidence.append(chunk)

    return counter_evidence