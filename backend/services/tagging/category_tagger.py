CATEGORIES = [
    "methodology",
    "dataset",
    "results",
    "limitations",
    "related_work",
    "citation"
]


def tag_chunk(text):
    text_lower = text.lower()

    scores = {
        category: 0
        for category in CATEGORIES
    }

    keywords = {
        "methodology": ["methodology", "method", "approach", "model", "algorithm"],
        "dataset": ["dataset", "data", "corpus", "samples", "participants"],
        "results": ["results", "accuracy", "precision", "recall", "f1", "performance"],
        "limitations": ["limitation", "limitations", "future work", "drawback"],
        "related_work": ["related work", "previous work", "existing work", "literature"],
        "citation": ["reference", "references", "cited", "et al."]
    }

    for category, words in keywords.items():
        for word in words:
            if word in text_lower:
                scores[category] += 1

    best_category = max(scores, key=scores.get)

    if scores[best_category] == 0:
        best_category = "related_work"

    return best_category