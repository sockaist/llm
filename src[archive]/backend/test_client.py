#!/usr/bin/env python3
"""
ChatBot API 테스트 클라이언트
서버 동작 확인용 간단한 테스트 스크립트
"""

import requests
import json
import sys
from typing import Dict, Any

# 서버 설정
SERVER_URL = "http://localhost:8000"

def test_server_connection():
    """서버 연결 테스트"""
    try:
        print("🔍 서버 연결 테스트 중...")
        response = requests.get(f"{SERVER_URL}/")
        if response.status_code == 200:
            data = response.json()
            print("✅ 서버 연결 성공!")
            print(f"📝 응답: {data}")
            return True
        else:
            print(f"❌ 서버 연결 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 서버 연결 오류: {e}")
        return False

def test_health_check():
    """헬스체크 테스트"""
    try:
        print("\\n🔍 헬스체크 테스트 중...")
        response = requests.get(f"{SERVER_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print("✅ 헬스체크 성공!")
            print(f"📊 서비스 상태: {data['status']}")
            print(f"📝 메시지: {data['message']}")
            print("🔧 컴포넌트 상태:")
            for component, status in data['components'].items():
                print(f"   • {component}: {status}")
            return True
        else:
            print(f"❌ 헬스체크 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 헬스체크 오류: {e}")
        return False

def test_chat(message: str, use_vector_search: bool = True):
    """채팅 테스트"""
    try:
        print(f"\\n💬 채팅 테스트: '{message}'")
        
        payload = {
            "message": message,
            "use_vector_search": use_vector_search
        }
        
        response = requests.post(
            f"{SERVER_URL}/chat",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 채팅 응답 성공!")
            print(f"🤖 응답: {data['response']}")
            print(f"📊 성공: {data['success']}")
            if 'message' in data:
                print(f"📝 상태: {data['message']}")
            return True
        else:
            print(f"❌ 채팅 응답 실패: {response.status_code}")
            print(f"📝 오류: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 채팅 테스트 오류: {e}")
        return False

def test_info():
    """API 정보 테스트"""
    try:
        print("\\n🔍 API 정보 테스트 중...")
        response = requests.get(f"{SERVER_URL}/info")
        if response.status_code == 200:
            data = response.json()
            print("✅ API 정보 조회 성공!")
            print(f"📝 이름: {data['name']}")
            print(f"📝 버전: {data['version']}")
            print(f"📝 설명: {data['description']}")
            print("🔧 사용 가능한 엔드포인트:")
            for endpoint, description in data['endpoints'].items():
                print(f"   • {endpoint}: {description}")
            return True
        else:
            print(f"❌ API 정보 조회 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API 정보 테스트 오류: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("🧪 KAIST 전산학부 ChatBot API 테스트 시작")
    print("="*60)
    
    # 1. 서버 연결 테스트
    if not test_server_connection():
        print("\\n❌ 서버가 실행되지 않았거나 연결할 수 없습니다.")
        print("💡 서버를 먼저 실행하세요: python run_server.py")
        sys.exit(1)
    
    # 2. 헬스체크 테스트
    if not test_health_check():
        print("\\n⚠️ 헬스체크 실패 - 일부 서비스에 문제가 있을 수 있습니다.")
    
    # 3. API 정보 테스트
    test_info()
    
    # 4. 채팅 테스트
    test_messages = [
        "안녕하세요!",
        "전산학부 교수님들 명단 알려주세요",
        "졸업 요건이 뭐야?",
        "컴퓨터구조 수업 정보 알려줘"
    ]
    
    for message in test_messages:
        test_chat(message)
    
    print("\\n" + "="*60)
    print("🎉 모든 테스트 완료!")
    print("💡 자세한 API 문서는 http://localhost:8000/docs 에서 확인할 수 있습니다.")

if __name__ == "__main__":
    main()