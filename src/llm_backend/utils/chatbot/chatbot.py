"""
ChatBot 클래스 구현 - Google Gemini API 연동
"""

import json
from typing import Any, Optional

# Google Gemini API 임포트
import google.generativeai as genai

# 프롬프트 템플릿과 출력 파서 임포트
from ..prompt import InstructionConfig
from ..output_parsers import BaseOutputParser


class LLMProvider:
    """
    LLM 제공자 클래스 - Google Gemini API 구현
    """

    def __init__(
        self,
        model_name: str,
        temperature: float,
        max_output_tokens: int,
        api_key: str,
        system_instruction: Optional[str] = None,
    ):
        """
        LLM 제공자 초기화

        Args:
            model_name (str): 사용할 Gemini 모델 이름
            temperature (float): 생성 텍스트의 무작위성 조절 값
            max_output_tokens (int): 생성 텍스트의 최대 토큰 수
            api_key (str): Google API 키
            system_instruction (Optional[str]): 시스템 지시사항
        """
        # API 키 설정
        genai.configure(api_key=api_key)

        # 생성 설정
        self.generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        }

        # 모델 초기화
        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=self.generation_config,
            system_instruction=system_instruction if system_instruction else None,
        )

        # 대화 세션
        self.convo = None

    def start_chat(self):
        """
        새로운 채팅 세션 시작
        """
        self.convo = self.model.start_chat()
        return self.convo

    def generate_response(self, prompt: str) -> str:
        """
        프롬프트에 대한 응답 생성

        Args:
            prompt (str): 입력 프롬프트

        Returns:
            str: 생성된 응답 텍스트
        """
        if self.convo is None:
            self.start_chat()

        try:
            self.convo.send_message(prompt)
            if self.convo.last:
                return self.convo.last.text
            else:
                return "응답이 없습니다."
        except Exception as e:
            return f"오류 발생: {e}"


class ChatBot:
    """
    LLM 모델과 상호작용하는 챗봇 클래스
    """

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash",
        temperature: float = 0.7,
        max_output_tokens: int = 200,
        instruction_config: Optional[InstructionConfig] = None,
        system_instruction: Optional[str] = None,
        output_parser: Optional[BaseOutputParser] = None,
        api_key: Optional[str] = None,
    ):
        """
        ChatBot 초기화

        Args:
            model_name (str, optional): 사용할 LLM 모델의 이름. 기본값은 "gemini-2.0-flash"입니다.
            temperature (float, optional): 생성될 텍스트의 무작위성을 조절하는 값. 기본값은 0.7입니다.
            max_output_tokens (int, optional): 생성될 텍스트의 최대 토큰 수. 기본값은 200입니다.
            instruction_config (InstructionConfig, optional): 챗봇의 명령어, 출력 형식, 예시 등을 담은 설정 객체. 기본값은 None입니다.
            system_instruction (str, optional): instruction_config가 없을 경우 사용할 기본 시스템 명령어. 기본값은 None입니다.
            output_parser (BaseOutputParser, optional): 모델 출력을 파싱할 파서. 기본값은 None입니다.
            api_key (str, optional): LLM API 키. 기본값은 None으로, 환경 변수에서 가져옵니다.
        """
        # API 키 설정
        self.api_key = "AIzaSyAFLQx2YD58mT3oT6w7-TFrwkf8TVAO4A0"
        if not self.api_key:
            print(
                "경고: API 키가 설정되지 않았습니다. 실제 API 호출은 작동하지 않을 수 있습니다."
            )

        # 모델 설정
        self.model_name = model_name
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens

        # 프롬프트 설정
        self.instruction_config = instruction_config
        self.system_instruction = system_instruction

        # 출력 파서 설정
        self.output_parser = output_parser
        if instruction_config and not output_parser:
            self.output_parser = instruction_config.output_parser

        # 대화 상태
        self.conversation_history = []
        self._is_running = False

        # LLM 제공자 초기화
        final_instruction = ""
        if self.instruction_config:
            final_instruction = self.instruction_config.format_instruction()
        elif self.system_instruction:
            final_instruction = self.system_instruction

        self.llm_provider = LLMProvider(
            model_name=self.model_name,
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
            api_key=self.api_key,
            system_instruction=final_instruction if final_instruction else None,
        )

    def start_chat(self):
        """
        새로운 채팅 세션을 시작합니다.
        """
        self.conversation_history = []
        self.llm_provider.start_chat()

        # 시스템 명령어가 있고 instruction_config가 없는 경우 첫 메시지로 전달
        if self.system_instruction and not self.instruction_config:
            try:
                # 시스템 명령어를 전달하고 응답은 무시
                self.llm_provider.generate_response(self.system_instruction)
            except Exception as e:
                print(f"Instruction 전달 중 오류 발생: {e}")

        print("챗봇과 대화를 시작합니다.")
        self._is_running = True

    def _get_formatted_prompt(self, user_input: str, **kwargs) -> str:
        """
        사용자 입력과 설정에 따라 포맷된 프롬프트를 생성합니다.

        Args:
            user_input (str): 사용자 입력 메시지
            **kwargs: 프롬프트 템플릿에 사용될 변수와 값

        Returns:
            str: 포맷된 프롬프트
        """
        # 기본 변수 설정
        variables = {"user_question": user_input, **kwargs}

        # InstructionConfig가 있는 경우
        if self.instruction_config:
            # 예시가 있는 경우 포함
            examples = (
                self.instruction_config.format_examples()
                if self.instruction_config.examples
                else ""
            )

            # 전체 프롬프트 생성
            formatted_instruction = self.instruction_config.format_instruction(
                **variables
            )
            prompt = f"{formatted_instruction}\n\n사용자 질문: {user_input}{examples}"
            return prompt

        # 시스템 명령어만 있는 경우
        elif self.system_instruction:
            return f"{self.system_instruction}\n\n사용자 질문: {user_input}"

        # 아무 설정도 없는 경우
        else:
            return user_input

    def _call_llm_api(self, prompt: str) -> str:
        """
        LLM API를 호출하여 응답을 받아옵니다.

        Args:
            prompt (str): LLM에 전달할 프롬프트

        Returns:
            str: LLM의 응답 텍스트
        """
        return self.llm_provider.generate_response(prompt)

    def _parse_response(self, response_text: str) -> Any:
        """
        LLM의 응답을 파싱합니다.

        Args:
            response_text (str): LLM의 응답 텍스트

        Returns:
            Any: 파싱된 응답 (출력 파서가 있는 경우) 또는 원본 텍스트
        """
        # 출력 파서가 있는 경우 파싱
        if self.output_parser:
            try:
                return self.output_parser.parse(response_text)
            except Exception as e:
                print(
                    f"경고: 출력 파싱에 실패했습니다. 원본 텍스트를 반환합니다. 오류: {e}"
                )
                return response_text

        # 출력 파서가 없지만 JSON 형식이 요청된 경우
        elif self.instruction_config and self.instruction_config.output_format:
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                print("경고: JSON 파싱에 실패했습니다. 원본 텍스트를 반환합니다.")
                return response_text

        # 그 외의 경우 원본 텍스트 반환
        else:
            return response_text

    def send_message(self, user_input: str, **kwargs) -> Any:
        """
        사용자 메시지를 보내고 챗봇의 응답을 반환합니다.

        Args:
            user_input (str): 사용자의 메시지
            **kwargs: 프롬프트 템플릿에 사용될 변수와 값

        Returns:
            Any: 챗봇의 응답 (파싱된 형식 또는 텍스트)
        """
        if not self._is_running:
            print("오류: 챗봇이 실행 중이 아닙니다. start_chat() 메서드를 호출하세요.")
            return "챗봇이 실행 중이 아닙니다."

        # 프롬프트 생성
        prompt = self._get_formatted_prompt(user_input, **kwargs)

        # 대화 기록에 사용자 메시지 추가
        self.conversation_history.append({"role": "user", "content": user_input})

        try:
            # LLM API 호출
            response_text = self._call_llm_api(prompt)

            # 대화 기록에 챗봇 응답 추가
            self.conversation_history.append(
                {"role": "assistant", "content": response_text}
            )

            # 응답 파싱 및 반환
            parsed_response = self._parse_response(response_text)
            return parsed_response

        except Exception as e:
            error_message = f"오류 발생: {e}"
            print(error_message)
            return error_message

    def run(self):
        """
        챗봇을 실행하여 사용자와의 대화를 시작합니다.
        """
        self.start_chat()
        print("종료하려면 '종료'를 입력하세요.")

        while self._is_running:
            user_input = input("사용자: ")
            if user_input.lower() == "종료":
                self.stop()
                break

            # 사용자 입력을 변수로 전달
            response = self.send_message(user_input, user_question=user_input)
            print("챗봇:", response)

        print("챗봇을 종료합니다.")

    def stop(self):
        """
        챗봇의 실행 루프를 종료합니다.
        """
        self._is_running = False

    def is_running(self):
        """
        챗봇이 현재 실행 중인지 여부를 반환합니다.

        Returns:
            bool: 챗봇이 실행 중이면 True, 아니면 False를 반환합니다.
        """
        return self._is_running

    def get_conversation_history(self):
        """
        현재까지의 대화 기록을 반환합니다.

        Returns:
            List[Dict[str, str]]: 대화 기록 리스트
        """
        return self.conversation_history

    def clear_conversation_history(self):
        """
        대화 기록을 초기화합니다.
        """
        self.conversation_history = []
