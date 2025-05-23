# 챗봇 프로젝트

## 소개
이 프로젝트는 Google Gemini API를 활용한 챗봇 시스템입니다.

## 설치 방법

### 필수 요구사항
- Python 3.9 이상
- pip 또는 conda

### 가상 환경 설정

#### Conda 사용 시
```bash
conda env create -f environment.yml
conda activate socchatbot_env
```

#### Pip 사용 시
```bash
python -m venv venv
source venv/bin/activate  # macOS, Linux
# venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 환경 변수 설정
`.env.example` 파일을 복사하여 `.env` 파일을 만들고 필요한 환경 변수를 설정합니다:
```bash
cp .env.example .env
```
그런 다음 `.env` 파일을 편집하여 `GOOGLE_API_KEY` 등을 설정합니다.

## 실행 방법
프로젝트 루트 디렉토리에서 다음 명령어를 실행합니다:
```bash
python start.py
```

## 프로젝트 구조
- `src/backend/`: 백엔드 코드
  - `src/llm/`: LLM 관련 코드
  - `src/utils/`: 유틸리티 모듈
- `src/frontend/`: 프론트엔드 코드
- `src/crawler/`: 크롤러 코드
- `src/parser/`: 파서 코드
- `data/`: 데이터 파일
- `qdrant_data/`: Qdrant 벡터 데이터베이스 파일
