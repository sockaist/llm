"""
OpenAI 기반 ChatBot 구현
"""

import openai
import json
import os
from datetime import date
from typing import Dict, Any, List, Optional
from .vector_searcher import VectorSearcher
import time

class OpenAIChatBot:
    """OpenAI API를 사용하는 ChatBot 클래스"""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4.1",
        vector_searcher: Optional[VectorSearcher] = None,
    ):
        """
        OpenAI ChatBot 초기화
        
        Args:
            api_key (str): OpenAI API 키
            model (str): 사용할 모델 (기본값: gpt-4.1)
            vector_searcher (Optional[VectorSearcher]): 기존 검색기 인스턴스(선택)
        """
        self.client = openai.OpenAI(api_key=api_key)
        self.model = os.getenv("HIERARCHY_TOP_MODEL", model)
        # 서비스에서 생성한 인스턴스를 재사용해 중복 초기화를 방지한다.
        self.vector_searcher = vector_searcher or VectorSearcher()
        
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
- 정보성 질문에는 가능한 한 자세하고 구조적으로 답변하세요(핵심 요약 + 세부 항목).
- 최우선 원칙: 사용자 질문과 직접 관련된 내용만 답변하세요.
- 질문과 무관한 배경지식, 일반론, 주변 주제는 포함하지 마세요.
- 링크가 있는 경우 함께 제공하세요
- 한국어로 답변하세요
"""
        
    def generate_response(
        self,
        user_query: str,
        use_vector_search: bool = True,
        start_date: date | None = None,
        end_date: date | None = None,
        search_keywords: Optional[List[str]] = None,
        sql_context: Optional[str] = None,
        vector_context: Optional[str] = None,
        current_date_text: Optional[str] = None,
    ) -> str:
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
            retrieval_debug: Dict[str, Any] = {
                "use_vector_search": use_vector_search,
                "search_available": bool(getattr(self.vector_searcher, "search_available", False)),
                "search_keywords": search_keywords or [],
                "search_result_count": 0,
                "sql_context_present": bool(sql_context),
                "vector_context_provided": bool(vector_context),
                "context_attached": False,
            }
            
            # Vector DB에서 관련 정보 검색
            generated_vector_context = ""
            if vector_context:
                generated_vector_context = vector_context
            elif use_vector_search:
                search_results = self.vector_searcher.search_with_keywords(
                    user_query,
                    keywords=search_keywords,
                    top_k=30,
                    start_date=start_date,
                    end_date=end_date,
                )
                retrieval_debug["search_result_count"] = len(search_results)
                
                if search_results:
                    # 관련 정보를 컨텍스트로 추가
                    generated_vector_context = self.vector_searcher.format_search_results(search_results)

            filter_info = ""
            if start_date or end_date:
                filter_info = f"\n적용된 날짜 필터: {start_date} ~ {end_date}\n"
            keyword_info = ""
            if search_keywords:
                keyword_info = f"\n적용된 검색 키워드: {', '.join(search_keywords)}\n"

            context_sections: List[str] = []
            if sql_context:
                context_sections.append(
                    "=== SQL 구조화 검색 결과 ===\n"
                    f"{sql_context}"
                )
            if generated_vector_context:
                context_sections.append(
                    "=== 벡터 검색 결과 ===\n"
                    f"{generated_vector_context}"
                )

            if context_sections:
                context_body = "\n\n".join(context_sections)
                date_rule = ""
                if current_date_text:
                    date_rule = (
                        f"\n현재 기준 날짜(Asia/Seoul): {current_date_text}\n"
                        "시간 표현(오늘/최근/지난달 등)은 반드시 위 날짜를 기준으로 해석하세요.\n"
                    )
                context_message = f"""
다음은 사용자 질문과 관련된 KAIST 전산학부 정보입니다. 반드시 모든 정보를 함께 참고하여 답변해주세요.

{context_body}
{filter_info}
{keyword_info}
{date_rule}

[최우선 질의]
{user_query}

중요 규칙:
1) 위 [최우선 질의]에 직접적으로 필요한 정보만 답변하세요.
2) 질의와 무관한 정보, 일반적인 배경 설명, 확장 주제는 포함하지 마세요.
3) 답변의 모든 항목은 질의와의 관련성을 한 번 더 확인한 뒤 포함하세요.

위 제공 문서 컨텍스트를 종합해 정확하고 도움이 되는 답변을 제공해주세요.
정보에 링크가 포함되어 있다면 반드시 함께 제공해주세요.
질문이 정보 탐색형이면 핵심 요약 뒤에 세부 항목을 충분히 자세히 설명해주세요.
"""
                messages.append({"role": "user", "content": context_message})
                retrieval_debug["context_attached"] = True
                retrieval_debug["vector_context_attached"] = bool(generated_vector_context)
                retrieval_debug["sql_context_attached"] = bool(sql_context)
            else:
                messages.append({"role": "user", "content": user_query})
            
            # OpenAI API 호출 직전 최종 프롬프트/요청 payload 디버그 로그
            self._log_final_request(
                messages=messages,
                temperature=0.7,
                max_tokens=None,
                call_site="generate_response",
                retrieval_debug=retrieval_debug,
            )

            # OpenAI API 호출
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
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
            retrieval_debug: Dict[str, Any] = {
                "use_vector_search": True,
                "search_available": bool(getattr(self.vector_searcher, "search_available", False)),
                "search_result_count": 0,
                "context_attached": False,
            }
            
            # Vector DB에서 관련 정보 검색
            search_results = self.vector_searcher.search_similar_documents(user_query, top_k=30)
            retrieval_debug["search_result_count"] = len(search_results)
            
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

[최우선 질의]
{user_query}

중요 규칙:
1) [최우선 질의]에 직접 관련된 내용만 답변하세요.
2) 질의와 무관한 정보는 포함하지 마세요.
3) 위 정보와 오늘의 날짜가 {time.strftime("%Y-%m-%d")}를 바탕으로 답하세요.
"""
                messages.append({"role": "user", "content": context_message})
                retrieval_debug["context_attached"] = True
            else:
                messages.append({"role": "user", "content": user_query})
            
            # OpenAI API 호출 직전 최종 프롬프트/요청 payload 디버그 로그
            self._log_final_request(
                messages=messages,
                temperature=0.7,
                max_tokens=None,
                call_site="generate_response_with_context",
                retrieval_debug=retrieval_debug,
            )

            # OpenAI API 호출
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"죄송합니다. 응답 생성 중 오류가 발생했습니다: {str(e)}"

    def _log_final_request(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: Optional[int],
        call_site: str,
        retrieval_debug: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        OpenAI API로 보내기 직전의 최종 요청 payload를 디버그 로그로 출력한다.
        DEBUG_OPENAI_FINAL_PROMPT=1 일 때만 출력한다.
        """
        if os.getenv("DEBUG_OPENAI_FINAL_PROMPT") != "1":
            return

        payload = {
            "call_site": call_site,
            "model": self.model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if retrieval_debug is not None:
            payload["retrieval_debug"] = retrieval_debug
        print("=== DEBUG_OPENAI_FINAL_PROMPT ===")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        print("=== /DEBUG_OPENAI_FINAL_PROMPT ===")
