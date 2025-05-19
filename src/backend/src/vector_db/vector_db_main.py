# Instal Docker: brew install --cask docker
# pip install 'qdrant-client[fastembed]'

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from embedding import content_embedder
from vector_db_helper import create_doc_upsert, read_doc, update_doc, delete_doc, search_doc, initialize_col
import json

import os
print(os.getcwd())

VECTOR_SIZE = 384 # dimension of embeded vectors, 384 for our embedding model
DISTANCE = Distance.COSINE # method to calculate distance in Qdrant DB

folder_path = "data/portal/job"
col_name = "portal.job"
 
# deployed Qdrant DB
client = QdrantClient(
    url="https://7eb854c4-8645-4c1f-ae73-609313fb8842.us-east4-0.gcp.cloud.qdrant.io", 
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.RA0jLn9d45PSYraNk4tpNeCPFcUgpkOILUBkFc2-w2g",
)

# initialize_col(client, "portal.job")
# cnt=0

# for filename in os.listdir(folder_path):
#     if(cnt > 10): break
#     cnt += 1
#     if filename.endswith(".json"):
#         file_path = os.path.join(folder_path, filename)

#         try:
#             with open(file_path, 'r', encoding='utf-8') as f:
#                 data = json.load(f)

#             print(f"uploading: {filename} → '{col_name}'")
#             create_doc_upsert(client, col_name, data)

#         except Exception as e:
#             print(f"Error ({filename}): {e}")

results = search_doc(client, "한국연구재단 연구직 원서 접수 기간","portal.job",2)

# # 4) 유사도 검색 (쿼리 벡터를 넣고 top-2 검색)
# results = client.search(
#     collection_name="my_collection",
#     query_vector=[0.15]*128,
#     limit=2
# )

print(results)

for hit in results:
    print(f"ID={hit.id}, 거리={hit.score:.4f}, payload={hit.payload}")

