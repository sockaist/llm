# Instal Docker: brew install --cask docker
# pip install 'qdrant-client[fastembed]'

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from embedding import content_embedder
from vector_db_helper import create_doc_upsert, read_doc, update_doc, delete_doc, search_doc, initialize_col, upsert_folder
from init import init_recreate_collections, init_upsertall
from config import QDRANT_API_KEY, QDRANT_URL, FORMATS, VECTOR_SIZE, DISTANCE

import json
import os


################## HELPTER CONSTANTS ############################

# 상수들은 config.py에서 import됨

INIT = True # set true to init DB


################### INITIALIZE ##########################

folder_path = "../../../../data/"
col_name = "portal.job"
 
# deployed Qdrant DB
client = QdrantClient(
    url=QDRANT_URL, 
    api_key=QDRANT_API_KEY
)

if(INIT):
    initialize_col(client, col_name) # 컬렉션(테이블) 생성
    init_recreate_collections(client) # 컬렉션(테이블) 생성
    init_upsertall(client, folder_path) # path 아래 있는 모든 폴더의 json 파일을 DB에 업로드

###########################################################


results = search_doc(client, "한국연구재단 연구직 원서 접수 기간","portal.job",2)

print(results)

for hit in results:
    print(f"ID={hit.id}, 거리={hit.score:.4f}, payload={hit.payload}")

