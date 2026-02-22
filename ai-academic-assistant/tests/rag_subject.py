from app.services.rag_service import build_index, retrieve_chunks

# Replace with a real PDF path
pdf_path = "iot-module1.pdf"

subject_id = 1

build_index(subject_id, pdf_path)

results = retrieve_chunks(subject_id, "What is iot? List different types of definitions")

print(results)
