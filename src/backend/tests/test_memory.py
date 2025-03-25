"""
테스트 케이스 - 메모리 시스템
"""
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# 프로젝트 루트 디렉토리를 파이썬 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.memory import (
    BufferMemory,
    ConversationBufferWindowMemory,
    ConversationSummaryMemory,
    ConversationTokenBufferMemory
)
from src.chatbot import ChatBot

class TestMemorySystems(unittest.TestCase):
    """
    메모리 시스템 테스트 케이스
    """
    
    def setUp(self):
        """
        테스트 설정
        """
        # ChatBot 모킹 (ConversationSummaryMemory 테스트용)
        self.patcher = patch('src.chatbot.chatbot.LLMProvider')
        self.mock_llm_provider = self.patcher.start()
        
        # 모의 응답 설정
        mock_instance = MagicMock()
        mock_instance.generate_response.return_value = "대화 요약: 사용자가 질문하고 챗봇이 답변했습니다."
        self.mock_llm_provider.return_value = mock_instance
    
    def tearDown(self):
        """
        테스트 종료 후 정리
        """
        self.patcher.stop()
    
    def test_buffer_memory(self):
        """
        BufferMemory 테스트
        """
        # BufferMemory 생성
        memory = BufferMemory(
            memory_key="chat_history",
            input_key="input",
            output_key="output"
        )
        
        # 대화 컨텍스트 저장
        memory.save_context(
            inputs={"input": "안녕하세요!"},
            outputs={"output": "안녕하세요! 무엇을 도와드릴까요?"}
        )
        
        memory.save_context(
            inputs={"input": "오늘 날씨 어때요?"},
            outputs={"output": "오늘은 맑고 화창한 날씨입니다."}
        )
        
        # 메모리 변수 로드
        memory_variables = memory.load_memory_variables()
        
        # 결과 검증
        self.assertIn("chat_history", memory_variables)
        self.assertIn("안녕하세요!", memory_variables["chat_history"])
        self.assertIn("오늘 날씨 어때요?", memory_variables["chat_history"])
        self.assertIn("맑고 화창한 날씨입니다", memory_variables["chat_history"])
        
        # 메시지 객체 형식으로 로드
        message_memory = BufferMemory(
            memory_key="chat_history",
            input_key="input",
            output_key="output",
            return_messages=True
        )
        
        message_memory.save_context(
            inputs={"input": "안녕하세요!"},
            outputs={"output": "안녕하세요! 무엇을 도와드릴까요?"}
        )
        
        message_memory.save_context(
            inputs={"input": "오늘 날씨 어때요?"},
            outputs={"output": "오늘은 맑고 화창한 날씨입니다."}
        )
        
        message_variables = message_memory.load_memory_variables()
        
        # 결과 검증
        self.assertIn("chat_history", message_variables)
        self.assertEqual(len(message_variables["chat_history"]), 2)
        self.assertEqual(message_variables["chat_history"][0]["input"], "안녕하세요!")
        self.assertEqual(message_variables["chat_history"][0]["output"], "안녕하세요! 무엇을 도와드릴까요?")
        self.assertEqual(message_variables["chat_history"][1]["input"], "오늘 날씨 어때요?")
        self.assertEqual(message_variables["chat_history"][1]["output"], "오늘은 맑고 화창한 날씨입니다.")
        
        # 메모리 초기화
        memory.clear()
        cleared_variables = memory.load_memory_variables()
        
        # 결과 검증
        self.assertEqual(cleared_variables["chat_history"], "")
    
    def test_conversation_buffer_window_memory(self):
        """
        ConversationBufferWindowMemory 테스트
        """
        # ConversationBufferWindowMemory 생성 (최근 2개 대화만 유지)
        memory = ConversationBufferWindowMemory(
            k=2,
            memory_key="chat_history",
            input_key="input",
            output_key="output"
        )
        
        # 여러 대화 컨텍스트 저장
        memory.save_context(
            inputs={"input": "안녕하세요!"},
            outputs={"output": "안녕하세요! 무엇을 도와드릴까요?"}
        )
        
        memory.save_context(
            inputs={"input": "당신은 누구인가요?"},
            outputs={"output": "저는 AI 챗봇입니다."}
        )
        
        memory.save_context(
            inputs={"input": "오늘 날씨 어때요?"},
            outputs={"output": "오늘은 맑고 화창한 날씨입니다."}
        )
        
        # 메모리 변수 로드 (최근 2개 대화만 포함)
        memory_variables = memory.load_memory_variables()
        
        # 결과 검증
        self.assertIn("chat_history", memory_variables)
        self.assertNotIn("안녕하세요!", memory_variables["chat_history"])  # 첫 번째 대화는 제외됨
        self.assertIn("당신은 누구인가요?", memory_variables["chat_history"])
        self.assertIn("AI 챗봇입니다", memory_variables["chat_history"])
        self.assertIn("오늘 날씨 어때요?", memory_variables["chat_history"])
        self.assertIn("맑고 화창한 날씨입니다", memory_variables["chat_history"])
        
        # 추가 대화 저장
        memory.save_context(
            inputs={"input": "내일 날씨는 어때요?"},
            outputs={"output": "내일은 비가 올 예정입니다."}
        )
        
        # 메모리 변수 다시 로드 (최근 2개 대화만 포함, 첫 번째와 두 번째 대화는 제외됨)
        updated_variables = memory.load_memory_variables()
        
        # 결과 검증
        self.assertNotIn("안녕하세요!", updated_variables["chat_history"])
        self.assertNotIn("당신은 누구인가요?", updated_variables["chat_history"])
        self.assertIn("오늘 날씨 어때요?", updated_variables["chat_history"])
        self.assertIn("내일 날씨는 어때요?", updated_variables["chat_history"])
        self.assertIn("비가 올 예정입니다", updated_variables["chat_history"])
    
    def test_conversation_summary_memory(self):
        """
        ConversationSummaryMemory 테스트
        """
        # ChatBot 생성
        chatbot = ChatBot(
            system_instruction="당신은 대화 요약 전문가입니다."
        )
        
        # ConversationSummaryMemory 생성
        memory = ConversationSummaryMemory(
            chatbot=chatbot,
            memory_key="chat_summary",
            input_key="input",
            output_key="output"
        )
        
        # 여러 대화 컨텍스트 저장
        for i in range(3):
            memory.save_context(
                inputs={"input": f"질문 {i}"},
                outputs={"output": f"답변 {i}"}
            )
        
        # 메모리 변수 로드 (요약된 대화)
        memory_variables = memory.load_memory_variables()
        
        # 결과 검증
        self.assertIn("chat_summary", memory_variables)
        self.assertEqual(memory_variables["chat_summary"], "대화 요약: 사용자가 질문하고 챗봇이 답변했습니다.")
        
        # 챗봇이 요약을 생성하기 위해 호출되었는지 확인
        chatbot.send_message.assert_called()
    
    def test_conversation_token_buffer_memory(self):
        """
        ConversationTokenBufferMemory 테스트
        """
        # ConversationTokenBufferMemory 생성 (최대 50 토큰 제한)
        memory = ConversationTokenBufferMemory(
            max_token_limit=50,
            memory_key="chat_history",
            input_key="input",
            output_key="output"
        )
        
        # 여러 대화 컨텍스트 저장
        memory.save_context(
            inputs={"input": "안녕하세요!"},
            outputs={"output": "안녕하세요! 무엇을 도와드릴까요?"}
        )
        
        # 토큰 수 확인 (실제 구현에 따라 다를 수 있음)
        self.assertLessEqual(memory.current_token_count, 50)
        
        # 긴 대화 추가
        long_input = "인공지능에 대해 자세히 알려주세요. 인공지능의 역사, 현재 상태, 미래 전망 등에 대해 설명해주세요."
        long_output = "인공지능은 인간의 학습능력, 추론능력, 지각능력을 인공적으로 구현한 컴퓨터 시스템입니다. 1950년대부터 연구가 시작되었으며, 현재는 딥러닝을 중심으로 빠르게 발전하고 있습니다. 미래에는 더욱 발전하여 다양한 분야에 적용될 것으로 예상됩니다."
        
        memory.save_context(
            inputs={"input": long_input},
            outputs={"output": long_output}
        )
        
        # 메모리 변수 로드 (토큰 제한에 따라 일부 대화만 포함될 수 있음)
        memory_variables = memory.load_memory_variables()
        
        # 결과 검증 (토큰 제한으로 인해 첫 번째 대화가 제외될 수 있음)
        self.assertIn("chat_history", memory_variables)
        
        # 현재 토큰 수가 제한을 초과하지 않는지 확인
        self.assertLessEqual(memory.current_token_count, 50)

if __name__ == "__main__":
    unittest.main()
