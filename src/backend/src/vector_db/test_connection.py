"""
Qdrant 연결 테스트 및 컬렉션 확인 스크립트
"""

from qdrant_client import QdrantClient
from config import QDRANT_API_KEY, QDRANT_URL

try:
    # Qdrant 클라이언트 생성
    client = QdrantClient(
        url=QDRANT_URL, 
        api_key=QDRANT_API_KEY,
        timeout=10
    )
    
    print("✅ Qdrant 연결 성공!")
    
    # 기존 컬렉션 목록 확인
    collections = client.get_collections()
    print(f"📂 기존 컬렉션 수: {len(collections.collections)}")
    
    for collection in collections.collections:
        print(f"  - {collection.name}")
        try:
            info = client.get_collection(collection.name)
            print(f"    벡터 차원: {info.config.params.vectors['vector'].size}")
            count = client.count(collection.name)
            print(f"    데이터 수: {count.count}")
        except Exception as e:
            print(f"    정보 확인 실패: {e}")
    
    print("\n" + "="*50)
    print("Qdrant 연결 테스트 완료")
    
except Exception as e:
    print(f"❌ Qdrant 연결 실패: {e}")
    print("환경 변수 QDRANT_API_KEY를 확인해주세요.")