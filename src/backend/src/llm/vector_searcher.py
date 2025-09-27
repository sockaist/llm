"""
Vector DB 검색 기능을 위한 모듈
"""

import sys
import os

# vector_db 모듈이 있는 경로를 추가
vector_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'vector_db'))
sys.path.insert(0, vector_db_path)

try:
    from vector_db_helper import search_doc
    from config import QDRANT_API_KEY, QDRANT_URL
    from qdrant_client import QdrantClient
except ImportError as e:
    print(f"Vector DB 모듈 import 실패: {e}")
    # 대안 설정
    QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
    QDRANT_URL = "https://897a4e03-5fcc-42a2-b3e2-ed5ab54fd160.us-west-1-0.aws.cloud.qdrant.io"
    
    try:
        from qdrant_client import QdrantClient
        # 간단한 search_doc 함수 구현
        def search_doc(client, query, collection, top_k):
            """Fallback search function"""
            try:
                from qdrant_client.models import NamedVector
                # 임시로 빈 벡터로 검색 (실제로는 embedding 필요)
                results = client.search(
                    collection_name=collection,
                    query_vector=NamedVector(name="vector", vector=[0]*768),
                    limit=top_k
                )
                return results
            except Exception:
                return []
    except ImportError:
        print("qdrant_client도 import 실패. Vector 검색 기능이 제한됩니다.")
        search_doc = None
        QdrantClient = None

import json
from typing import List, Dict, Any

class VectorSearcher:
    """Vector DB에서 유사한 정보를 검색하는 클래스"""
    
    def __init__(self):
        """
        Vector DB 클라이언트 초기화
        """
        self.client = None
        self.search_available = False
        
        try:
            if QdrantClient and QDRANT_API_KEY:
                self.client = QdrantClient(
                    url=QDRANT_URL,
                    api_key=QDRANT_API_KEY,
                    timeout=10
                )
                self.search_available = True
                print("✅ Vector DB 연결 성공")
            else:
                print("⚠️ Vector DB 설정이 없어 검색 기능이 비활성화됩니다.")
        except Exception as e:
            print(f"❌ Vector DB 연결 실패: {e}")
            self.client = None
            self.search_available = False
    
    def search_similar_documents(self, query: str, top_k: int = 30) -> List[Dict[str, Any]]:
        """
        쿼리와 유사한 문서들을 검색
        
        Args:
            query (str): 검색 쿼리
            top_k (int): 반환할 문서 수 (기본값: 30)
            
        Returns:
            List[Dict[str, Any]]: 검색된 문서들의 리스트
        """
        if not self.search_available or not self.client or not search_doc:
            print("⚠️ Vector DB 검색을 사용할 수 없습니다.")
            return []
        
        try:
            all_results = []
            
            # 여러 컬렉션에서 검색
            collections = [
                "csweb.news", "csweb.ai", "csweb.admin", "csweb.profs", 
                "portal.job", "portal.startUp"
            ]
            
            for collection in collections:
                try:
                    results = search_doc(self.client, query, collection, top_k // len(collections) + 5)
                    
                    for result in results:
                        doc_info = {
                            "content": result.payload.get("text", ""),
                            "score": result.score,
                            "collection": collection,
                            "metadata": {
                                "title": result.payload.get("title", ""),
                                "date": result.payload.get("date", ""),
                                "link": result.payload.get("link", ""),
                                "author": result.payload.get("author", ""),
                                "name": result.payload.get("name", ""),
                                "position": result.payload.get("position", ""),
                                "field": result.payload.get("field", "")
                            }
                        }
                        all_results.append(doc_info)
                        
                except Exception as e:
                    print(f"컬렉션 {collection} 검색 중 오류: {e}")
                    continue
            
            # 점수 기준으로 정렬하고 상위 top_k개 반환
            all_results.sort(key=lambda x: x["score"], reverse=True)
            return all_results[:top_k]
            
        except Exception as e:
            print(f"검색 중 오류 발생: {e}")
            return []
    
    def format_search_results(self, results: List[Dict[str, Any]]) -> str:
        """
        검색 결과를 문자열로 포맷팅
        
        Args:
            results (List[Dict[str, Any]]): 검색 결과
            
        Returns:
            str: 포맷팅된 검색 결과
        """
        if not results:
            return "관련 정보를 찾을 수 없습니다."
        
        formatted_text = "=== 관련 정보 ===\n\n"
        
        for i, result in enumerate(results, 1):
            formatted_text += f"[정보 {i}]\n"
            
            # 메타데이터 추가
            metadata = result["metadata"]
            if metadata.get("title"):
                formatted_text += f"제목: {metadata['title']}\n"
            if metadata.get("author"):
                formatted_text += f"작성자: {metadata['author']}\n"
            if metadata.get("name"):
                formatted_text += f"이름: {metadata['name']}\n"
            if metadata.get("position"):
                formatted_text += f"직책: {metadata['position']}\n"
            if metadata.get("field"):
                formatted_text += f"분야: {metadata['field']}\n"
            if metadata.get("date"):
                formatted_text += f"날짜: {metadata['date']}\n"
            if metadata.get("link"):
                formatted_text += f"링크: {metadata['link']}\n"
            
            # 내용 추가
            content = result["content"]
            if len(content) > 300:
                content = content[:300] + "..."
            formatted_text += f"내용: {content}\n"
            formatted_text += f"유사도 점수: {result['score']:.4f}\n"
            formatted_text += f"출처: {result['collection']}\n"
            formatted_text += "-" * 50 + "\n\n"
        
        return formatted_text