"""
테스트 케이스 - ChatBot 클래스
"""
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# 프로젝트 루트 디렉토리를 파이썬 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.chatbot import ChatBot
from src.prompt import InstructionConfig
from src.output_parsers import JSONOutputParser, ListOutputParser

class TestChatBot(unittest.TestCase):
    """
    ChatBot 클래스 테스트 케이스
    """
    
    def setUp(self):
        """
        테스트 설정
        """
        # LLM 호출을 모킹하여 실제 API 호출 없이 테스트
        self.patcher = patch('src.chatbot.chatbot.LLMProvider')
        self.mock_llm_provider = self.patcher.start()
        
        # 모의 응답 설정
        mock_instance = MagicMock()
        mock_instance.generate_response.return_value = "테스트 응답입니다."
        self.mock_llm_provider.return_value = mock_instance
    
    def tearDown(self):
        """
        테스트 종료 후 정리
        """
        self.patcher.stop()
    
    def test_basic_chatbot_initialization(self):
        """
        기본 ChatBot 초기화 테스트
        """
        chatbot = ChatBot(
            system_instruction="당신은 테스트 챗봇입니다."
        )
        
        self.assertEqual(chatbot.system_instruction, "당신은 테스트 챗봇입니다.")
        self.assertIsNone(chatbot.instruction_config)
        self.assertFalse(chatbot._is_running)
    
    def test_chatbot_with_instruction_config(self):
        """
        InstructionConfig를 사용한 ChatBot 초기화 테스트
        """
        instruction_config = InstructionConfig(
            instruction="당신은 {product}에 대한 정보를 제공하는 챗봇입니다.",
            input_variables=["product"],
            output_parser=JSONOutputParser()
        )
        
        chatbot = ChatBot(
            instruction_config=instruction_config
        )
        
        self.assertIsNone(chatbot.system_instruction)
        self.assertEqual(chatbot.instruction_config, instruction_config)
        self.assertFalse(chatbot._is_running)
    
    def test_start_chat(self):
        """
        채팅 시작 테스트
        """
        chatbot = ChatBot(
            system_instruction="당신은 테스트 챗봇입니다."
        )
        
        chatbot.start_chat()
        self.assertTrue(chatbot._is_running)
        self.assertIsNotNone(chatbot.conversation_history)
        self.assertEqual(len(chatbot.conversation_history), 0)
    
    def test_send_message(self):
        """
        메시지 전송 테스트
        """
        chatbot = ChatBot(
            system_instruction="당신은 테스트 챗봇입니다."
        )
        
        # 채팅 시작 전 메시지 전송 시도
        with self.assertRaises(RuntimeError):
            chatbot.send_message("안녕하세요!")
        
        # 채팅 시작 후 메시지 전송
        chatbot.start_chat()
        response = chatbot.send_message("안녕하세요!")
        
        self.assertEqual(response, "테스트 응답입니다.")
        self.assertEqual(len(chatbot.conversation_history), 2)  # 사용자 메시지와 챗봇 응답
        self.assertEqual(chatbot.conversation_history[0]["role"], "user")
        self.assertEqual(chatbot.conversation_history[0]["content"], "안녕하세요!")
        self.assertEqual(chatbot.conversation_history[1]["role"], "assistant")
        self.assertEqual(chatbot.conversation_history[1]["content"], "테스트 응답입니다.")
    
    def test_send_message_with_variables(self):
        """
        변수를 포함한 메시지 전송 테스트
        """
        instruction_config = InstructionConfig(
            instruction="당신은 {product}에 대한 정보를 제공하는 챗봇입니다.",
            input_variables=["product"]
        )
        
        chatbot = ChatBot(
            instruction_config=instruction_config
        )
        
        chatbot.start_chat()
        response = chatbot.send_message("최신 제품 정보 알려줘", product="스마트폰")
        
        self.assertEqual(response, "테스트 응답입니다.")
        # 내부적으로 instruction_config.format이 호출되었는지 확인하는 것은 어렵지만,
        # 응답이 정상적으로 반환되었는지 확인
    
    def test_get_conversation_history(self):
        """
        대화 기록 가져오기 테스트
        """
        chatbot = ChatBot(
            system_instruction="당신은 테스트 챗봇입니다."
        )
        
        chatbot.start_chat()
        chatbot.send_message("안녕하세요!")
        chatbot.send_message("오늘 날씨 어때요?")
        
        history = chatbot.get_conversation_history()
        
        self.assertEqual(len(history), 4)  # 두 개의 사용자 메시지와 두 개의 챗봇 응답
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[0]["content"], "안녕하세요!")
        self.assertEqual(history[1]["role"], "assistant")
        self.assertEqual(history[1]["content"], "테스트 응답입니다.")
        self.assertEqual(history[2]["role"], "user")
        self.assertEqual(history[2]["content"], "오늘 날씨 어때요?")
        self.assertEqual(history[3]["role"], "assistant")
        self.assertEqual(history[3]["content"], "테스트 응답입니다.")
    
    def test_clear_conversation_history(self):
        """
        대화 기록 초기화 테스트
        """
        chatbot = ChatBot(
            system_instruction="당신은 테스트 챗봇입니다."
        )
        
        chatbot.start_chat()
        chatbot.send_message("안녕하세요!")
        
        self.assertEqual(len(chatbot.conversation_history), 2)
        
        chatbot.clear_conversation_history()
        
        self.assertEqual(len(chatbot.conversation_history), 0)
    
    def test_chatbot_with_output_parser(self):
        """
        출력 파서를 사용한 ChatBot 테스트
        """
        # 출력 파서를 사용하는 InstructionConfig 생성
        instruction_config = InstructionConfig(
            instruction="다음 항목을 리스트로 작성해주세요: {topic}",
            input_variables=["topic"],
            output_parser=ListOutputParser()
        )
        
        # 출력 파서가 JSON 문자열을 파싱하도록 모킹
        mock_parser = MagicMock()
        mock_parser.parse.return_value = ["항목1", "항목2", "항목3"]
        instruction_config.output_parser = mock_parser
        
        chatbot = ChatBot(
            instruction_config=instruction_config
        )
        
        chatbot.start_chat()
        response = chatbot.send_message("과일 종류 알려줘", topic="과일")
        
        # 출력 파서가 호출되었고, 파싱된 결과가 반환되었는지 확인
        mock_parser.parse.assert_called_once_with("테스트 응답입니다.")
        self.assertEqual(response, ["항목1", "항목2", "항목3"])

if __name__ == "__main__":
    unittest.main()
