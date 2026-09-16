import chromadb


CHROMA_PATH = "./chroma_db"

client = chromadb.PersistentClient(path=CHROMA_PATH)

collection = client.get_or_create_collection(
    name="research_chunks"
)


def add_chunk(chunk, embedding):
    collection.add(
        ids=[chunk["chunk_id"]],
        embeddings=[embedding],
        documents=[chunk["text"]],
        metadatas=[{
            "paper_id": str(chunk["paper_id"]),
            "page_number": str(chunk["page_number"]),
            "category": chunk["category"]
        }]
    )


def get_collection():
    return collection