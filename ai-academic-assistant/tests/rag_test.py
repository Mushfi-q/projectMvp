import ollama
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# 1️⃣ Load embedding model (lightweight)
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

# 2️⃣ Sample document (simulate syllabus text)
documents = [
    "Machine Learning is a field of Artificial Intelligence.",
    "Supervised learning uses labeled data.",
    "Unsupervised learning finds hidden patterns.",
    "Neural networks are inspired by the human brain."
]

# 3️⃣ Generate embeddings
embeddings = embed_model.encode(documents)

# Convert to numpy float32
embeddings = np.array(embeddings).astype("float32")

# 4️⃣ Create FAISS index
dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)

print("FAISS index built successfully")

# 5️⃣ Query
query = "What is supervised learning?"
query_embedding = embed_model.encode([query])
query_embedding = np.array(query_embedding).astype("float32")

# 6️⃣ Search
k = 2
distances, indices = index.search(query_embedding, k)

retrieved_docs = [documents[i] for i in indices[0]]

print("Retrieved context:", retrieved_docs)

# 7️⃣ Send to Ollama with context
context = "\n".join(retrieved_docs)

prompt = f"""
Use the context below to answer the question.

Context:
{context}

Question:
{query}
"""

response = ollama.chat(
    model="phi3:mini",
    messages=[{"role": "user", "content": prompt}]
)

print("\nLLM Response:\n")
print(response["message"]["content"])
