"""
테스트 케이스 - 프롬프트 템플릿 시스템
"""
import sys
import os
import unittest

# 프로젝트 루트 디렉토리를 파이썬 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.prompt import (
    SimplePromptTemplate,
    InstructionConfig
)

try:
    from src.prompt import Jinja2PromptTemplate
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

class TestPromptTemplates(unittest.TestCase):
    """
    프롬프트 템플릿 시스템 테스트 케이스
    """
    
    def test_simple_prompt_template(self):
        """
        SimplePromptTemplate 테스트
        """
        # 기본 템플릿 생성
        template = SimplePromptTemplate(
            template="안녕하세요, {name}님! 오늘 {weather} 날씨에 어떻게 지내세요?",
            input_variables=["name", "weather"]
        )
        
        # 변수 값 채우기
        result = template.format(name="홍길동", weather="맑은")
        self.assertEqual(result, "안녕하세요, 홍길동님! 오늘 맑은 날씨에 어떻게 지내세요?")
        
        # 변수 누락 시 오류 발생
        with self.assertRaises(ValueError):
            template.format(name="홍길동")
    
    @unittest.skipIf(not JINJA2_AVAILABLE, "Jinja2가 설치되지 않았습니다.")
    def test_jinja2_prompt_template(self):
        """
        Jinja2PromptTemplate 테스트
        """
        # Jinja2 템플릿 생성
        template = Jinja2PromptTemplate(
            template="안녕하세요, {{ name }}님! {% if weather %}오늘 {{ weather }} 날씨에 {% endif %}어떻게 지내세요?",
            input_variables=["name", "weather"]
        )
        
        # 모든 변수 값 채우기
        result = template.format(name="홍길동", weather="맑은")
        self.assertEqual(result, "안녕하세요, 홍길동님! 오늘 맑은 날씨에 어떻게 지내세요?")
        
        # 선택적 변수 생략
        result = template.format(name="홍길동", weather=None)
        self.assertEqual(result, "안녕하세요, 홍길동님! 어떻게 지내세요?")
    
    def test_instruction_config(self):
        """
        InstructionConfig 테스트
        """
        # 기본 InstructionConfig 생성
        instruction_config = InstructionConfig(
            instruction="당신은 {product}에 대한 정보를 제공하는 챗봇입니다.",
            input_variables=["product"],
            output_format={
                "product_name": "제품 이름 (문자열)",
                "description": "제품 설명 (문자열)",
                "price": "제품 가격 (숫자)"
            },
            examples=[
                {"input": "최신 스마트폰 정보 알려줘", "output": '{"product_name": "갤럭시 S24", "description": "삼성의 최신 플래그십 스마트폰입니다.", "price": 1200000}'},
            ]
        )
        
        # 변수 값 채우기
        formatted_instruction = instruction_config.format(product="스마트폰")
        self.assertEqual(formatted_instruction, "당신은 스마트폰에 대한 정보를 제공하는 챗봇입니다.")
        
        # 포맷된 명령어 확인
        formatted_instruction = instruction_config.format_instruction(product="스마트폰")
        self.assertIn("당신은 스마트폰에 대한 정보를 제공하는 챗봇입니다.", formatted_instruction)
        self.assertIn("출력 형식은 다음과 같습니다:", formatted_instruction)
        self.assertIn("product_name", formatted_instruction)
        
        # 예시 포맷 확인
        examples = instruction_config.format_examples()
        self.assertIn("다음은 몇 가지 예시입니다:", examples)
        self.assertIn("최신 스마트폰 정보 알려줘", examples)
        self.assertIn("갤럭시 S24", examples)
        
        # 완전한 프롬프트 생성 확인
        complete_prompt = instruction_config.format_complete_prompt(product="스마트폰")
        self.assertIn("당신은 스마트폰에 대한 정보를 제공하는 챗봇입니다.", complete_prompt)
        self.assertIn("출력 형식은 다음과 같습니다:", complete_prompt)
        self.assertIn("다음은 몇 가지 예시입니다:", complete_prompt)

if __name__ == "__main__":
    unittest.main()
