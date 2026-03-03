"""
KAIST 전산학부 ChatBot FastAPI 서버
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import logging
from typing import Dict, Any

from .models import ChatRequest, ChatResponse, HealthResponse, ErrorResponse
from .chatbot_service import get_chatbot_service, ChatBotService

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 라이프사이클 관리
    서버 시작시 ChatBot 서비스 초기화
    """
    logger.info("🚀 서버 시작 - ChatBot 서비스 초기화 중...")
    try:
        # ChatBot 서비스 초기화 (전역 인스턴스 생성)
        service = get_chatbot_service()
        logger.info("✅ ChatBot 서비스 초기화 완료!")
        yield
    except Exception as e:
        logger.error(f"❌ 서버 시작 실패: {e}")
        raise e
    finally:
        logger.info("🛑 서버 종료")


# FastAPI 앱 생성
app = FastAPI(
    title="KAIST 전산학부 ChatBot API",
    description="KAIST 전산학부 학생 지원 ChatBot의 REST API 서버",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=Dict[str, str])
async def root():
    """루트 엔드포인트"""
    return {
        "message": "KAIST 전산학부 ChatBot API 서버",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check(service: ChatBotService = Depends(get_chatbot_service)):
    """
    헬스체크 엔드포인트
    서비스 상태 확인
    """
    try:
        components = service.get_health_status()
        all_healthy = all(status in {"healthy", "disabled"} for status in components.values())
        
        return HealthResponse(
            status="healthy" if all_healthy else "unhealthy",
            message="모든 서비스가 정상 작동 중입니다." if all_healthy else "일부 서비스에 문제가 있습니다.",
            components=components
        )
    except Exception as e:
        logger.error(f"헬스체크 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"헬스체크 실패: {str(e)}"
        )


@app.get("/info", response_model=Dict[str, Any])
async def api_info():
    """API 정보 엔드포인트"""
    return {
        "name": "KAIST 전산학부 ChatBot API",
        "version": "1.0.0",
        "description": "KAIST 전산학부 학생 지원 챗봇 API",
        "endpoints": {
            "GET /": "루트 엔드포인트",
            "GET /health": "서비스 헬스체크",
            "GET /info": "API 정보 조회",
            "GET /ontology": "온톨로지 계층 조회",
            "POST /chat": "채팅 응답 생성",
        },
    }


@app.get("/ontology", response_model=Dict[str, Any])
async def ontology(service: ChatBotService = Depends(get_chatbot_service)):
    """
    온톨로지 계층 조회 엔드포인트
    """
    try:
        return service.get_ontology_tree()
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"온톨로지 조회 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"온톨로지 조회 중 오류 발생: {str(e)}",
        )


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: ChatBotService = Depends(get_chatbot_service)
):
    """
    채팅 엔드포인트
    사용자 질문에 대한 ChatBot 응답 제공
    """
    try:
        logger.info(f"채팅 요청 수신: {request.message[:100]}...")
        
        result = service.process_message(
            user_input=request.message,
            use_vector_search=request.use_vector_search
        )
        
        if result["success"]:
            logger.info("채팅 응답 생성 완료")
            return ChatResponse(
                response=result["response"],
                success=True,
                message=result.get("message", "응답 생성 완료")
            )
        else:
            logger.warning(f"채팅 처리 실패: {result.get('error', 'Unknown error')}")
            return ChatResponse(
                response=result["response"],
                success=False,
                message=result.get("error", "처리 실패")
            )
            
    except Exception as e:
        logger.error(f"채팅 엔드포인트 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"채팅 처리 중 오류 발생: {str(e)}"
        )


# 예외 처리 핸들러
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """전역 예외 처리"""
    logger.error(f"예상치 못한 오류: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "서버 내부 오류가 발생했습니다."},
    )


if __name__ == "__main__":
    # 개발 서버 실행
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
