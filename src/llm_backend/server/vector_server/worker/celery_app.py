# llm_backend/server/vector_server/worker/celery_app.py
import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "vector_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["llm_backend.server.vector_server.worker.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
)
