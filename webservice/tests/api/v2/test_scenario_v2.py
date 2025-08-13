"""
v2 시나리오 생성 API 테스트
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from pathlib import Path
import sys

# 프로젝트 경로 설정
sys.path.append(str(Path(__file__).resolve().parents[3]))

from backend.main import app
from backend.routers.v2.models import (
    V2GenerationRequest,
    V2GenerationResponse,
    V2GenerationStatus
)


class TestV2ScenarioAPI:
    """v2 시나리오 생성 API 테스트 클래스"""
    
    @pytest.fixture
    def client(self):
        """테스트 클라이언트 fixture"""
        return TestClient(app)
    
    @pytest.fixture
    def sample_request(self):
        """테스트용 요청 데이터 fixture"""
        return {
            "client_id": "test_client_12345",
            "repo_path": "/test/repo/path",
            "use_performance_mode": True
        }
    
    def test_generate_endpoint_success(self, client, sample_request):
        """정상적인 생성 요청 테스트"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_dir', return_value=True):
            
            response = client.post("/api/v2/scenario/generate", json=sample_request)
            
            assert response.status_code == 200
            data = response.json()
            
            # 응답 구조 검증
            assert "client_id" in data
            assert "status" in data
            assert "message" in data
            assert "websocket_url" in data
            
            # 값 검증
            assert data["client_id"] == sample_request["client_id"]
            assert data["status"] == "accepted"
            assert "ws://localhost:8000/api/v2/ws/progress/" in data["websocket_url"]
    
    def test_generate_endpoint_invalid_repo_path(self, client):
        """잘못된 저장소 경로 테스트"""
        invalid_request = {
            "client_id": "test_client_12345",
            "repo_path": "/nonexistent/path",
            "use_performance_mode": True
        }
        
        with patch('pathlib.Path.exists', return_value=False):
            response = client.post("/api/v2/scenario/generate", json=invalid_request)
            
            # 백그라운드 작업에서 처리되므로 일단은 200으로 응답하고 WebSocket으로 오류 전송
            assert response.status_code == 200
    
    def test_generate_endpoint_duplicate_client_id(self, client, sample_request):
        """중복 클라이언트 ID 테스트"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_dir', return_value=True):
            
            # 첫 번째 요청
            response1 = client.post("/api/v2/scenario/generate", json=sample_request)
            assert response1.status_code == 200
            
            # 동일한 클라이언트 ID로 두 번째 요청
            response2 = client.post("/api/v2/scenario/generate", json=sample_request)
            
            # 중복 요청은 409 Conflict로 응답해야 함
            assert response2.status_code == 409
            data = response2.json()
            assert "이미 진행 중인 작업" in data["detail"]
    
    def test_generate_endpoint_missing_fields(self, client):
        """필수 필드 누락 테스트"""
        incomplete_request = {
            "client_id": "test_client_12345"
            # repo_path 누락
        }
        
        response = client.post("/api/v2/scenario/generate", json=incomplete_request)
        assert response.status_code == 422  # Validation error
    
    def test_generate_endpoint_invalid_json(self, client):
        """잘못된 JSON 형식 테스트"""
        response = client.post(
            "/api/v2/scenario/generate", 
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_status_endpoint(self, client):
        """상태 조회 엔드포인트 테스트"""
        client_id = "test_status_client"
        
        response = client.get(f"/api/v2/scenario/status/{client_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["client_id"] == client_id
        assert data["is_generating"] is False
        assert data["is_websocket_connected"] is False
        assert data["status"] == "idle"
    
    def test_status_endpoint_active_generation(self, client, sample_request):
        """활성 생성 작업이 있는 상태 조회 테스트"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_dir', return_value=True):
            
            # 생성 작업 시작
            response = client.post("/api/v2/scenario/generate", json=sample_request)
            assert response.status_code == 200
            
            # 상태 조회
            status_response = client.get(f"/api/v2/scenario/status/{sample_request['client_id']}")
            assert status_response.status_code == 200
            
            data = status_response.json()
            assert data["is_generating"] is True
            assert data["status"] == "generating"


class TestV2Models:
    """v2 데이터 모델 테스트 클래스"""
    
    def test_v2_generation_request_validation(self):
        """V2GenerationRequest 모델 유효성 검증 테스트"""
        # 정상적인 요청
        valid_data = {
            "client_id": "test_client_123",
            "repo_path": "/test/path",
            "use_performance_mode": True
        }
        request = V2GenerationRequest(**valid_data)
        assert request.client_id == "test_client_123"
        assert request.repo_path == "/test/path"
        assert request.use_performance_mode is True
    
    def test_v2_generation_request_defaults(self):
        """V2GenerationRequest 기본값 테스트"""
        minimal_data = {
            "client_id": "test_client_123",
            "repo_path": "/test/path"
        }
        request = V2GenerationRequest(**minimal_data)
        assert request.use_performance_mode is True  # 기본값
    
    def test_v2_generation_request_missing_required_fields(self):
        """V2GenerationRequest 필수 필드 누락 테스트"""
        with pytest.raises(ValueError):
            V2GenerationRequest(client_id="test")  # repo_path 누락
        
        with pytest.raises(ValueError):
            V2GenerationRequest(repo_path="/test/path")  # client_id 누락
    
    def test_v2_generation_response_creation(self):
        """V2GenerationResponse 모델 생성 테스트"""
        response = V2GenerationResponse(
            client_id="test_client_123",
            websocket_url="ws://localhost:8000/api/v2/ws/progress/test_client_123"
        )
        
        assert response.client_id == "test_client_123"
        assert response.status == "accepted"  # 기본값
        assert response.message == "생성 작업이 시작되었습니다."  # 기본값
        assert "ws://localhost:8000" in response.websocket_url


class TestV2BackgroundGeneration:
    """v2 백그라운드 생성 로직 테스트"""
    
    @pytest.mark.asyncio
    async def test_handle_v2_generation_success_flow(self):
        """성공적인 생성 플로우 테스트 (모킹)"""
        from backend.routers.v2.scenario_v2 import _handle_v2_generation
        from backend.routers.v2.models import V2GenerationRequest
        
        request = V2GenerationRequest(
            client_id="test_flow_client",
            repo_path="/test/repo",
            use_performance_mode=True
        )
        
        # 모든 의존성 모킹
        with patch('backend.routers.v2.scenario_v2.v2_connection_manager.send_progress') as mock_send, \
             patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_dir', return_value=True), \
             patch('src.config_loader.load_config', return_value={"model_name": "test_model", "timeout": 60}), \
             patch('src.git_analyzer.get_git_analysis_text', return_value="test git analysis"), \
             patch('src.prompt_loader.add_git_analysis_to_rag', return_value=5), \
             patch('src.prompt_loader.create_final_prompt', return_value="test prompt"), \
             patch('src.llm_handler.call_ollama_llm', return_value="<json>{'test': 'result'}</json>"), \
             patch('src.excel_writer.save_results_to_excel', return_value="/test/output.xlsx"):
            
            # 생성 로직 실행 (예외가 발생하지 않으면 성공)
            await _handle_v2_generation("test_flow_client", request)
            
            # send_progress가 여러 번 호출되었는지 확인 (각 단계별로)
            assert mock_send.call_count >= 5  # 최소 5단계 (수신, 분석, RAG, LLM, 완료)
    
    @pytest.mark.asyncio
    async def test_handle_v2_generation_git_analysis_failure(self):
        """Git 분석 실패 테스트"""
        from backend.routers.v2.scenario_v2 import _handle_v2_generation
        from backend.routers.v2.models import V2GenerationRequest
        
        request = V2GenerationRequest(
            client_id="test_fail_client",
            repo_path="/test/repo",
            use_performance_mode=True
        )
        
        with patch('backend.routers.v2.scenario_v2.v2_connection_manager.send_progress') as mock_send, \
             patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_dir', return_value=True), \
             patch('src.config_loader.load_config', return_value={"model_name": "test_model"}), \
             patch('src.git_analyzer.get_git_analysis_text', return_value=""):  # 빈 분석 결과
            
            # 생성 로직 실행 (오류 처리 확인)
            await _handle_v2_generation("test_fail_client", request)
            
            # 오류 메시지가 전송되었는지 확인
            error_calls = [call for call in mock_send.call_args_list if 'ERROR' in str(call)]
            assert len(error_calls) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])