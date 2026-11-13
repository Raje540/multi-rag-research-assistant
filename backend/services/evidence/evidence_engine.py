def build_evidence_summary(retrieved_chunks):
    papers = {}

    for chunk in retrieved_chunks:
        paper_id = chunk["paper_id"]

        if paper_id not in papers:
            papers[paper_id] = {
                "paper_id": paper_id,
                "evidence": []
            }

        papers[paper_id]["evidence"].append({
            "page_number": chunk["page_number"],
            "category": chunk["category"],
            "text": chunk["text"],
            "distance": chunk["distance"]
        })

    total_papers = len(papers)

    return {
        "total_papers": total_papers,
        "papers": list(papers.values())
    }