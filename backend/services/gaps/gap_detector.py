def detect_gap(evidence_summary):
    """
    Detect a potential research gap from cross-paper evidence.
    """

    total_papers = evidence_summary.get("total_papers", 0)

    if total_papers == 0:
        return {
            "gap_detected": False,
            "reason": "No relevant evidence found."
        }

    # Collect categories represented across the retrieved papers
    categories = set()

    for paper in evidence_summary.get("papers", []):
        for evidence in paper.get("evidence", []):
            categories.add(evidence.get("category"))

    gaps = []

    if "dataset" not in categories:
        gaps.append("Limited evidence about datasets.")

    if "methodology" not in categories:
        gaps.append("Limited evidence about methodology.")

    if "results" not in categories:
        gaps.append("Limited evidence about reported results.")

    if "limitations" not in categories:
        gaps.append("Limited evidence about limitations and future work.")

    if gaps:
        return {
            "gap_detected": True,
            "gap_type": "evidence_based",
            "gaps": gaps,
            "total_papers": total_papers
        }

    return {
        "gap_detected": False,
        "gap_type": None,
        "gaps": [],
        "total_papers": total_papers
    }