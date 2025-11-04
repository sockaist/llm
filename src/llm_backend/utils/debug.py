# src/llm_backend/utils/debug.py
"""
개발용 디버깅 유틸리티
--------------------------------
- trace(msg): 현재 호출 위치와 함께 DEBUG 로그 출력
- @trace_in: 함수 진입/종료 자동 로그
- with profile("task_name"): 코드 블록 실행 시간 측정
"""

import inspect
import time
import functools
from contextlib import contextmanager
from llm_backend.utils.logger import logger, APP_MODE


def trace(msg: str):
    """
    호출 위치(파일명, 줄번호, 함수명)와 함께 메시지를 DEBUG 레벨로 출력.
    개발 모드(APP_MODE=dev)일 때만 활성화.
    """
    if APP_MODE != "dev":
        return

    frame = inspect.stack()[1]
    filename = frame.filename.split("/")[-1]
    lineno = frame.lineno
    func = frame.function
    timestamp = time.strftime("%H:%M:%S", time.localtime())

    logger.debug(
        f"[TRACE {timestamp}] {msg} | {filename}:{lineno} ({func}) @ {time.time():.2f}"
    )


def trace_in(func):
    """
    함수의 진입과 종료를 자동으로 trace하는 데코레이터.
    예시:
        @trace_in
        def foo(): ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if APP_MODE == "dev":
            trace(f"Entering {func.__name__}")
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end = time.perf_counter()
            if APP_MODE == "dev":
                trace(f"Exiting {func.__name__} (elapsed: {end - start:.4f}s)")
    return wrapper


@contextmanager
def profile(name: str):
    """
    특정 코드 블록의 실행 시간을 측정하는 context manager.
    예시:
        with profile("BM25 fitting"):
            bm25_fit(docs)
    """
    if APP_MODE != "dev":
        yield
        return

    trace(f"⏱ Start {name}")
    start = time.perf_counter()
    try:
        yield
    finally:
        end = time.perf_counter()
        trace(f"End {name} (elapsed: {end - start:.4f}s)")