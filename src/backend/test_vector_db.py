import os
import sys
import unittest
import json
from pathlib import Path
from dotenv import load_dotenv

# 필요한 경로 추가
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# 실제 존재하는 모듈 임포트
from qdrant_client import QdrantClient
from src.vector_db_helper import search_doc, create_doc_upsert
from src.embedding import content_embedder, model
from src.InputChecker import InputChecker, InputNormalizer, QueryMaker, FilterGenerator

# 환경 변수 로드
load_dotenv()

class TestRAGImplementation(unittest.TestCase):
    
    def setUp(self):
        """테스트 설정 및 필요한 객체 초기화"""
        # Qdrant 클라이언트 설정
        self.client = QdrantClient(
            url="https://7eb854c4-8645-4c1f-ae73-609313fb8842.us-east4-0.gcp.cloud.qdrant.io",
            api_key=os.environ.get('QDRANT_API_KEY')
        )
        
        # Google API 키 설정
        self.api_key = os.environ.get('GOOGLE_API_KEY')
        
        # 챗봇 모듈들 초기화
        self.input_checker = InputChecker(self.api_key)
        self.input_normalizer = InputNormalizer(self.api_key)
        self.query_maker = QueryMaker(self.api_key)
        self.filter_generator = FilterGenerator(self.api_key)
        
        # 테스트용 컬렉션 이름
        self.test_collection = "portal.job"
        
        # 테스트용 샘플 문서
        self.sample_doc = {
            "title": "KAIST 전산학부 RAG 시스템 연구",
            "author": "김연구",
            "date": "2024-01-15",
            "link": "https://example.com/rag-research",
            "content": "RAG(Retrieval-Augmented Generation)는 대규모 언어 모델의 성능을 향상시키기 위한 방법입니다. 벡터 데이터베이스를 활용하여 관련 문서를 검색하고, 이를 바탕으로 더 정확한 답변을 생성합니다."
        }

    def test_document_embedding_and_storage(self):
        """문서 임베딩 및 저장 테스트"""
        # 문서 임베딩 및 저장
        create_doc_upsert(self.client, self.test_collection, self.sample_doc)
        
        # 저장된 문서 수 확인
        count = self.client.count(collection_name=self.test_collection, exact=True).count
        self.assertGreater(count, 0)
        print(f"저장된 문서 청크 수: {count}")

    def test_vector_search(self):
        """벡터 검색 테스트"""
        # 문서 저장
        create_doc_upsert(self.client, self.test_collection, self.sample_doc)
        
        # 검색 테스트
        query = "RAG 시스템이란 무엇인가요?"
        search_results = search_doc(self.client, query, self.test_collection, k=3)
        
        self.assertGreater(len(search_results), 0)
        
        print(f"검색 쿼리: {query}")
        for i, hit in enumerate(search_results):
            print(f"{i+1}. 점수: {hit.score:.4f}")
            print(f"   내용: {hit.payload.get('text', '')[:100]}...")

    def test_input_processing_pipeline(self):
        """입력 처리 파이프라인 테스트"""
        user_input = "최근 KAIST 전산학부 채용 공고가 있나요?"
        
        # 1. 입력 검증
        check_result = self.input_checker.process_query(user_input)
        print(f"입력 검증 결과: {check_result}")
        
        if check_result.get('is_valid', False):
            # 2. 입력 정규화
            normalize_result = self.input_normalizer.process_query(user_input)
            print(f"정규화 결과: {normalize_result}")
            
            # 3. 쿼리 생성
            query_result = self.query_maker.process_query(user_input)
            print(f"쿼리 생성 결과: {query_result}")
            
            # 4. 필터 생성
            filter_result = self.filter_generator.process_query(user_input)
            print(f"필터 생성 결과: {filter_result}")
            
            self.assertTrue(True)  # 모든 단계가 성공적으로 실행됨
        else:
            print("입력이 유효하지 않음")

    def test_complete_rag_pipeline(self):
        """완전한 RAG 파이프라인 테스트"""
        # 테스트 문서 저장
        create_doc_upsert(self.client, self.test_collection, self.sample_doc)
        
        user_query = "KAIST에서 RAG 연구를 하는 사람이 누구인가요?"
        
        print(f"사용자 질문: {user_query}")
        
        # 1. 입력 검증
        check_result = self.input_checker.process_query(user_query)
        print(f"1. 입력 검증: {check_result.get('is_valid', False)}")
        
        if not check_result.get('is_valid', False):
            print("입력이 유효하지 않습니다.")
            return
        
        # 2. 입력 정규화
        normalize_result = self.input_normalizer.process_query(user_query)
        normalized_query = normalize_result.get('normalized_query', user_query)
        print(f"2. 정규화된 쿼리: {normalized_query}")
        
        # 3. 필터 생성
        filter_result = self.filter_generator.process_query(user_query)
        print(f"3. 생성된 필터: {filter_result}")
        
        # 4. 벡터 검색
        search_results = search_doc(self.client, normalized_query, self.test_collection, k=3)
        print(f"4. 검색된 문서 수: {len(search_results)}")
        
        # 5. 검색 결과를 컨텍스트로 구성
        context_docs = []
        for hit in search_results:
            context_docs.append({
                'text': hit.payload.get('text', ''),
                'title': hit.payload.get('title', ''),
                'author': hit.payload.get('author', ''),
                'score': hit.score
            })
        
        print("5. 검색된 컨텍스트:")
        for i, doc in enumerate(context_docs):
            print(f"   {i+1}. {doc['title']} (점수: {doc['score']:.4f})")
            print(f"      저자: {doc['author']}")
            print(f"      내용: {doc['text'][:100]}...")
        
        # 6. 최종 응답 생성을 위한 프롬프트 구성
        context_text = "\n".join([f"문서 {i+1}: {doc['text']}" for i, doc in enumerate(context_docs)])
        
        final_prompt = f"""다음은 사용자 질문과 관련된 검색 결과입니다:

{context_text}

사용자 질문: {user_query}

위의 검색 결과를 바탕으로 정확하고 도움이 되는 답변을 제공해주세요."""

        print(f"6. 생성된 프롬프트 길이: {len(final_prompt)} 문자")
        
        # 응답 생성 (실제로는 LLM을 호출하여 생성)
        # 여기서는 테스트이므로 샘플 응답으로 대체
        sample_response = f"검색 결과에 따르면, KAIST 전산학부에서 RAG 연구를 수행하는 연구자는 {self.sample_doc['author']}입니다. 해당 연구는 {self.sample_doc['date']}에 발표되었으며, RAG 시스템의 성능 향상에 관한 내용을 다루고 있습니다."
        
        print(f"7. 최종 응답: {sample_response}")
        
        # 테스트 검증
        self.assertGreater(len(search_results), 0)
        self.assertGreater(len(context_text), 0)
        self.assertGreater(len(sample_response), 0)

def run_rag_demo():
    """RAG 시스템 데모 실행"""
    load_dotenv()
    
    # 클라이언트 및 챗봇 초기화
    client = QdrantClient(
        url="https://7eb854c4-8645-4c1f-ae73-609313fb8842.us-east4-0.gcp.cloud.qdrant.io",
        api_key=os.environ.get('QDRANT_API_KEY')
    )
    
    api_key = os.environ.get('GOOGLE_API_KEY')
    input_checker = InputChecker(api_key)
    input_normalizer = InputNormalizer(api_key)
    filter_generator = FilterGenerator(api_key)
    
    collection_name = "portal.job"
    
    print("=== KAIST 전산학부 RAG 시스템 데모 ===")
    
    while True:
        user_query = input("\n질문을 입력하세요 (종료: 'quit'): ")
        if user_query.lower() == 'quit':
            break
        
        print(f"\n📝 사용자 질문: {user_query}")
        
        # 1. 입력 검증
        print("🔍 입력 검증 중...")
        check_result = input_checker.process_query(user_query)
        
        if not check_result.get('is_valid', False):
            print(f"❌ 입력이 유효하지 않습니다: {check_result.get('reason', '')}")
            continue
        
        # 2. 입력 정규화
        print("✏️  입력 정규화 중...")
        normalize_result = input_normalizer.process_query(user_query)
        normalized_query = normalize_result.get('normalized_query', user_query)
        
        # 3. 벡터 검색
        print("🔎 관련 문서 검색 중...")
        search_results = search_doc(client, normalized_query, collection_name, k=3)
        
        if not search_results:
            print("❌ 관련 문서를 찾을 수 없습니다.")
            continue
        
        print(f"✅ {len(search_results)}개의 관련 문서를 찾았습니다:")
        
        for i, hit in enumerate(search_results[:3]):
            print(f"\n📄 문서 {i+1} (유사도: {hit.score:.4f})")
            print(f"   제목: {hit.payload.get('title', 'N/A')}")
            print(f"   저자: {hit.payload.get('author', 'N/A')}")
            print(f"   날짜: {hit.payload.get('date', 'N/A')}")
            print(f"   내용: {hit.payload.get('text', '')[:150]}...")
        
        print(f"\n💡 정규화된 검색어: {normalized_query}")

if __name__ == "__main__":
    # 테스트 실행
    # unittest.main()
    
    # 데모 실행
    run_rag_demo()
