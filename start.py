#!/usr/bin/env python3
"""Vector 서버 구동 스크립트."""

import os
import sys

import uvicorn
from dotenv import load_dotenv


# 프로젝트 루트 디렉토리를 PYTHONPATH에 추가
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)


def main():
    """FastAPI Vector 서버를 uvicorn으로 실행한다."""

    load_dotenv()

    host = os.getenv("VECTOR_HOST", "0.0.0.0")
    port = int(os.getenv("VECTOR_PORT", "8000"))
    reload = os.getenv("UVICORN_RELOAD", "0") == "1"

    # 모듈 경로 문자열을 사용해 지연 임포트 및 CLI 실행을 단순화
    uvicorn.run(
        "src.llm_backend.server.vector_server.main:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
