import requests


OLLAMA_URL = "http://localhost:11434/api/embeddings"
MODEL_NAME = "nomic-embed-text"


def generate_embedding(text):
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": text
        }
    )

    response.raise_for_status()

    return response.json()["embedding"]