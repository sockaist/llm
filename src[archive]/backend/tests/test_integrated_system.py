"""
통합 테스트 케이스 - 전체 시스템 테스트
"""
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# 프로젝트 루트 디렉토리를 파이썬 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.prompt import InstructionConfig
from src.output_parsers import JSONOutputParser, ListOutputParser
from src.chatbot import ChatBot
from src.chain import LLMChain, SequentialChain, TransformChain
from src.memory import BufferMemory, ConversationBufferWindowMemory

class TestIntegratedSystem(unittest.TestCase):
    """
    통합 시스템 테스트 케이스
    """
    
    def setUp(self):
        """
        테스트 설정
        """
        # ChatBot 모킹
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
    
    def test_integrated_qa_system(self):
        """
        통합 질문 응답 시스템 테스트
        """
        # 1. 메모리 시스템 설정
        memory = ConversationBufferWindowMemory(
            k=5,
            memory_key="chat_history",
            input_key="input",
            output_key="output",
            return_messages=True
        )
        
        # 2. 질문 분석을 위한 체인 설정
        question_analysis_prompt = InstructionConfig(
            instruction="다음 질문을 분석하여 주요 키워드를 추출해주세요: {question}",
            input_variables=["question"],
            output_parser=ListOutputParser()
        )
        
        # 출력 파서 모킹
        mock_list_parser = MagicMock()
        mock_list_parser.parse.return_value = ["키워드1", "키워드2", "키워드3"]
        question_analysis_prompt.output_parser = mock_list_parser
        
        question_analysis_chatbot = ChatBot(
            system_instruction="당신은 텍스트 분석 전문가입니다."
        )
        
        question_analysis_chain = LLMChain(
            chatbot=question_analysis_chatbot,
            prompt=question_analysis_prompt,
            output_key="keywords"
        )
        
        # 3. 답변 생성을 위한 체인 설정
        answer_prompt = InstructionConfig(
            instruction="""
다음 질문에 대한 답변을 JSON 형식으로 작성해주세요:
질문: {question}

추출된 키워드: {keywords}

이전 대화 내용:
{chat_history}
""",
            input_variables=["question", "keywords", "chat_history"],
            output_parser=JSONOutputParser(),
            output_format={
                "answer": "질문에 대한 답변",
                "sources": "참고 자료 (있는 경우)",
                "confidence": "답변의 확신도 (0-100)"
            }
        )
        
        # 출력 파서 모킹
        mock_json_parser = MagicMock()
        mock_json_parser.parse.return_value = {
            "answer": "이것은 테스트 답변입니다.",
            "sources": "테스트 참고 자료",
            "confidence": 90
        }
        answer_prompt.output_parser = mock_json_parser
        
        answer_chatbot = ChatBot(
            system_instruction="당신은 지식이 풍부한 도우미입니다."
        )
        
        answer_chain = LLMChain(
            chatbot=answer_chatbot,
            prompt=answer_prompt,
            output_key="response"
        )
        
        # 4. 변환 체인 설정 (메모리 업데이트 및 결과 포맷팅)
        def transform_func(inputs):
            # 메모리 업데이트
            memory.save_context(
                inputs={"input": inputs["question"]},
                outputs={"output": inputs["response"]["answer"]}
            )
            
            # 결과 포맷팅
            return {
                "formatted_answer": f"답변: {inputs['response']['answer']}\n"
                                   f"확신도: {inputs['response']['confidence']}%\n"
                                   f"참고 자료: {inputs['response']['sources']}"
            }
        
        transform_chain = TransformChain(
            transform_func=transform_func,
            input_variables=["question", "response"],
            output_variables=["formatted_answer"]
        )
        
        # 5. 전체 체인 설정
        qa_chain = SequentialChain(
            chains=[question_analysis_chain, answer_chain, transform_chain],
            input_variables=["question"],
            output_variables=["keywords", "response", "formatted_answer"]
        )
        
        # 6. 체인 실행
        chat_history_str = "사용자: 이전 질문\n시스템: 이전 답변\n"
        result = qa_chain.run({
            "question": "인공지능이란 무엇인가요?",
            "chat_history": chat_history_str
        })
        
        # 7. 결과 검증
        self.assertIn("keywords", result)
        self.assertIn("response", result)
        self.assertIn("formatted_answer", result)
        self.assertEqual(result["keywords"], ["키워드1", "키워드2", "키워드3"])
        self.assertEqual(result["response"]["answer"], "이것은 테스트 답변입니다.")
        self.assertEqual(result["response"]["confidence"], 90)
        self.assertIn("이것은 테스트 답변입니다.", result["formatted_answer"])
        
        # 8. 메모리 업데이트 확인
        memory_variables = memory.load_memory_variables()
        self.assertIn("chat_history", memory_variables)
        self.assertEqual(len(memory_variables["chat_history"]), 1)
        self.assertEqual(memory_variables["chat_history"][0]["input"], "인공지능이란 무엇인가요?")
        self.assertEqual(memory_variables["chat_history"][0]["output"], "이것은 테스트 답변입니다.")

if __name__ == "__main__":
    unittest.main()
