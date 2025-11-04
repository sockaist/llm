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


class OpenAIInputNormalizer:
    """OpenAI API를 사용한 입력 정규화 클래스"""

    @trace_in
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", config_path: str = None):
        """
        OpenAI 입력 정규화기 초기화
        """
        try:
            self.client = openai.OpenAI(api_key=api_key)
            self.model = model

            # 기본 config 파일 경로 설정
            if config_path is None:
                config_path = os.path.join(os.path.dirname(__file__), "utils_json", "inputNormalizer.json")

            # JSON 설정 파일 로드
            self.config = self._load_config(config_path)
            self.examples = self.config.get("examples", [])
            self.system_prompt = self._build_system_prompt()

            info(f"[InputNormalizer] Initialized successfully (model={model}, examples={len(self.examples)})")

        except Exception as e:
            error(f"[InputNormalizer] Initialization failed: {e}")
            error(traceback.format_exc())
            raise

    @trace_in
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """JSON 설정 파일 로드"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                debug(f"[InputNormalizer] Config loaded from {config_path}")
                return config
        except Exception as e:
            error(f"[InputNormalizer] Failed to load config: {e}")
            return {
                "instruction": "입력을 정규화하고 JSON 형식으로 응답하세요.",
                "output_format": {"output": "정규화된 입력"},
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
                prompt += f"출력: {json.dumps({'output': ex['output']}, ensure_ascii=False)}\n\n"

        debug("[InputNormalizer] System prompt constructed successfully.")
        return prompt

    @trace_in
    def process_query(self, user_message: str) -> Dict[str, Any]:
        """사용자 쿼리 정규화"""
        try:
            trace(f"Normalizing user message: {user_message[:60]}...")

            messages = [{"role": "system", "content": self.system_prompt}]

            for ex in self.examples[:5]:
                messages.append({"role": "user", "content": ex["input"]})
                messages.append({"role": "assistant", "content": json.dumps({"output": ex["output"]}, ensure_ascii=False)})

            messages.append({"role": "user", "content": user_message})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=200
            )

            result_text = response.choices[0].message.content.strip()
            debug(f"[InputNormalizer] Raw output: {result_text}")

            # JSON 파싱 시도
            try:
                result = json.loads(result_text)
                info("[InputNormalizer] JSON parsed successfully.")
                return result
            except json.JSONDecodeError:
                trace("[InputNormalizer] JSON parsing failed, returning plain text output.")
                return {"output": result_text}

        except Exception as e:
            error(f"[InputNormalizer] Exception during normalization: {e}")
            error(traceback.format_exc())
            # 실패 시 원본 메시지 반환
            return {"output": user_message}

    @trace_in
    def normalize_input(self, user_message: str) -> str:
        """main_enhanced.py 호환성을 위한 메소드"""
        result = self.process_query(user_message)
        return result.get("output", user_message)