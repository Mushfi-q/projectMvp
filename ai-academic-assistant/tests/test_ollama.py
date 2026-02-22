import ollama

response = ollama.chat(
    model='phi3:mini',
    messages=[
        {"role": "user", "content": "Explain what is Machine Learning in simple terms."}],
    options={"num_predict": 200}
)

print(response['message']['content'])
