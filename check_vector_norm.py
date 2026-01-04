from qdrant_client import QdrantClient
import numpy as np
import json

client = QdrantClient(
    "http://localhost:6333",
    api_key="f3f7559964924ec579b6cfae06df70ad61c2f1b857ff10ea4a3cb35e11de6f73" 
)

print(f"Collection Info: {client.get_collection('csweb')}")
print("-" * 20)

res, _ = client.scroll(
    collection_name="csweb",
    limit=5,
    with_vectors=True,
    with_payload=True
)

for point in res:
    print(f"ID: {point.id}")
    print(f"  Payload: {point.payload}")
    v = point.vector
    # ... rest of vector check ...
    if isinstance(v, dict):
        if 'dense' in v:
            vec = np.array(v['dense'])
        elif 'title' in v:
            vec = np.array(v['title'])
        else:
            print("  Complex vector type:", v.keys())
            continue
    else:
         vec = np.array(v)
            
    norm = np.linalg.norm(vec)
    print(f"  Shape: {vec.shape}")
    print(f"  Norm: {norm}")
    print(f"  Sample: {vec[:5]}")
