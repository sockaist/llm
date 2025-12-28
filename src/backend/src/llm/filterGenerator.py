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


class OpenAIFilterGenerator:
    """OpenAI API를 사용한 검색 필터 생성 클래스"""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        config_path: str = None
    ):
        """
        OpenAI 필터 생성기 초기화

        Args:
            api_key (str): OpenAI API 키
            model (str): 사용할 모델 이름
            config_path (str): filterGenerator.json 설정 파일 경로 (기본적으로 상대경로 사용)
        """
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

        # config 경로를 상대경로로 지정
        if config_path is None:
            base_dir = os.path.dirname(__file__)
            config_path = os.path.join(base_dir, "utils_json", "filterGenerator.json")

        # 설정 파일 로드
        self.config = self._load_config(config_path)

        # 예시 로드
        self.examples = self.config.get("examples", [])

        # 시스템 프롬프트 구성
        self.system_prompt = self._build_system_prompt()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """JSON 설정 파일 로드"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"필터 설정 파일 로드 실패: {e}")
            return {
                "instruction": "사용자 질문에서 기간과 필터 단어를 추출하세요.",
                "output_format": {
                    "start_date": None,
                    "end_date": None,
                    "filter_words": []
                },
                "examples": []
            }

    def _build_system_prompt(self) -> str:
        """JSON 설정 기반으로 시스템 프롬프트 생성"""
        instruction = self.config.get("instruction", "")
        output_format = self.config.get("output_format", {})

        # 오늘 날짜 추가
        today = datetime.date.today().strftime("%Y-%m-%d")
        date_context = f"오늘 날짜는 {today}입니다. '최근', '오늘 이후', '지난 달' 등의 표현은 이 날짜를 기준으로 계산하세요.\n\n"

        prompt = f"{date_context}{instruction}\n\n"
        prompt += f"출력 형식:\n{json.dumps(output_format, ensure_ascii=False, indent=2)}\n\n"

        # 예시 추가
        if self.examples:
            prompt += "예시:\n"
            for ex in self.examples:
                prompt += f"입력: {ex['input']}\n"
                prompt += f"출력: {json.dumps(ex['output'], ensure_ascii=False)}\n\n"

        return prompt

    def process_query(self, user_message: str) -> Dict[str, Any]:
        """
        사용자 질문으로부터 필터 생성

        Args:
            user_message (str): 사용자 입력 문장
        Returns:
            Dict[str, Any]: {"start_date": ..., "end_date": ..., "filter_words": [...]}
        """
        try:
            messages = [{"role": "system", "content": self.system_prompt}]

            # few-shot 예시 추가
            for ex in self.examples:
                messages.append({"role": "user", "content": ex["input"]})
                messages.append({"role": "assistant", "content": json.dumps(ex["output"], ensure_ascii=False)})

            # 실제 입력 추가
            messages.append({"role": "user", "content": user_message})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=300,
            )

            raw_output = response.choices[0].message.content.strip()

            # JSON 파싱 시도
            try:
                result = json.loads(raw_output)
                return result
            except json.JSONDecodeError:
                print("JSON 파싱 실패, 원문 반환")
                return {"start_date": None, "end_date": None, "filter_words": [raw_output]}

        except Exception as e:
            print(f"필터 생성 중 오류: {e}")
            print(traceback.format_exc())
            return {"start_date": None, "end_date": None, "filter_words": []}

    def generate_filters(self, user_message: str) -> Dict[str, Any]:
        """
        main.py 등에서 간단히 호출할 수 있는 wrapper

        Args:
            user_message (str): 사용자 질문
        Returns:
            Dict[str, Any]: 필터 결과
        """
        return self.process_query(user_message)