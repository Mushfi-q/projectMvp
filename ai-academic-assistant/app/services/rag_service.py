import os
import re
import json
import numpy as np
import faiss
from functools import lru_cache
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


def build_index(subject_id, pdf_path):
    subject_path = os.path.join(
        VECTOR_STORE_PATH, f"subject_{subject_id}"
    )
    os.makedirs(subject_path, exist_ok=True)

    index_file = os.path.join(subject_path, "index.faiss")
    meta_file = os.path.join(subject_path, "metadata.json")

    logger.info(f"Extracting text from PDF: {pdf_path}")
    text = extract_text_from_pdf(pdf_path)
    new_chunks = chunk_text(text)

    model = get_embed_model()
    new_embeddings = model.encode(new_chunks)
    new_embeddings = np.array(new_embeddings).astype("float32")

    # Load existing index + metadata if they exist (append mode)
    existing_metadata = []
    if os.path.exists(index_file) and os.path.exists(meta_file):
        logger.info(f"Appending to existing FAISS index for subject {subject_id}")
        existing_index = faiss.read_index(index_file)
        with open(meta_file, "r") as f:
            existing_metadata = json.load(f)
        existing_index.add(new_embeddings)
        index = existing_index
    else:
        logger.info(f"Creating new FAISS index for subject {subject_id}")
        dimension = new_embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(new_embeddings)

    faiss.write_index(index, index_file)

    # Append new chunks to metadata with correct indices
    start_index = len(existing_metadata)
    for i, chunk in enumerate(new_chunks):
        existing_metadata.append({
            "chunk_index": start_index + i,
            "text": chunk
        })

    with open(meta_file, "w") as f:
        json.dump(existing_metadata, f)

    logger.info(f"Subject {subject_id} index now has {len(existing_metadata)} total chunks")

    # Invalidate Python RAM cache so next student query fetches these updated embeddings
    load_faiss_index.cache_clear()
    
    # Also invalidate global LLM response cache in ai_service
    try:
        from app.services.ai_service import _response_cache
        _response_cache.clear()
        logger.info("Cleared global _response_cache to accommodate new syllabus embeddings.")
    except Exception as e:
        logger.warning(f"Could not clear ai_service _response_cache: {e}")

    return True


@lru_cache(maxsize=5)
def load_faiss_index(index_path, metadata_path):
    if not os.path.exists(index_path):
        return None, None
        
    index = faiss.read_index(index_path)
    with open(metadata_path, "r") as f:
        metadata = json.load(f)
        
    return index, metadata

def retrieve_chunks(subject_offering_id, query, k=8):
    subject_path = os.path.join(
        VECTOR_STORE_PATH, f"subject_{subject_offering_id}"
    )

    index_path = os.path.join(subject_path, "index.faiss")
    metadata_path = os.path.join(subject_path, "metadata.json")

    index, metadata = load_faiss_index(index_path, metadata_path)
    
    if not index:
        return []

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
