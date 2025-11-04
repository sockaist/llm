"""
OpenAI 기반 필터 생성 모듈
사용자의 질문에서 기간(start_date, end_date)과 filter_words를 추출
"""

import openai
import json
import os
import traceback
import datetime
from typing import Dict, Any
from llm_backend.utils.logger import logger, info, debug, error
from llm_backend.utils.debug import trace, trace_in


class OpenAIFilterGenerator:
    """OpenAI API를 사용한 검색 필터 생성 클래스"""

    @trace_in
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        config_path: str = None,
        strict: bool = True
    ):
        """
        OpenAI 필터 생성기 초기화
        """
        try:
            self.client = openai.OpenAI(api_key=api_key)
            self.model = model
            self.strict = strict

            # config 경로를 상대경로로 지정
            if config_path is None:
                base_dir = os.path.dirname(__file__)
                config_path = os.path.join(base_dir, "utils_json", "filterGenerator.json")

            # 설정 파일 로드
            self.config = self._load_config(config_path)
            self.examples = self.config.get("examples", [])
            self.system_prompt = self._build_system_prompt()

            info(f"[FilterGenerator] Initialized with model={model}, strict={strict}")
        except Exception as e:
            error(f"[FilterGenerator] Initialization failed: {e}")
            error(traceback.format_exc())
            raise

    @trace_in
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """JSON 설정 파일 로드"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                debug(f"[FilterGenerator] Config loaded from {config_path}")
                return config
        except Exception as e:
            error(f"[FilterGenerator] Failed to load config: {e}")
            return {
                "instruction": "사용자 질문에서 기간과 필터 단어를 추출하세요.",
                "output_format": {
                    "start_date": None,
                    "end_date": None,
                    "filter_words": []
                },
                "examples": []
            }

    @trace_in
    def _build_system_prompt(self) -> str:
        """JSON 설정 기반으로 시스템 프롬프트 생성"""
        instruction = self.config.get("instruction", "")
        output_format = self.config.get("output_format", {})
        today = datetime.date.today().strftime("%Y-%m-%d")

        date_context = f"오늘 날짜는 {today}입니다. '최근', '오늘 이후', '지난 달' 등의 표현은 이 날짜를 기준으로 계산하세요.\n\n"

        prompt = f"{date_context}{instruction}\n\n"
        prompt += f"출력 형식:\n{json.dumps(output_format, ensure_ascii=False, indent=2)}\n\n"

        if self.examples:
            prompt += "예시:\n"
            for ex in self.examples:
                prompt += f"입력: {ex['input']}\n"
                prompt += f"출력: {json.dumps(ex['output'], ensure_ascii=False)}\n\n"

        debug("[FilterGenerator] System prompt constructed successfully.")
        return prompt

    @trace_in
    def process_query(self, user_message: str) -> Dict[str, Any]:
        """사용자 질문으로부터 필터 생성"""
        try:
            trace(f"Processing query: {user_message[:50]}...")

            messages = [{"role": "system", "content": self.system_prompt}]
            for ex in self.examples:
                messages.append({"role": "user", "content": ex["input"]})
                messages.append({"role": "assistant", "content": json.dumps(ex["output"], ensure_ascii=False)})

            messages.append({"role": "user", "content": user_message})

            params = dict(model=self.model, messages=messages, max_tokens=300)
            if self.strict:
                params.update({"temperature": 0, "top_p": 1})
            else:
                params.update({"temperature": 0.3, "top_p": 0.9})

            response = self.client.chat.completions.create(**params)
            raw_output = response.choices[0].message.content.strip()
            debug(f"[FilterGenerator] Raw model output: {raw_output}")

            try:
                result = json.loads(raw_output)
                info(f"[FilterGenerator] Successfully parsed JSON result.")
                return result
            except json.JSONDecodeError:
                error("[FilterGenerator] JSON 파싱 실패, 원문 반환")
                return {"start_date": None, "end_date": None, "filter_words": [raw_output]}

        except Exception as e:
            error(f"[FilterGenerator] Error during filter generation: {e}")
            error(traceback.format_exc())
            return {"start_date": None, "end_date": None, "filter_words": []}

    @trace_in
    def generate_filters(self, user_message: str) -> Dict[str, Any]:
        """main.py 등에서 간단히 호출할 수 있는 wrapper"""
        return self.process_query(user_message)