# Multi-RAG Research Assistant

An evidence-traceable Multi-RAG system for analyzing multiple research papers, detecting potential research gaps, validating them using supporting and counter-evidence, and generating research directions.

## Tech Stack

- Python 3.10
- FastAPI
- Streamlit
- PostgreSQL
- ChromaDB
- Ollama
- Nomic Embed Text
- PyMuPDF

## Project Goal

The system analyzes multiple research papers from a selected research domain and identifies potential research gaps by comparing evidence across papers.

## Core Features

- Multiple research paper upload
- PDF text extraction
- Research-paper categorization
- Multi-paper RAG retrieval
- Evidence-based comparison
- Research gap detection
- Gap validation using supporting and counter-evidence
- Evidence traceability
- Research direction recommendations

## Architecture

User → Streamlit → FastAPI → PostgreSQL / ChromaDB / Ollama

## Status

🚧 Project under development.