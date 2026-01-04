# VectorDB 사용자 가이드 (Korean)

VectorDB v2.0은 개발자 친화적인 **Universal Vector Database Solution**입니다.
복잡한 설정 없이 어떤 JSON 데이터든 벡터화하여 검색할 수 있습니다.

## 목차

1.  [시작하기 (Getting Started)](getting_started.md)
    -   설치 및 기본 설정
    -   서버 실행 방법
2.  [핵심 개념 (Key Concepts)](concepts.md)
    -   Universal JSON Handler (자동 평탄화)
    -   설정 시스템 (Unified Config)
3.  [Python SDK (개발자 가이드)](sdk_reference.md)
    -   `VectorDBClient` 사용법
    -   Sync/Async 클라이언트
    -   검색 및 업로드 예제
4.  [CLI 참조 (Command Line Interface)](cli_reference.md)
    -   `server start`
    -   `config show`
5.  [배포 및 운영 (Deployment)](deployment.md)
    -   Docker / Kubernetes
    -   프로덕션 환경 설정

## 빠른 시작

```bash
# 1. 설치
pip install vectordb

# 2. 서버 실행
python -m vectordb server start --port 8000

# 3. Python에서 사용
from vectordb.client import VectorDBClient
client = VectorDBClient()
client.search("인공지능 트렌드")
```
