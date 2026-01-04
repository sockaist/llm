#!/usr/bin/env python3
"""
KAIST 전산학부 ChatBot 서버 실행 스크립트
"""

import os
import sys
import uvicorn
from pathlib import Path
from dotenv import load_dotenv

# 현재 파일의 디렉토리를 기준으로 경로 설정
current_dir = Path(__file__).parent
backend_dir = current_dir / "src" / "backend"

# Python 경로에 백엔드 디렉토리 추가
sys.path.insert(0, str(backend_dir))

load_dotenv()

def main():
    """서버 실행 메인 함수"""
    try:
        print("[INFO] KAIST 전산학부 ChatBot 서버를 시작합니다...")
        print(f"📂 작업 디렉토리: {current_dir}")
        print(f"📂 백엔드 디렉토리: {backend_dir}")
        
        # 환경 변수 확인
        if not os.getenv("OPENAI_API_KEY"):
            print("[FAIL] OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
            print("[TIP] .env 파일에 OPENAI_API_KEY=your_api_key를 추가하세요.")
            return
            
        # FastAPI 서버 실행
        uvicorn.run(
            "src.server.server:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
        
    except Exception as e:
        print(f"[FAIL] 서버 실행 실패: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()