from backend.services.pdf.extractor import extract_text_from_pdf
from backend.services.pdf.chunker import chunk_pages
from backend.services.embeddings.embedding_service import generate_embedding
from backend.services.vectorstore.chroma_service import add_chunk


def ingest_pdf(pdf_path, paper_id):
    pages = extract_text_from_pdf(pdf_path)

    chunks = chunk_pages(
        pages,
        paper_id=paper_id
    )

    for chunk in chunks:
        embedding = generate_embedding(chunk["text"])
        add_chunk(chunk, embedding)

    print(f"Ingestion complete: {len(chunks)} chunks added")


if __name__ == "__main__":
    ingest_pdf(
        "data/uploads/ssrn-3798873.pdf",
        paper_id=3
    )