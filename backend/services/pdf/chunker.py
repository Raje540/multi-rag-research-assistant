from backend.services.tagging.category_tagger import tag_chunk


def chunk_pages(pages, paper_id, chunk_size=1000, overlap=200):
    chunks = []

    for page in pages:
        text = page["text"]
        page_number = page["page_number"]

        start = 0
        chunk_number = 1

        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append({
                    "chunk_id": f"{paper_id}_{chunk_number}",
                    "paper_id": paper_id,
                    "page_number": page_number,
                    "text": chunk_text,
                    "category": tag_chunk(chunk_text)
                })

                chunk_number += 1

            start += chunk_size - overlap

    return chunks