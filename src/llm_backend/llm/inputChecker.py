"""
OpenAI 기반 입력 검증 및 정규화 모듈
"""

import openai
import json
import os
import traceback
from typing import Dict, Any
from llm_backend.utils.logger import logger, info, debug, error
from llm_backend.utils.debug import trace, trace_in


class OpenAIInputChecker:
    """OpenAI API를 사용한 입력 검증 클래스"""

    @trace_in
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", config_path: str = None):
        """
        OpenAI 입력 검증기 초기화
        """
        try:
            self.client = openai.OpenAI(api_key=api_key)
            self.model = model

            # 기본 config 파일 경로 설정
            if config_path is None:
                config_path = os.path.join(os.path.dirname(__file__), "utils_json", "inputchecker.json")

            # JSON 설정 파일 로드
            self.config = self._load_config(config_path)
            self.examples = self.config.get("examples", [])
            self.system_prompt = self._build_system_prompt()

            info(f"[InputChecker] Initialized with model={model}, examples={len(self.examples)}")
        except Exception as e:
            error(f"[InputChecker] Initialization failed: {e}")
            error(traceback.format_exc())
            raise

    @trace_in
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """JSON 설정 파일 로드"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                debug(f"[InputChecker] Config loaded successfully from {config_path}")
                return config
        except Exception as e:
            error(f"[InputChecker] Failed to load config file: {e}")
            return {
                "instruction": "입력의 유효성을 검사하고 JSON 형식으로 응답하세요.",
                "output_format": {"is_valid": "true 또는 false"},
                "examples": []
            }

    @trace_in
    def _build_system_prompt(self) -> str:
        """JSON 설정을 기반으로 시스템 프롬프트 구성"""
        instruction = self.config.get("instruction", "")
        output_format = self.config.get("output_format", {})
        examples = self.examples

        prompt = f"{instruction}\n\n"
        prompt += f"출력 형식:\n{json.dumps(output_format, ensure_ascii=False, indent=2)}\n\n"

        # 예시 추가
        if examples:
            prompt += "예시:\n"
            for ex in examples:
                prompt += f"입력: {ex['input']}\n"
                prompt += f"출력: {json.dumps(ex['output'], ensure_ascii=False)}\n\n"

        debug("[InputChecker] System prompt constructed successfully.")
        return prompt

    @trace_in
    def process_query(self, user_message: str) -> Dict[str, Any]:
        """사용자 쿼리의 유효성 검사"""
        try:
            trace(f"Processing input validation for message: {user_message[:50]}...")

            # 메시지 구성
            messages = [{"role": "system", "content": self.system_prompt}]
            for ex in self.examples[:3]:
                messages.append({"role": "user", "content": ex["input"]})
                messages.append({"role": "assistant", "content": json.dumps(ex["output"], ensure_ascii=False)})

            messages.append({"role": "user", "content": user_message})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=100
            )

            result_text = response.choices[0].message.content.strip()
            debug(f"[InputChecker] Raw output: {result_text}")

            # JSON 파싱 시도
            try:
                result = json.loads(result_text)
                info("[InputChecker] JSON parsed successfully.")
                return result
            except json.JSONDecodeError:
                trace("[InputChecker] JSON parse failed, attempting heuristic recovery.")
                if "true" in result_text.lower():
                    return {"is_valid": "true"}
                else:
                    return {"is_valid": "false"}

        except Exception as e:
            error(f"[InputChecker] Exception occurred: {e}")
            error(traceback.format_exc())
            # 기본적으로 유효한 것으로 처리
            return {"is_valid": "true"}

    @trace_in
    def check_input(self, user_message: str) -> bool:
        """main_enhanced.py 호환성을 위한 메소드"""
        result = self.process_query(user_message)
        return result.get("is_valid", "true") == "true"