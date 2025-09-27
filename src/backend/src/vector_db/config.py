"""
Vector DB 설정 파일
순환 import 문제를 해결하기 위해 공통 상수들을 분리
"""

from qdrant_client.models import Distance
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# Qdrant 설정
QDRANT_API_KEY = os.environ.get('QDRANT_API_KEY')
QDRANT_URL = "https://897a4e03-5fcc-42a2-b3e2-ed5ab54fd160.us-west-1-0.aws.cloud.qdrant.io"

# 벡터 설정
DISTANCE = Distance.COSINE
THRESHOLD = 1.0  # clustering threshold
VECTOR_SIZE = 768  # ko-sroberta-multitask의 기본 차원

# 컬렉션 형식 정의
FORMATS = {
    "portal.job": ["title","author","date","link","content"], 
    "portal.startUp": ["title","author","date","link","content"], 
    "csweb.news": ["title","date","link","content"], 
    "csweb.canlender": ["title","date","link","content","location"], 
    "csweb.research": ["name","professor","field","web","email","phone","office","intro","etc"], 
    "csweb.edu": ["title","link","content"], 
    "csweb.ai": ["title","date","link","content"], 
    "csweb.profs": ["name","field","major","degree","web","mail","phone","office","etc"], 
    "csweb.admin": ["name","position","work","mail","phone","office","etc"],
    "csweb.refer": ["name","web","etc"], 
    # TODO: add formats for notion crawling data
}