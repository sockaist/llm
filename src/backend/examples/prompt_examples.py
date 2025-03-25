"""
프롬프트 템플릿 사용 예제
"""
import sys
import os

# 프로젝트 루트 디렉토리를 파이썬 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.prompt import (
    SimplePromptTemplate,
    Jinja2PromptTemplate,
    InstructionConfig
)

def simple_prompt_template_example():
    """
    SimplePromptTemplate 사용 예제
    """
    print("\n=== SimplePromptTemplate 사용 예제 ===")
    
    # 기본 템플릿 생성
    template = SimplePromptTemplate(
        template="안녕하세요, {name}님! 오늘 {weather} 날씨에 어떻게 지내세요?",
        input_variables=["name", "weather"]
    )
    
    # 변수 값 채우기
    result = template.format(name="홍길동", weather="맑은")
    print(f"결과: {result}")
    
    # 변수 누락 시 오류 발생
    try:
        template.format(name="홍길동")
    except ValueError as e:
        print(f"오류: {e}")

def jinja2_prompt_template_example():
    """
    Jinja2PromptTemplate 사용 예제
    """
    print("\n=== Jinja2PromptTemplate 사용 예제 ===")
    
    try:
        # Jinja2 템플릿 생성
        template = Jinja2PromptTemplate(
            template="안녕하세요, {{ name }}님! {% if weather %}오늘 {{ weather }} 날씨에 {% endif %}어떻게 지내세요?",
            input_variables=["name", "weather"]
        )
        
        # 모든 변수 값 채우기
        result = template.format(name="홍길동", weather="맑은")
        print(f"모든 변수 포함 결과: {result}")
        
        # 선택적 변수 생략
        result = template.format(name="홍길동", weather=None)
        print(f"선택적 변수 생략 결과: {result}")
    except ImportError:
        print("Jinja2가 설치되지 않았습니다. pip install jinja2 명령으로 설치할 수 있습니다.")

def instruction_config_example():
    """
    InstructionConfig 사용 예제
    """
    print("\n=== InstructionConfig 사용 예제 ===")
    
    # 기본 InstructionConfig 생성
    instruction_config = InstructionConfig(
        instruction="당신은 {product}에 대한 정보를 제공하는 챗봇입니다. 사용자의 질문에 친절하게 답변해주세요.",
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
    formatted_instruction = instruction_config.format_instruction(product="스마트폰")
    print(f"포맷된 명령어:\n{formatted_instruction}")
    
    # 예시 포맷
    examples = instruction_config.format_examples()
    print(f"\n포맷된 예시:\n{examples}")
    
    # 완전한 프롬프트 생성
    complete_prompt = instruction_config.format_complete_prompt(product="스마트폰")
    print(f"\n완전한 프롬프트:\n{complete_prompt}")
    
    # Jinja2 템플릿 사용
    try:
        jinja2_instruction_config = InstructionConfig(
            instruction="당신은 {{ product }}에 대한 정보를 제공하는 챗봇입니다. {% if user_name %}{{ user_name }}님의 {% endif %}질문에 친절하게 답변해주세요.",
            input_variables=["product", "user_name"],
            template_type="jinja2"
        )
        
        # 모든 변수 값 채우기
        formatted_instruction = jinja2_instruction_config.format_instruction(product="스마트폰", user_name="홍길동")
        print(f"\nJinja2 포맷된 명령어 (모든 변수):\n{formatted_instruction}")
        
        # 선택적 변수 생략
        formatted_instruction = jinja2_instruction_config.format_instruction(product="스마트폰", user_name=None)
        print(f"\nJinja2 포맷된 명령어 (선택적 변수 생략):\n{formatted_instruction}")
    except ImportError:
        print("\nJinja2가 설치되지 않았습니다. pip install jinja2 명령으로 설치할 수 있습니다.")

if __name__ == "__main__":
    simple_prompt_template_example()
    jinja2_prompt_template_example()
    instruction_config_example()
