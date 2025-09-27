from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from embedding import content_embedder
from vector_db_helper import upsert_folder
from config import FORMATS, VECTOR_SIZE, DISTANCE


#### functions for initialization, needed only once at first

def init_recreate_collections(client):
    # 컬렉션(테이블) 생성, only once

    for col_name in FORMATS.keys():

        client.recreate_collection(
            collection_name= col_name,
            vectors_config={
                "vector": VectorParams(
                    size=VECTOR_SIZE, # 벡터 차원 수
                    distance=DISTANCE  # 유사도 계산 방식
                )
            }
        )

 
def init_upsertall(client, path):
    # path 아래 있는 모든 폴더의 json 파일을 DB에 업로드
    
    for col_name in FORMATS.keys():
        folder_name = col_name.split(".")[0] + "/" + col_name.split(".")[1]

        upsert_folder(client,path + folder_name, col_name) # put limit number of datas if needed
    