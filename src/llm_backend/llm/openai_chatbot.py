"""
OpenAI 기반 ChatBot 구현
"""

import openai
import json
from typing import Dict, Any, List, Optional
from ..vectorstore.vector_searcher import VectorSearcher

class OpenAIChatBot:
    """OpenAI API를 사용하는 ChatBot 클래스"""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """
        OpenAI ChatBot 초기화
        
        Args:
            api_key (str): OpenAI API 키
            model (str): 사용할 모델 (기본값: gpt-4o-mini)
        """
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        self.vector_searcher = VectorSearcher()
        
        # 시스템 프롬프트 설정
        self.system_prompt = """
당신은 KAIST 전산학부 집행위원회에서 개발한 학생 지원 챗봇입니다.

주요 역할:
1. 전산학부 학사 과정 및 교과 과정 정보 제공
2. 전산학부 행사 및 프로그램 안내  
3. 전산학부 내 학생 지원 시스템 정보 제공
4. 전산학부 관련 자주 묻는 질문 답변
5. 학교와 관련한 일반적인 질문 답변

응답 가이드라인:
- 친근하고 도움이 되는 톤으로 답변하세요
- 정확한 정보를 제공하되, 확실하지 않은 경우 그렇다고 명시하세요
- 제공된 관련 정보를 최대한 활용하여 구체적으로 답변하세요
- 링크가 있는 경우 함께 제공하세요
- 한국어로 답변하세요
"""
        
    def generate_response(self, user_query: str, use_vector_search: bool = True) -> str:
        """
        사용자 쿼리에 대한 응답 생성
        
        Args:
            user_query (str): 사용자 질문
            use_vector_search (bool): Vector DB 검색 사용 여부
            
        Returns:
            str: 생성된 응답
        """
        try:
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Vector DB에서 관련 정보 검색
            if use_vector_search:
                search_results = self.vector_searcher.search_similar_documents(user_query, top_k=30)
                
                if search_results:
                    # 관련 정보를 컨텍스트로 추가
                    context = self.vector_searcher.format_search_results(search_results)
                    
                    context_message = f"""
다음은 사용자 질문과 관련된 KAIST 전산학부 정보입니다. 이 정보를 참고하여 답변해주세요:

{context}

사용자 질문: {user_query}

위의 관련 정보를 바탕으로 사용자의 질문에 정확하고 도움이 되는 답변을 제공해주세요. 
정보에 링크가 포함되어 있다면 함께 제공해주세요.
"""
                    messages.append({"role": "user", "content": context_message})
                else:
                    messages.append({"role": "user", "content": user_query})
            else:
                messages.append({"role": "user", "content": user_query})
            
            # OpenAI API 호출
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2048
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"죄송합니다. 응답 생성 중 오류가 발생했습니다: {str(e)}"
    
    def generate_response_with_context(self, user_query: str, additional_context: str = "") -> str:
        """
        추가 컨텍스트와 함께 응답 생성
        
        Args:
            user_query (str): 사용자 질문
            additional_context (str): 추가 컨텍스트
            
        Returns:
            str: 생성된 응답
        """
        try:
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Vector DB에서 관련 정보 검색
            search_results = self.vector_searcher.search_similar_documents(user_query, top_k=30)
            
            full_context = ""
            if search_results:
                db_context = self.vector_searcher.format_search_results(search_results)
                full_context += f"데이터베이스 정보:\n{db_context}\n\n"
            
            if additional_context:
                full_context += f"추가 정보:\n{additional_context}\n\n"
            
            if full_context:
                context_message = f"""
다음은 사용자 질문과 관련된 정보입니다:

{full_context}

사용자 질문: {user_query}

위의 정보를 바탕으로 정확하고 도움이 되는 답변을 제공해주세요.
"""
                messages.append({"role": "user", "content": context_message})
            else:
                messages.append({"role": "user", "content": user_query})
            
            # OpenAI API 호출
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2048
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"죄송합니다. 응답 생성 중 오류가 발생했습니다: {str(e)}"