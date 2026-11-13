import os
import logging
import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

# Initialize persistent local ChromaDB storage
CHROMA_DATA_PATH = "data/chroma_db"
os.makedirs(CHROMA_DATA_PATH, exist_ok=True)

chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)

# Initialize ChromaDB's native embedding function (loads model into RAM once)
print("Loading local embedding model (all-MiniLM-L6-v2)...")
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

def get_or_create_collection(project_id: int):
    """Get or create a dedicated ChromaDB collection with embedded vector function."""
    collection_name = f"project_{project_id}_chunks"
    return chroma_client.get_or_create_collection(
        name=collection_name,
        embedding_function=sentence_transformer_ef,
        metadata={"hnsw:space": "cosine"}
    )

def store_chunks_in_vector_db(
    project_id: int,
    paper_id: int,
    chunks: list[dict],
    batch_size: int = 100,
    paper_title: str = ""
) -> int:
    """
    Generates embeddings and upserts text chunks into ChromaDB in RAM-safe batches.
    Preserves paper_id, page, section, category and paper title metadata for
    evidence traceability.
    """
    if not chunks:
        return 0

    collection = get_or_create_collection(project_id)

    # Re-indexing the same paper: remove its old chunks first so no stale or
    # duplicate chunks stay behind.
    try:
        collection.delete(where={"paper_id": int(paper_id)})
    except Exception as exc:
        logger.warning("Could not clear old chunks for paper %s: %s", paper_id, exc)

    total_chunks = len(chunks)

    # Process chunks in batches to prevent RAM spikes on large documents
    for i in range(0, total_chunks, batch_size):
        batch = chunks[i : i + batch_size]

        documents = []
        metadatas = []
        ids = []

        for idx_offset, chunk in enumerate(batch):
            global_idx = i + idx_offset
            chunk_id = f"paper_{paper_id}_chunk_{global_idx}"

            documents.append(chunk["text"])
            metadatas.append({
                "paper_id": int(paper_id),
                "page": int(chunk["page"]),
                "chunk_index": global_idx,
                "section": str(chunk.get("section", "unknown")),
                "category": str(chunk.get("category", "Other")),
                "paper_title": str(paper_title or "")
            })
            ids.append(chunk_id)

        # Upsert batch into ChromaDB
        collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    return total_chunks

def delete_paper_chunks(project_id: int, paper_id: int) -> None:
    """Remove all indexed chunks of one paper from the project's collection."""
    collection = get_or_create_collection(project_id)
    collection.delete(where={"paper_id": int(paper_id)})

def search_similar_chunks(
    project_id: int,
    query: str,
    top_k: int = 5,
    paper_id_filter: int | None = None,
    category_filter: str | None = None,
    exclude_paper_id: int | None = None,
    include_citations: bool = False
):
    """
    Search for relevant text chunks across all project papers.
    Returns ChromaDB query results with fallback protection.

    Optional filters:
      paper_id_filter   - only search inside this paper
      category_filter   - only this category (e.g. "Limitations", "Methodology")
      exclude_paper_id  - skip this paper (used to look for evidence in the OTHER papers)
      include_citations - by default, reference-list chunks are left out of results
    """
    try:
        collection = get_or_create_collection(project_id)
        total = collection.count()

        # Check if collection is empty
        if total == 0:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]], "ids": [[]]}

        # Optional metadata filtering
        conditions = []
        if paper_id_filter:
            conditions.append({"paper_id": int(paper_id_filter)})
        if category_filter:
            conditions.append({"category": str(category_filter)})
        if exclude_paper_id:
            conditions.append({"paper_id": {"$ne": int(exclude_paper_id)}})

        if not conditions:
            where_clause = None
        elif len(conditions) == 1:
            where_clause = conditions[0]
        else:
            where_clause = {"$and": conditions}

        # Fetch extra results when reference chunks will be dropped afterwards
        fetch_k = top_k if include_citations else top_k * 2

        raw_results = collection.query(
            query_texts=[query],
            n_results=max(1, min(fetch_k, total)),
            where=where_clause
        )

        if not include_citations and raw_results.get("documents") and raw_results["documents"][0]:
            metas = raw_results["metadatas"][0]
            keep = [i for i, m in enumerate(metas) if (m or {}).get("category") != "Citation"][:top_k]
            for key in ("documents", "metadatas", "distances", "ids"):
                values = raw_results.get(key)
                if values and values[0] is not None:
                    raw_results[key] = [[values[0][i] for i in keep]]

        return raw_results

    except Exception as exc:
        logger.warning("Vector search failed: %s", exc)
        return {"documents": [[]], "metadatas": [[]], "distances": [[]], "ids": [[]]}