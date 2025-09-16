#!/usr/bin/env python3
"""
v2 시스템 간단 테스트
"""

import sys
import json
from pathlib import Path

# 프로젝트 경로 추가
sys.path.append('.')

def test_v2_models():
    """v2 데이터 모델 테스트"""
    print("🧪 v2 데이터 모델 테스트 시작")
    
    try:
        from app.api.routers.v2.models import (
            V2GenerationRequest, 
            V2GenerationResponse, 
            V2ProgressMessage,
            V2GenerationStatus
        )
        
        # V2GenerationRequest 테스트
        request = V2GenerationRequest(
            client_id="test_client_123",
            repo_path="/test/repo/path",
            changes_text="테스트 변경사항",
            use_performance_mode=True
        )
        
        assert request.client_id == "test_client_123"
        assert request.repo_path == "/test/repo/path"
        assert request.use_performance_mode is True
        print("✅ V2GenerationRequest 테스트 성공")
        
        # V2GenerationResponse 테스트
        response = V2GenerationResponse(
            client_id="test_client_123",
            websocket_url="ws://localhost:8000/api/v2/ws/progress/test_client_123"
        )
        
        assert response.client_id == "test_client_123"
        assert response.status == "accepted"
        assert "ws://localhost:8000" in response.websocket_url
        print("✅ V2GenerationResponse 테스트 성공")
        
        # V2ProgressMessage 테스트
        progress = V2ProgressMessage(
            client_id="test_client_123",
            status=V2GenerationStatus.ANALYZING_GIT,
            message="Git 분석 중...",
            progress=25.0
        )
        
        assert progress.client_id == "test_client_123"
        assert progress.status == V2GenerationStatus.ANALYZING_GIT
        assert progress.progress == 25.0
        print("✅ V2ProgressMessage 테스트 성공")
        
        # JSON 직렬화 테스트
        progress_dict = progress.model_dump()
        progress_json = json.dumps(progress_dict)
        assert "analyzing_git" in progress_json
        print("✅ JSON 직렬화 테스트 성공")
        
        print("🎉 모든 v2 모델 테스트 성공!")
        
    except Exception as e:
        print(f"❌ v2 모델 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"v2 모델 테스트 실패: {e}"


def test_v2_connection_manager():
    """v2 연결 관리자 테스트"""
    print("\n🧪 v2 연결 관리자 테스트 시작")
    
    try:
        from app.api.routers.v2.progress_websocket import V2ConnectionManager
        from app.api.routers.v2.models import V2ProgressMessage, V2GenerationStatus
        
        # 연결 관리자 생성
        manager = V2ConnectionManager()
        
        # 초기 상태 확인
        assert len(manager.get_connected_clients()) == 0
        assert not manager.is_connected("test_client")
        print("✅ 초기 상태 확인 성공")
        
        # 연결 상태 시뮬레이션 (실제 WebSocket 없이)
        manager.connections["test_client"] = "mock_websocket"
        
        assert manager.is_connected("test_client")
        assert "test_client" in manager.get_connected_clients()
        print("✅ 연결 상태 관리 테스트 성공")
        
        print("🎉 v2 연결 관리자 테스트 성공!")
        
    except Exception as e:
        print(f"❌ v2 연결 관리자 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"v2 연결 관리자 테스트 실패: {e}"


def test_v2_api_endpoints():
    """v2 API 엔드포인트 테스트"""
    print("\n🧪 v2 API 엔드포인트 테스트 시작")
    
    try:
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        # 상태 조회 엔드포인트 테스트
        response = client.get("/api/v2/scenario/status/test_client")
        assert response.status_code == 200
        
        data = response.json()
        assert data["client_id"] == "test_client"
        assert data["is_generating"] is False
        assert data["status"] == "idle"
        print("✅ 상태 조회 엔드포인트 테스트 성공")
        
        # API 루트 엔드포인트 테스트
        root_response = client.get("/api")
        assert root_response.status_code == 200
        print("✅ API 루트 엔드포인트 테스트 성공")
        
        print("🎉 v2 API 엔드포인트 테스트 성공!")
        
    except Exception as e:
        print(f"❌ v2 API 엔드포인트 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"v2 API 엔드포인트 테스트 실패: {e}"


def main():
    """메인 테스트 실행 함수"""
    print("🚀 v2 시스템 간단 테스트 실행")
    
    results = []
    
    # 각 테스트 실행
    results.append(test_v2_models())
    results.append(test_v2_connection_manager())
    results.append(test_v2_api_endpoints())
    
    # 결과 요약
    print(f"\n📊 테스트 결과 요약:")
    passed = sum(results)
    total = len(results)
    
    print(f"✅ 성공: {passed}/{total}")
    if passed < total:
        print(f"❌ 실패: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 모든 테스트 성공!")
    else:
        print("⚠️ 일부 테스트 실패")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)