"""
테스트 케이스 - 체인 기능
"""
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# 프로젝트 루트 디렉토리를 파이썬 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.chain import Chain, LLMChain, SequentialChain, RouterChain, TransformChain
from src.chatbot import ChatBot
from src.prompt import InstructionConfig
from src.output_parsers import ListOutputParser

class TestChains(unittest.TestCase):
    """
    체인 기능 테스트 케이스
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
    
    def test_llm_chain(self):
        """
        LLMChain 테스트
        """
        # 프롬프트 템플릿 생성
        prompt = InstructionConfig(
            instruction="다음 주제에 대한 세 가지 핵심 포인트를 알려주세요: {topic}",
            input_variables=["topic"]
        )
        
        # 출력 파서 모킹
        mock_parser = MagicMock()
        mock_parser.parse.return_value = ["포인트1", "포인트2", "포인트3"]
        prompt.output_parser = mock_parser
        
        # ChatBot 생성
        chatbot = ChatBot(
            system_instruction="당신은 교육 콘텐츠 전문가입니다."
        )
        
        # LLMChain 생성
        chain = LLMChain(
            chatbot=chatbot,
            prompt=prompt,
            output_key="points"
        )
        
        # 체인 실행
        result = chain.run({"topic": "인공지능의 미래"})
        
        # 결과 검증
        self.assertIn("points", result)
        self.assertEqual(result["points"], ["포인트1", "포인트2", "포인트3"])
        
        # 입력 변수가 전달되었는지 확인
        chatbot.start_chat.assert_called_once()
        self.assertEqual(chatbot.send_message.call_args[0][0], "인공지능의 미래")
        self.assertEqual(chatbot.send_message.call_args[1], {"topic": "인공지능의 미래"})
    
    def test_sequential_chain(self):
        """
        SequentialChain 테스트
        """
        # 첫 번째 체인: 주제에 대한 핵심 포인트 생성
        points_prompt = InstructionConfig(
            instruction="다음 주제에 대한 세 가지 핵심 포인트를 알려주세요: {topic}",
            input_variables=["topic"]
        )
        
        # 출력 파서 모킹
        mock_points_parser = MagicMock()
        mock_points_parser.parse.return_value = ["포인트1", "포인트2", "포인트3"]
        points_prompt.output_parser = mock_points_parser
        
        points_chatbot = ChatBot(
            system_instruction="당신은 교육 콘텐츠 전문가입니다."
        )
        
        points_chain = LLMChain(
            chatbot=points_chatbot,
            prompt=points_prompt,
            output_key="points"
        )
        
        # 두 번째 체인: 핵심 포인트를 바탕으로 요약 생성
        summary_prompt = InstructionConfig(
            instruction="다음 핵심 포인트를 바탕으로 {topic}에 대한 간결한 요약을 작성해주세요:\n{points}",
            input_variables=["topic", "points"]
        )
        
        summary_chatbot = ChatBot(
            system_instruction="당신은 전문 작가입니다."
        )
        
        summary_chain = LLMChain(
            chatbot=summary_chatbot,
            prompt=summary_prompt,
            output_key="summary"
        )
        
        # SequentialChain 생성
        sequential_chain = SequentialChain(
            chains=[points_chain, summary_chain],
            input_variables=["topic"],
            output_variables=["points", "summary"]
        )
        
        # 체인 실행
        result = sequential_chain.run({"topic": "기후 변화"})
        
        # 결과 검증
        self.assertIn("points", result)
        self.assertIn("summary", result)
        self.assertEqual(result["points"], ["포인트1", "포인트2", "포인트3"])
        self.assertEqual(result["summary"], "테스트 응답입니다.")
        
        # 두 번째 체인에 첫 번째 체인의 결과가 전달되었는지 확인
        self.assertEqual(summary_chatbot.send_message.call_args[1]["points"], ["포인트1", "포인트2", "포인트3"])
    
    def test_router_chain(self):
        """
        RouterChain 테스트
        """
        # 라우팅 함수 정의
        def router_func(inputs):
            query = inputs.get("query", "").lower()
            if "날씨" in query:
                return "weather"
            elif "뉴스" in query:
                return "news"
            else:
                return "general"
        
        # 날씨 체인
        weather_prompt = InstructionConfig(
            instruction="다음 지역의 날씨 정보를 제공해주세요: {query}",
            input_variables=["query"]
        )
        
        weather_chatbot = ChatBot(
            system_instruction="당신은 기상 정보 전문가입니다."
        )
        
        weather_chain = LLMChain(
            chatbot=weather_chatbot,
            prompt=weather_prompt,
            output_key="response"
        )
        
        # 뉴스 체인
        news_prompt = InstructionConfig(
            instruction="다음 주제에 대한 최신 뉴스를 알려주세요: {query}",
            input_variables=["query"]
        )
        
        news_chatbot = ChatBot(
            system_instruction="당신은 뉴스 기자입니다."
        )
        
        news_chain = LLMChain(
            chatbot=news_chatbot,
            prompt=news_prompt,
            output_key="response"
        )
        
        # 일반 체인
        general_prompt = InstructionConfig(
            instruction="다음 질문에 답변해주세요: {query}",
            input_variables=["query"]
        )
        
        general_chatbot = ChatBot(
            system_instruction="당신은 친절한 도우미입니다."
        )
        
        general_chain = LLMChain(
            chatbot=general_chatbot,
            prompt=general_prompt,
            output_key="response"
        )
        
        # RouterChain 생성
        router_chain = RouterChain(
            router_func=router_func,
            destination_chains={
                "weather": weather_chain,
                "news": news_chain,
                "general": general_chain
            }
        )
        
        # 날씨 질문으로 체인 실행
        weather_result = router_chain.run({"query": "서울 날씨 어때요?"})
        
        # 결과 검증
        self.assertIn("response", weather_result)
        self.assertEqual(weather_result["response"], "테스트 응답입니다.")
        self.assertEqual(weather_result["_router_key"], "weather")
        
        # 날씨 체인이 호출되었는지 확인
        weather_chatbot.send_message.assert_called_once()
        
        # 뉴스 질문으로 체인 실행
        news_result = router_chain.run({"query": "최신 기술 뉴스 알려줘"})
        
        # 결과 검증
        self.assertIn("response", news_result)
        self.assertEqual(news_result["response"], "테스트 응답입니다.")
        self.assertEqual(news_result["_router_key"], "news")
        
        # 뉴스 체인이 호출되었는지 확인
        news_chatbot.send_message.assert_called_once()
    
    def test_transform_chain(self):
        """
        TransformChain 테스트
        """
        # 변환 함수 정의
        def transform_func(inputs):
            text = inputs.get("text", "")
            
            # 단어 수 계산
            word_count = len(text.split())
            
            # 문자 수 계산
            char_count = len(text)
            
            # 문장 수 계산
            sentence_count = len([s for s in text.split('.') if s.strip()])
            
            return {
                "word_count": word_count,
                "char_count": char_count,
                "sentence_count": sentence_count,
                "text": text  # 원본 텍스트도 유지
            }
        
        # TransformChain 생성
        transform_chain = TransformChain(
            transform_func=transform_func,
            input_variables=["text"],
            output_variables=["word_count", "char_count", "sentence_count", "text"]
        )
        
        # 체인 실행
        text = "이것은 예시 문장입니다. 이 문장은 텍스트 분석을 위한 것입니다. 파이썬으로 텍스트를 분석해봅시다."
        result = transform_chain.run({"text": text})
        
        # 결과 검증
        self.assertEqual(result["word_count"], 16)
        self.assertEqual(result["char_count"], len(text))
        self.assertEqual(result["sentence_count"], 3)
        self.assertEqual(result["text"], text)

if __name__ == "__main__":
    unittest.main()
