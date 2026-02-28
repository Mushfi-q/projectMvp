import os
import re
import json
import numpy as np
import faiss
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from app.utils.logger import logger

VECTOR_STORE_PATH = "app/vector_store"

_embed_model = None

def get_embed_model():
    global _embed_model
    if _embed_model is None:
        try:
            _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            logger.warning(f"Error loading model, trying offline/local: {e}")
            _embed_model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
    return _embed_model


def extract_text_from_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text() or ""
        page_text = re.sub(r'\s+', ' ', page_text)  # normalize spaces
        text += page_text
    return text


def chunk_text(text, chunk_size=300, overlap=80):
    chunks = []
    
    # Split by major section first (e.g., "1. Introduction to IoT")
    parts = re.split(r'(\d+\.\s+[A-Za-z ]+)', text)
    
    sections = []
    if parts:
        # Add any initial text before the first heading
        if parts[0].strip():
            sections.append(parts[0])
            
        # Reconstruct heading + content blocks
        for i in range(1, len(parts), 2):
            heading = parts[i]
            content = parts[i+1] if i+1 < len(parts) else ""
            sections.append(heading + content)
            
    # Chunk inside each section independently
    for section in sections:
        start = 0
        while start < len(section):
            end = start + chunk_size
            chunks.append(section[start:end])
            start += chunk_size - overlap
            
    return chunks


def build_index(subject_offering_id, pdf_path):
    subject_path = os.path.join(
        VECTOR_STORE_PATH, f"subject_{subject_offering_id}"
    )
    os.makedirs(subject_path, exist_ok=True)

    logger.info(f"Extracting text from PDF: {pdf_path}")
    text = extract_text_from_pdf(pdf_path)
    chunks = chunk_text(text)

    model = get_embed_model()
    embeddings = model.encode(chunks)
    embeddings = np.array(embeddings).astype("float32")

    dimension = embeddings.shape[1]
    logger.info(f"Building FAISS index for subject {subject_offering_id}")
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    faiss.write_index(index, os.path.join(subject_path, "index.faiss"))

    metadata = [
        {"chunk_index": i, "text": chunk}
        for i, chunk in enumerate(chunks)
    ]

    with open(os.path.join(subject_path, "metadata.json"), "w") as f:
        json.dump(metadata, f)

    return True


def retrieve_chunks(subject_offering_id, query, k=8):
    subject_path = os.path.join(
        VECTOR_STORE_PATH, f"subject_{subject_offering_id}"
    )

    index_path = os.path.join(subject_path, "index.faiss")
    metadata_path = os.path.join(subject_path, "metadata.json")

    if not os.path.exists(index_path):
        return []

    index = faiss.read_index(index_path)

    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    # Keyword Boost Hack
    query_lower = query.lower()
    if "definition" in query_lower or "define" in query_lower:
        query = query + " Definitions for IoT"

    model = get_embed_model()
    query_embedding = model.encode([query])
    query_embedding = np.array(query_embedding).astype("float32")

    distances, indices = index.search(query_embedding, k)

    # Expand context to include adjacent chunks (small-to-big retrieval) to fix fragmented definitions
    context_indices = set()
    for i in indices[0]:
        if i >= 0:
            context_indices.update([int(i)-3, int(i)-2, int(i)-1, int(i), int(i)+1, int(i)+2])

    valid_indices = sorted([i for i in context_indices if 0 <= i < len(metadata)])

    retrieved = []
    if valid_indices:
        overlap = 80
        merged = metadata[valid_indices[0]]["text"]
        for i in range(1, len(valid_indices)):
            if valid_indices[i] == valid_indices[i-1] + 1:
                merged += metadata[valid_indices[i]]["text"][overlap:]
            else:
                retrieved.append(merged)
                merged = metadata[valid_indices[i]]["text"]
        retrieved.append(merged)

    return retrieved
