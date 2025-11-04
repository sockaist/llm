import os
import sys
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

# 프로젝트 루트 디렉토리를 파이썬 경로에 추가
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Google Gemini API 임포트
import google.generativeai as genai

# 프롬프트 템플릿과 출력 파서 임포트
from ..prompt import InstructionConfig
from ..output_parsers import JSONOutputParser
from ..chatbot import ChatBot

"""
class Tree_of_Thought:
    def():"
"""