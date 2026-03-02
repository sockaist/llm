"""
FastAPI용 Pydantic 모델 정의
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ChatRequest(BaseModel):
    """채팅 요청 모델"""
    message: str = Field(..., min_length=1, max_length=1000, description="사용자 질문")
    use_vector_search: Optional[bool] = Field(True, description="Vector DB 검색 사용 여부")


class ChatResponse(BaseModel):
    """채팅 응답 모델"""
    response: str = Field(..., description="챗봇 응답")
    success: bool = Field(..., description="성공 여부")
    message: Optional[str] = Field(None, description="상태 메시지")


class HealthResponse(BaseModel):
    """헬스체크 응답 모델"""
    status: str = Field(..., description="서버 상태")
    message: str = Field(..., description="상태 메시지")
    components: Dict[str, str] = Field(..., description="각 컴포넌트 상태")


class ErrorResponse(BaseModel):
    """에러 응답 모델"""
    error: str = Field(..., description="에러 메시지")
    detail: Optional[str] = Field(None, description="에러 상세 정보")
    success: bool = Field(False, description="성공 여부")