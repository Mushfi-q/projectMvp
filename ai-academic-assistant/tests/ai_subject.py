from app.services.ai_service import generate_subject_response

subject_id = 1

query = "What is IoT? List different definitions."

response = generate_subject_response(subject_id, query)

print("\nAI RESPONSE:\n")
print(response)
