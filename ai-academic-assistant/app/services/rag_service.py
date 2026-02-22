import os
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
        text += page.extract_text() or ""
    return text


def chunk_text(text, chunk_size=500, overlap=50):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
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


def retrieve_chunks(subject_offering_id, query, k=3):
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

    model = get_embed_model()
    query_embedding = model.encode([query])
    query_embedding = np.array(query_embedding).astype("float32")

    distances, indices = index.search(query_embedding, k)

    retrieved = [
        metadata[i]["text"]
        for i in indices[0]
        if i < len(metadata)
    ]

    return retrieved
