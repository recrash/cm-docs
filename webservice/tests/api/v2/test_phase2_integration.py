"""
Phase 2 통합 테스트

전체 문서 생성 워크플로우의 통합 테스트
"""

import pytest
import asyncio
import json
import base64
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.api.routers.v2.models import FullGenerationRequest


class TestPhase2Integration:
    """Phase 2 통합 테스트"""
    
    @pytest.fixture
    def client(self):
        """테스트 클라이언트"""
        return TestClient(app)
    
    @pytest.fixture
    def sample_metadata(self):
        """샘플 메타데이터"""
        return {
            "change_id": "CM-20240101-PHASE2",
            "system": "Phase2테스트시스템",
            "title": "Phase 2 통합 테스트",
            "requester": "테스트개발자",
            "request_dept": "QA팀"
        }
    
    @pytest.fixture
    def sample_full_generation_request(self, sample_metadata):
        """전체 문서 생성 요청 샘플"""
        return {
            "session_id": "test_session_20240101_123456",
            "vcs_analysis_text": "테스트 변경사항:\n- Phase 2 기능 추가\n- CLI 확장\n- API 오케스트레이션",
            "metadata_json": sample_metadata
        }
    
    def test_start_full_generation_success(self, client, sample_full_generation_request):
        """전체 문서 생성 시작 성공 테스트"""
        response = client.post(
            "/api/webservice/v2/start-full-generation",
            json=sample_full_generation_request
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["session_id"] == sample_full_generation_request["session_id"]
        assert data["status"] == "accepted"
        assert "전체 문서 생성 작업이 시작되었습니다" in data["message"]
    
    def test_start_full_generation_invalid_request(self, client):
        """잘못된 요청 테스트"""
        invalid_request = {
            "session_id": "",  # 빈 session_id
            "vcs_analysis_text": "테스트",
            # metadata_json 누락
        }
        
        response = client.post(
            "/api/webservice/v2/start-full-generation",
            json=invalid_request
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_get_full_generation_status_not_found(self, client):
        """존재하지 않는 세션 상태 조회 테스트"""
        response = client.get("/api/webservice/v2/full-generation-status/nonexistent_session")
        
        assert response.status_code == 404
        assert "세션을 찾을 수 없습니다" in response.json()["detail"]
    
    def test_get_full_generation_status_existing_session(self, client, sample_full_generation_request):
        """존재하는 세션 상태 조회 테스트"""
        # 먼저 세션 생성
        start_response = client.post(
            "/api/webservice/v2/start-full-generation",
            json=sample_full_generation_request
        )
        assert start_response.status_code == 200
        
        session_id = sample_full_generation_request["session_id"]
        
        # 상태 조회
        status_response = client.get(f"/api/webservice/v2/full-generation-status/{session_id}")
        
        assert status_response.status_code == 200
        status_data = status_response.json()
        
        assert status_data["session_id"] == session_id
        assert "status" in status_data
        assert "current_step" in status_data
        assert "steps_completed" in status_data
        assert "total_steps" in status_data
        assert "progress" in status_data
    
    @patch('app.services.autodoc_client.AutoDocClient')
    @patch('app.core.llm_handler.LLMHandler')
    def test_full_generation_workflow_mock(self, mock_llm_handler, mock_autodoc_client, client, sample_full_generation_request):
        """전체 워크플로우 모킹 테스트"""
        # LLM 핸들러 모킹
        mock_llm = MagicMock()
        mock_llm.generate_scenarios_async.return_value = {
            "test_cases": [{"case": "테스트 케이스 1"}],
            "description": "모킹된 시나리오 설명"
        }
        mock_llm_handler.return_value = mock_llm
        
        # AutoDoc 클라이언트 모킹
        mock_client = AsyncMock()
        mock_client.build_cm_word.return_value = {"ok": True, "filename": "test_word.docx"}
        mock_client.build_cm_list.return_value = {"ok": True, "filename": "test_list.xlsx"}
        mock_client.build_base_scenario.return_value = {"ok": True, "filename": "test_base.xlsx"}
        
        mock_autodoc_client.return_value.__aenter__.return_value = mock_client
        
        # Excel 생성 모킹
        with patch('app.core.excel_writer.create_excel_file') as mock_excel_writer:
            mock_excel_writer.return_value = "test_scenario.xlsx"
            
            # 전체 문서 생성 시작
            response = client.post(
                "/api/webservice/v2/start-full-generation",
                json=sample_full_generation_request
            )
            
            assert response.status_code == 200
            session_id = sample_full_generation_request["session_id"]
            
            # 잠시 기다려서 백그라운드 작업이 진행되도록 함
            import time
            time.sleep(0.5)
            
            # 상태 확인
            status_response = client.get(f"/api/webservice/v2/full-generation-status/{session_id}")
            assert status_response.status_code == 200
    
    def test_pydantic_model_validation(self, sample_metadata):
        """Pydantic 모델 검증 테스트"""
        # 유효한 요청
        valid_request = FullGenerationRequest(
            session_id="test_session_123",
            vcs_analysis_text="테스트 분석",
            metadata_json=sample_metadata
        )
        
        assert valid_request.session_id == "test_session_123"
        assert valid_request.vcs_analysis_text == "테스트 분석"
        assert valid_request.metadata_json == sample_metadata
        
        # 잘못된 요청 (빈 session_id)
        with pytest.raises(ValueError):
            FullGenerationRequest(
                session_id="",
                vcs_analysis_text="테스트 분석",
                metadata_json=sample_metadata
            )
    
    def test_cli_integration_scenario(self):
        """CLI 통합 시나리오 테스트 (단위 테스트 수준)"""
        # CLI에서 보낼 URL 파라미터 시뮬레이션
        metadata_dict = {
            "change_id": "CM-CLI-TEST",
            "system": "CLI테스트시스템",
            "title": "CLI 통합 테스트"
        }
        metadata_json = json.dumps(metadata_dict, ensure_ascii=False)
        metadata_b64 = base64.b64encode(metadata_json.encode('utf-8')).decode('ascii')
        
        # URL 파라미터 파싱 시뮬레이션
        import urllib.parse
        test_url = f"testscenariomaker:///test/repo?sessionId=cli_session_123&metadata={metadata_b64}"
        parsed = urllib.parse.urlparse(test_url)
        query_params = urllib.parse.parse_qs(parsed.query)
        
        # 파라미터 검증
        assert query_params.get('sessionId', [None])[0] == "cli_session_123"
        assert 'metadata' in query_params
        
        # Base64 디코딩 검증
        decoded_metadata = base64.b64decode(query_params['metadata'][0]).decode('utf-8')
        parsed_metadata = json.loads(decoded_metadata)
        
        assert parsed_metadata["change_id"] == "CM-CLI-TEST"
        assert parsed_metadata["system"] == "CLI테스트시스템"
    
    @pytest.mark.asyncio
    async def test_websocket_integration_mock(self, sample_full_generation_request):
        """WebSocket 통합 테스트 (모킹)"""
        from app.api.routers.v2.full_generation_websocket import (
            generate_download_urls,
            get_status_message
        )
        from app.api.routers.v2.models import FullGenerationStatus
        
        # 다운로드 URL 생성 테스트
        results = {
            "word_filename": "test_word.docx",
            "excel_list_filename": "test_list.xlsx",
            "base_scenario_filename": "test_base.xlsx",
            "merged_excel_filename": "test_merged.xlsx"
        }
        
        download_urls = generate_download_urls(results)
        
        assert "/api/autodoc/download/test_word.docx" in download_urls["word"]
        assert "/api/autodoc/download/test_list.xlsx" in download_urls["excel_list"]
        assert "/api/autodoc/download/test_base.xlsx" in download_urls["base_scenario"]
        assert "/api/autodoc/download/test_merged.xlsx" in download_urls["merged_excel"]
        
        # 상태 메시지 테스트
        assert get_status_message(FullGenerationStatus.RECEIVED) == "요청을 수신했습니다"
        assert get_status_message(FullGenerationStatus.COMPLETED) == "모든 문서 생성이 완료되었습니다"
        assert get_status_message(FullGenerationStatus.ERROR) == "문서 생성 중 오류가 발생했습니다"
    
    def test_api_documentation_integration(self, client):
        """API 문서 통합 테스트 - Phase 2 엔드포인트가 포함되는지 확인"""
        # OpenAPI 스키마 조회
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        paths = schema.get("paths", {})
        
        # Phase 2 엔드포인트가 스키마에 포함되는지 확인
        assert "/api/webservice/v2/start-full-generation" in paths
        assert "/api/webservice/v2/full-generation-status/{session_id}" in paths
        
        # WebSocket 엔드포인트도 포함되는지 확인 (선택사항)
        # WebSocket은 OpenAPI 3.0에서 표준이 아니므로 구현에 따라 다를 수 있음


if __name__ == "__main__":
    # 개별 실행 시 테스트 실행
    pytest.main([__file__, "-v"])