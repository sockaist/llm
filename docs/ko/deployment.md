# Deployment Guide (Korean)

VectorDB v2.0을 프로덕션 환경에 배포하는 방법입니다.

## Docker 배포

공식 Docker 이미지를 사용하거나 직접 빌드할 수 있습니다.

### Dockerfile 예시
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY . /app
RUN pip install .

ENV VECTORDB_ENV=production
CMD ["python", "-m", "vectordb", "server", "start", "--port", "8000"]
```

## Kubernetes 배포

Kubernetes Deployment YAML 예시:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vectordb
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: vectordb
        image: my-vectordb:latest
        env:
        - name: VECTORDB_API_KEY
          valueFrom:
            secretKeyRef:
              name: vectordb-secrets
              key: api-key
```

## 프로덕션 체크리스트

1.  [ ] **보안 티어 설정**: `production.yaml`에서 `tier: 2` 이상 확인.
2.  [ ] **API Key**: `.env` 또는 K8s Secret으로 마스터 키 주입.
3.  [ ] **Qdrant 연결**: 외장 Qdrant 클러스터 주소 설정 (`VECTORDB_HOST`).
4.  [ ] **Workers**: CPU 코어 수에 맞춰 `workers` 개수 조정.
