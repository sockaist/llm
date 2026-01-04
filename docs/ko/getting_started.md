# 시작하기 (Getting Started) (Korean)

이 문서는 VectorDB v2.0 설치부터 기본 사용법까지 안내합니다.

## 1. 요구 사항
- Python 3.8 이상
- Qdrant (Docker로 실행 권장)

```bash
docker run -p 6333:6333 qdrant/qdrant
```

## 2. 설치

```bash
pip install -r requirements.txt
# 또는 패키지 형태로
pip install .
```

## 3. 서버 실행

CLI를 사용하여 간편하게 서버를 실행할 수 있습니다.

```bash
# 개발 모드 실행 (Debug 로그)
python -m vectordb server start --env development

# 프로덕션 모드 실행 (포트 9090)
python -m vectordb server start --env production --port 9090
```

## 4. 설정 확인

현재 적용된 설정을 확인하려면 다음 명령어를 사용하세요.

```bash
python -m vectordb config show --env development
```

출력 예시:
```json
{
  "server": {
    "host": "127.0.0.1",
    "port": 8000
  },
  "vectordb": {
    "engine": "qdrant"
  }
}
```
