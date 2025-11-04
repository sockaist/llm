import os
from openai import OpenAI
from llm_backend.vectorstore.vector_db_manager import VectorDBManager

# --- 1. 벡터 DB 초기화 ---
mgr = VectorDBManager(default_collection="notion.marketing")
mgr.fit_bm25_from_json_folder("./data")

# --- 2. 검색 쿼리 ---
query_text = "시스템 관련 교수님들이 전산학부에 있을까?"
retrieved_docs = mgr.query(query_text, top_k=15, collections=["notion.marketing"])

# --- 3. 상위 문서 내용 병합 ---
context = "\n\n".join(
    f"제목: {d.get('title', '(제목 없음)')}\n내용: {d.get('text', '')}"
    for d in retrieved_docs
)

# --- 4. LLM 초기화 ---
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY 환경변수가 설정되어 있지 않습니다!")

client = OpenAI(api_key=api_key)

# --- 5. LLM에 질의 (RAG 방식) ---
prompt = f"""
당신은 신뢰도 높은 지식 요약 어시스턴트입니다.
아래는 notion 데이터베이스에서 검색된 관련 문서들입니다.

=========================
{context}
=========================

각 문서에는 제목(title)이 포함되어 있습니다.
"{query_text}"에 대한 답변을 한 문단으로 작성하되,
- 반드시 답변의 끝부분에 참고한 문서 제목을 괄호 안에 인용 형태로 표시하세요.
- 여러 문서를 참고했다면 (예: "출처: 제목1, 제목2")처럼 쉼표로 구분하세요.
- 문서 제목이 비어 있으면 "출처 미상"으로 표기하세요.

출력 형식 예시:
요약된 답변 문장들... (출처: LG AI연구원 학부생 체험형 인턴 채용, AIM Intelligence AI 인턴십 1기 모집)
"""

response = client.chat.completions.create(
    model="gpt-4o-mini",  # or "gpt-4o"
    messages=[{"role": "user", "content": prompt}],
    temperature=0.3
)

print("\n--- RAG 결과 ---")
print(response.choices[0].message.content)