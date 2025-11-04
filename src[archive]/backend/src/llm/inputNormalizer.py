"""
OpenAI 기반 입력 검증 및 정규화 모듈
"""

import openai
import json
import os
import traceback
from typing import Dict, Any


class OpenAIInputNormalizer:
    """OpenAI API를 사용한 입력 정규화 클래스"""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", config_path: str = "/Users/youngseocho/Desktop/socChatbot/llm/src/backend/src/llm/utils_json/inputNormalizer.json"):
        """
        OpenAI 입력 정규화기 초기화
        
        Args:
            api_key (str): OpenAI API 키
            model (str): 사용할 모델
            config_path (str): inputNormalizer.json 파일 경로
        """
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        
        # 기본 config 파일 경로 설정
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), "utils_json", "inputNormalizer.json")
        
        # JSON 설정 파일 로드
        self.config = self._load_config(config_path)
        
        # examples를 먼저 설정
        self.examples = self.config.get('examples', [])
        
        # 시스템 프롬프트 설정
        self.system_prompt = self._build_system_prompt()
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """
        JSON 설정 파일 로드
        
        Args:
            config_path (str): 설정 파일 경로
            
        Returns:
            Dict[str, Any]: 설정 데이터
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"설정 파일 로드 실패: {e}")
            # 기본 설정 반환
            return {
                "instruction": "입력을 정규화하고 JSON 형식으로 응답하세요.",
                "output_format": {"output": "정규화된 입력"},
                "examples": []
            }
    
    def _build_system_prompt(self) -> str:
        """
        JSON 설정을 기반으로 시스템 프롬프트 구성
        
        Returns:
            str: 구성된 시스템 프롬프트
        """
        instruction = self.config.get('instruction', '')
        output_format = self.config.get('output_format', {})
        
        prompt = f"{instruction}\n\n"
        prompt += f"출력 형식:\n{json.dumps(output_format, ensure_ascii=False, indent=2)}\n\n"
        
        # 예시가 있다면 추가
        if self.examples:
            prompt += "예시:\n"
            for example in self.examples:
                prompt += f"입력: {example['input']}\n"
                prompt += f"출력: {json.dumps({'output': example['output']}, ensure_ascii=False)}\n\n"
        
        return prompt

    def process_query(self, user_message: str) -> Dict[str, Any]:
        """
        사용자 쿼리 정규화
        
        Args:
            user_message (str): 사용자 메시지
            
        Returns:
            Dict[str, Any]: 정규화 결과
        """
        try:
            # 메시지 구성 - few-shot learning을 위한 예시 포함
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # 예시를 few-shot learning으로 추가 (더 나은 성능을 위해)
            for example in self.examples:  # 최대 5개 예시만 사용
                messages.append({"role": "user", "content": example['input']})
                messages.append({"role": "assistant", "content": json.dumps({'output': example['output']}, ensure_ascii=False)})
            
            # 실제 사용자 메시지 추가
            messages.append({"role": "user", "content": user_message})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=200
            )

            print(f"OpenAI 정규화 응답: {response}")  # 디버그 출력 추가
            
            result_text = response.choices[0].message.content.strip()
            
            # JSON 파싱 시도
            try:
                result = json.loads(result_text)
                return result
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 원본 텍스트 반환
                return {"output": result_text}
                    
        except Exception as e:
            print(f"입력 정규화 중 오류: {e}")
            print(f"오류 위치: {traceback.format_exc()}")
            # 실패 시 원본 메시지 반환
            return {"output": user_message}
    
    def normalize_input(self, user_message: str) -> str:
        """
        main_enhanced.py 호환성을 위한 메소드
        
        Args:
            user_message (str): 사용자 메시지
            
        Returns:
            str: 정규화된 질문
        """
        result = self.process_query(user_message)
        return result.get("output", user_message)