from backend.services.vectorstore.chroma_service import get_collection
from backend.services.embeddings.embedding_service import generate_embedding


def retrieve_chunks(query, top_k=5, category=None):
    collection = get_collection()

    query_embedding = generate_embedding(query)

    where_filter = None

    if category:
        where_filter = {
            "category": category
        }

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where_filter
    )

    retrieved_chunks = []

    for i in range(len(results["documents"][0])):
        retrieved_chunks.append({
            "text": results["documents"][0][i],
            "paper_id": results["metadatas"][0][i]["paper_id"],
            "page_number": results["metadatas"][0][i]["page_number"],
            "category": results["metadatas"][0][i]["category"],
            "distance": results["distances"][0][i]
        })

    return retrieved_chunks