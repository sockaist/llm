from chatbot.src.backend.src.llm.parser_llm import inputChecker    



def main():
    """
    메인 함수
    """
    print("\n===== 심리 상담사 챗봇 =====")
    
    # API 키 설정
    api_key = "GOOGLE_API_KEY"
    
    try:
        # 심리 상담사 챗봇 초기화
        print("\n챗봇 시스템을 초기화하는 중입니다. 잠시만 기다려주세요...")
        checker = inputChecker(api_key=api_key)
        
        print("\n===== 심리 상담사 챗봇 =====")
        print("종료하려면 'exit' 또는 '종료'를 입력하세요.\n")
        
        while True:
            # 사용자 입력 받기
            user_message = input("\n사용자: ")
            print(user_message)
            result = checker.process_query(user_message)
            print(result)
            # 종료 조건
            if user_message.lower() in ["exit", "종료"]:
                print("상담을 종료합니다.")
                break
            
            # 쿼리 처리
            try:
                print(user_message)
                result = checker.process_query(user_message)
                print(result)
                
                # 유효하지 않은 쿼리인 경우
                if not result.get("is_valid", False):
                    print(f"\n상담사: 죄송합니다. 이 질문은 심리 상담 목적에 맞지 않습니다.")
                    continue
                
                # 상담 응답 출력
                print(f"질문이 유효합니다.")
                
            except Exception as e:
                print(f"오류 발생: {e}")
    
    except Exception as e:
        print(f"\n시스템 초기화 중 오류 발생: {e}")
        print("프로그램을 종료합니다.")

if __name__ == "__main__":
    main()
