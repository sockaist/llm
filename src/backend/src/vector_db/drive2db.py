from qdrant_client import QdrantClient, models
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, PointIdsList, FilterSelector
from qdrant_client.models import SearchRequest, SearchParams, NamedVector
from qdrant_client.http.models import ScoredPoint
import requests
import io, re, csv
from typing import Dict, Any
import pdfplumber 
import zipfile
from embedding import content_embedder
from config import QDRANT_URL, QDRANT_API_KEY, VECTOR_SIZE, DISTANCE

FORMAT = ["date","link","content","id"]
PDF_MAGIC = b'%PDF'
client = QdrantClient(
    url=QDRANT_URL, 
    api_key=QDRANT_API_KEY
)

def drive2db(date: str, link: str, id: int) -> Dict[str, Any]:
    """
    Google Drive URL에서 데이터를 추출하고 지정된 딕셔너리 형태로 반환합니다.

    Args:
        date (str): 문서와 관련된 날짜 정보 (예: "2025-10-25").
        link (str): Google Drive 공유 파일 URL (예: https://drive.google.com/file/d/~~~~/view?usp=sharing)

    Returns:
        Dict[str, Any]: 파싱된 데이터(date, link, content, id)를 포함하는 dictionary.
    """
    full_text = []
    
    # 1. 파일 타입(pdf, word) 구분
    file_type = classify_file_type(link)

    # 2. 파일 타입에 따라 프로세싱
    if file_type=="pdf":
        link_id = re.search(r'/d/([a-zA-Z0-9_-]+)', link)
        file_id = link_id.group(1)
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        try:
            response = requests.get(download_url, stream=True)
            response.raise_for_status() 
            file_stream = io.BytesIO(response.content)

        except requests.exceptions.RequestException as e:
            print(f"다운로드 중 오류 발생: {e}")
            return {
                "date": date, "link": link, "content": f"DOWNLOAD ERROR: {e}"
            }
        try:
            with pdfplumber.open(file_stream) as pdf:
                for page_index, page in enumerate(pdf.pages):
                    # 1. 텍스트 추출
                    page_text = page.extract_text()
                    if page_text:
                        lines = page_text.split('\n')
                        for line in lines:
                            cleaned_line = " ".join(line.strip().split())
                            cleaned_line = re.sub(r"[^0-9A-Za-z가-힣\s.,!?\-()]", "", cleaned_line)
                            if cleaned_line:
                                full_text.append(cleaned_line)

                    # 2. 이미지 처리 구조는 남겨두지만, 실제 바이너리/설명은 스킵
                    if page.images:
                        full_text.append("<IMAGE>")

                    # 3. 페이지 구분 
                    full_text.append(f"<PAGE_BREAK: {page_index}>")

        except Exception as e:
            print(f"PDF 처리 중 오류 발생: {e}")
            return {
                "date": date, "link": link, "content": f"PARSING ERROR: {e}"
            }
        
    elif file_type=="word":
        # 드라이브에 워드 파일 올리면 구글 독스로 변하는 이슈가 있어서 처리가 어려움.
        pass

    else:
        print(f"error: {link} is neither pdf nor word.")
        return dict()

    # 4. 최종 딕셔너리 생성 및 반환
    info = {
        "date": date+"T00:00:00Z",
        "link": link,
        "content": " ".join(full_text).strip(),
        "id": id
    }

    return info


def classify_file_type(link:str) -> str:
    """
    구글 드라이브 파일의 형식(word, pdf)을 구분합니다.
    """
    
    if re.search(r'docs\.google\.com/document/d/', link):
        return "word"
    elif re.search(r'drive\.google\.com/file/d/', link):
        return "pdf"    
    else:
        return "unknown"


def drive_upsert_all(client, file_path):
    """
    date, link 형식의 csv 파일을 읽어 각 행을 DB에 업로드합니다.

    Args:
        file_path (str): csv 파일의 경로.

    Returns:
        None
    """
    output_list = []

    try:
        with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            row_count = 1
            
            for row in reader:
                date_key = 'date'
                link_key = 'link'
                
                if date_key in row and link_key in row:
                    data = drive2db(row['date'], row['link'], row_count)
                    create_doc_upsert(client, data)
                    row_count += 1
                else:
                    print(f"Warning: {row_count}번째 행이 잘못되었습니다.")
                    row_count += 1
                    
    except FileNotFoundError:
        print(f"Error: 파일을 찾을 수 없습니다: {file_path}")
    except Exception as e:
        print(f"Error: CSV 파일을 처리하는 중 예기치 않은 오류 발생: {e}")
        
    return output_list


def init_drive_collections(client):
    client.recreate_collection(
        collection_name="drive",
        vectors_config={
            "vector": VectorParams(
                size=VECTOR_SIZE, 
                distance=DISTANCE
            )
        }
    )
    client.create_payload_index(
        collection_name="drive",
        field_name="id",
        field_schema=models.PayloadSchemaType.INTEGER
    )
        



def create_doc_upsert(client, data):
    """
    Args:
        client: qdrant client for cur DB
        data: dictionary data to upsert
    """
    try:
        if not data:
            print("Warning: Empty data provided to create_doc_upsert")
            return
        
        raw_text = data["content"]
        id = data["id"]
        exist = client.count(
            collection_name="drive",
            count_filter=models.Filter(
                must=[models.FieldCondition(
                    key="id", 
                    match=models.MatchValue(value=id),
                )]
            ),
            exact=False,  
        ).count > 0
        if exist:
            print(f"Info: Document with id {id} already exists in drive, skipping upsert.")
            return

        
        if not raw_text or not raw_text.strip():
            print(f"Warning: Empty content in data for collection drive")
            print(f"Data keys: {list(data.keys()) if data else 'None'}")
            return

        print(f"Processing text of length: {len(raw_text)}")
        chunks = content_embedder(raw_text) 

        if not chunks:
            print(f"Warning: No chunks generated for data in collection drive")
            return
        
        id = client.count(
            collection_name = "drive",
            exact=True
        ).count + 1
        
        points = []

        for t,v in chunks:
            payload = {}
            payload["text"] = t

            for name in FORMAT:
                payload[name] = data[name]
            payload["id"] = int(data["id"])

            new_p = PointStruct(
                id= id,
                vector= {"vector": v},
                payload= payload
            )
            print(f"Created point {id} with vector shape: {v.shape if hasattr(v, 'shape') else len(v)}")

            id += 1 
            points.append(new_p)
        
        if points:
            client.upsert(collection_name="drive", points=points)
            print(f"Successfully upserted {len(points)} points to drive")
        else:
            print(f"No points to upsert for collection drive")
            
    except Exception as e:
        print(f"Error in create_doc_upsert for collection drive: {e}")
        print(f"Data: {data}")
        raise


if __name__ == "__main__":
    # init_drive_collections(client)
    drive_upsert_all(client, "./drive_list")