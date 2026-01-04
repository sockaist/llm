# Deployment Guide (English)

How to deploy VectorDB v2.0 to production.

## Docker

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY . /app
RUN pip install .
ENV VECTORDB_ENV=production
CMD ["python", "-m", "vectordb", "server", "start", "--port", "8000"]
```

## Production Checklist

1.  [ ] **Security Tier**: Ensure `tier: 2` (MFA/Auth) enabled in `production.yaml`.
2.  [ ] **Secrets**: Inject `VECTORDB_API_KEY` via Environment Variables.
3.  [ ] **Database**: Connect to stable Qdrant cluster (not localhost).
4.  [ ] **Concurrency**: Tune `workers` count based on CPU cores.
