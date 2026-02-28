import json

overlap = 80
with open('app/vector_store/subject_1/metadata.json', 'r') as f:
    metadata = json.load(f)

indices = [11, 12, 13, 14]

merged = metadata[indices[0]]["text"]
for i in range(1, len(indices)):
    merged += metadata[indices[i]]["text"][overlap:]

print(merged)
