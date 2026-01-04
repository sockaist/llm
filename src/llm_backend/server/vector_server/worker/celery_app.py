# llm_backend/server/vector_server/worker/celery_app.py
import os
from celery import Celery
from celery.signals import after_setup_logger, after_setup_task_logger
from llm_backend.utils.logger import ColoredFormatter

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "vector_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["llm_backend.server.vector_server.worker.tasks"],
)




@after_setup_logger.connect
def setup_loggers(logger, *args, **kwargs):
    for handler in logger.handlers:
        handler.setFormatter(ColoredFormatter())


@after_setup_task_logger.connect
def setup_task_loggers(logger, *args, **kwargs):
    for handler in logger.handlers:
        handler.setFormatter(ColoredFormatter())


celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
    worker_hijack_root_logger=False,  # Allow custom logging configuration
    task_always_eager=os.getenv("CELERY_TASK_ALWAYS_EAGER", "False").lower() == "true",
)
