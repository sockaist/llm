# Instal Docker: brew install --cask docker
# pip install 'qdrant-client[fastembed]'

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from embedding import content_embedder
from vector_db_helper import create_doc_upsert, read_doc, update_doc, delete_doc, search_doc, initialize_col, upsert_folder
from init import init_recreate_collections, init_upsertall
from dotenv import load_dotenv

import json
import os


################## HELPTER CONSTANTS ############################


VECTOR_SIZE = 384 # dimension of embeded vectors, 384 for our embedding model
DISTANCE = Distance.COSINE # method to calculate distance in Qdrant DB

load_dotenv()
QDRANT_API_KEY = os.environ.get('QDRANT_API_KEY')

FORMATS = {"portal.job" : ["title","author","date","link","content"], "portal.startUp" : ["title","author","date","link","content"], 
           "csweb.news" : ["title","date","link","content"], "csweb.canlender" : ["title","date","link","content","location"], "csweb.research" : ["name","professor","field","web","email","phone","office","intro","etc"], "csweb.edu" : ["title","link","content"], "csweb.ai" : ["title","date","link","content"], "csweb.profs" : ["name","field","major","degree","web","mail","phone","office","etc"], "csweb.admin" : ["name","position","work","mail","phone","office","etc"],"csweb.refer" : ["name","web","etc"], 
           #TODO : add formats for notion crawling data
           }

INIT = False


################### INITIALIZE ##########################

folder_path = "data/"
col_name = "portal.job"
 
# deployed Qdrant DB
client = QdrantClient(
    url="https://7eb854c4-8645-4c1f-ae73-609313fb8842.us-east4-0.gcp.cloud.qdrant.io", 
    api_key=QDRANT_API_KEY
)

if(INIT):
    init_recreate_collections(client) # 컬렉션(테이블) 생성
    init_upsertall(client, folder_path) # path 아래 있는 모든 폴더의 json 파일을 DB에 업로드

###########################################################


results = search_doc(client, "한국연구재단 연구직 원서 접수 기간","portal.job",2)

print(results)

for hit in results:
    print(f"ID={hit.id}, 거리={hit.score:.4f}, payload={hit.payload}")

