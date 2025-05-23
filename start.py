#!/usr/bin/env python3
"""
챗봇 시작 스크립트
"""
import os
import sys
from dotenv import load_dotenv

# 프로젝트 루트 디렉토리 경로 추가
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.append(project_root)

# 환경 변수 로드
load_dotenv()

# 백엔드 모듈 임포트
from src.backend.main import main

if __name__ == "__main__":
    main()
