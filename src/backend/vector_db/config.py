"""
PostgreSQL + pgvector 설정 파일
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Always load project-root `.env` first, then allow ambient env overrides.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv()

# PostgreSQL 설정
# POSTGRES_DSN 우선, 없으면 DATABASE_URL 사용
POSTGRES_DSN = os.environ.get("POSTGRES_DSN") or os.environ.get("DATABASE_URL")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.environ.get("POSTGRES_DB", "postgres")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "")
PGVECTOR_TABLE = os.environ.get("PGVECTOR_TABLE", "documents")

# 임베딩 설정
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_EMBEDDING_MODEL = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
VECTOR_SIZE = int(os.environ.get("OPENAI_EMBEDDING_DIM", "1536"))
CHUNK_SIZE = int(os.environ.get("EMBEDDING_CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.environ.get("EMBEDDING_CHUNK_OVERLAP", "120"))

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
    "notion.marketing" : ["title","date","start","finish","content","images","url","id"],
    "notion.notice" : ["title","date","start","finish","content","images","url","id"],
    "drive" : ["date","link","content","id"] # for pdf, word files uploaded from drive
}
