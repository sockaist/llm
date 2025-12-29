"""Vector DB 설정 (YAML 기본값 + 환경변수 override).

우선순위: 환경변수 > YAML > 코드 기본값
- YAML 경로: VECTOR_CONFIG_PATH (기본 ./config/vectorstore.yaml)
- 주요 키:
  qdrant.url, qdrant.api_key
  paths.bm25_path, paths.snapshot_dir
"""

from qdrant_client.models import Distance
import os
import yaml
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()


def _load_yaml(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fp:
            return yaml.safe_load(fp) or {}
    except Exception:
        return {}


def _cfg_lookup(cfg: dict, path: str, default):
    cur = cfg
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur if cur is not None else default


def _to_int(val, default: int) -> int:
    try:
        return int(val)
    except Exception:
        return default


def _to_float(val, default: float) -> float:
    try:
        return float(val)
    except Exception:
        return default


CONFIG_PATH = os.environ.get("VECTOR_CONFIG_PATH", "./config/vectorstore.yaml")
_yaml_cfg = _load_yaml(CONFIG_PATH)

# Qdrant 설정 (환경변수 → YAML → 기본값)
QDRANT_URL = os.environ.get(
    "QDRANT_URL",
    _cfg_lookup(_yaml_cfg, "qdrant.url", "http://localhost:6333"),
)
QDRANT_API_KEY = os.environ.get(
    "QDRANT_API_KEY",
    _cfg_lookup(_yaml_cfg, "qdrant.api_key", None),
)

# 경로 설정 (환경변수 → YAML → 기본값)
BM25_PATH = os.environ.get(
    "BM25_PATH",
    _cfg_lookup(_yaml_cfg, "paths.bm25_path", "./models/bm25_vectorizer.pkl"),
)
SNAPSHOT_DIR = os.environ.get(
    "SNAPSHOT_DIR",
    _cfg_lookup(_yaml_cfg, "paths.snapshot_dir", "./snapshots"),
)

# SPLADE 설정
SPLADE_MODEL_NAME = os.environ.get(
    "SPLADE_MODEL_NAME",
    _cfg_lookup(_yaml_cfg, "splade.model_name", "yjoonjang/splade-ko-v1"),
)
SPLADE_MAX_LENGTH = _to_int(
    os.environ.get("SPLADE_MAX_LENGTH", None)
    or _cfg_lookup(_yaml_cfg, "splade.max_length", 256),
    256,
)
SPLADE_THRESHOLD = _to_float(
    os.environ.get("SPLADE_THRESHOLD", None)
    or _cfg_lookup(_yaml_cfg, "splade.threshold", 0.01),
    0.01,
)
SPLADE_DEVICE = os.environ.get(
    "SPLADE_DEVICE",
    _cfg_lookup(_yaml_cfg, "splade.device", "cpu"),
)
SPLADE_TOP_K = _to_int(
    os.environ.get("SPLADE_TOP_K", None)
    or _cfg_lookup(_yaml_cfg, "splade.top_k", 2000),
    2000,
)

# 벡터 설정
DISTANCE = Distance.COSINE
THRESHOLD = 1.0  # clustering threshold
VECTOR_SIZE = 768  # ko-sroberta-multitask의 기본 차원

# 컬렉션 형식 정의
FORMATS = {
    "portal.job": ["title","author","date","link","content","id"], 
    "portal.startUp": ["title","author","date","link","content","id"],
    "csweb.news": ["title","date","link","content","id"],
    "csweb.calendar": ["title","date","link","content","location","id"],
    "csweb.research": ["name","professor","field","web","email","phone","office","intro","etc","id"], 
    "csweb.edu": ["title","link","content","id"], 
    "csweb.ai": ["title","date","link","content","id"], 
    "csweb.profs": ["name","field","major","degree","web","mail","phone","office","etc","id"], 
    "csweb.admin": ["name","position","work","mail","phone","office","etc","id"],
    "csweb.refer": ["name","web","etc","id"], 
    "notion.marketing" : ["title","date","start","finish","contents","images","url","id"],
    "notion.notice" : ["title","date","start","finish","contents","images","url","id"]
    # "drive" : ["date","link","content","id"] # for pdf, word files uploaded from drive
}