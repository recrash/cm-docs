"""
API 클라이언트 단위 테스트

httpx 기반 API 클라이언트의 테스트입니다.
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import httpx

from ts_cli.api_client import (
    APIClient,
    APIError,
    NetworkError,
    AuthenticationError,
    ValidationError,
    test_connection_sync,
)


class TestAPIError:
    """API 오류 클래스 테스트"""

    def test_api_error_basic(self):
        """기본 API 오류 테스트"""
        error = APIError("Test error")

        assert str(error) == "API 오류: Test error"
        assert error.message == "Test error"
        assert error.status_code is None
        assert error.response_data == {}

    def test_api_error_with_status_code(self):
        """상태 코드가 있는 API 오류 테스트"""
        error = APIError("Test error", status_code=400)

        assert str(error) == "API 오류 (400): Test error"
        assert error.status_code == 400

    def test_api_error_with_response_data(self):
        """응답 데이터가 있는 API 오류 테스트"""
        response_data = {"error": "validation failed", "details": ["field required"]}
        error = APIError("Test error", response_data=response_data)

        assert error.response_data == response_data

    def test_network_error_inheritance(self):
        """NetworkError 상속 테스트"""
        error = NetworkError("Network failed")

        assert isinstance(error, APIError)
        assert "Network failed" in str(error)

    def test_authentication_error_inheritance(self):
        """AuthenticationError 상속 테스트"""
        error = AuthenticationError("Auth failed", status_code=401)

        assert isinstance(error, APIError)
        assert error.status_code == 401

    def test_validation_error_inheritance(self):
        """ValidationError 상속 테스트"""
        error = ValidationError("Validation failed", status_code=400)

        assert isinstance(error, APIError)
        assert error.status_code == 400


class TestAPIClient:
    """API 클라이언트 테스트"""

    @pytest.fixture
    def mock_config(self):
        """Mock API 설정"""
        return {
            "base_url": "https://test-api.example.com",
            "timeout": 30,
            "max_retries": 3,
            "retry_delay": 1.0,
        }

    @pytest.fixture
    def api_client(self, mock_config):
        """API 클라이언트 인스턴스"""
        return APIClient(mock_config)

    def test_api_client_initialization(self, mock_config):
        """API 클라이언트 초기화 테스트"""
        client = APIClient(mock_config)

        assert client.config == mock_config
        assert client.client.base_url == mock_config["base_url"]
        assert client.client.timeout.connect == mock_config["timeout"]

    @patch("ts_cli.api_client.get_api_config")
    def test_api_client_default_config(self, mock_get_config):
        """기본 설정으로 API 클라이언트 초기화 테스트"""
        default_config = {"base_url": "https://default.com", "timeout": 60}
        mock_get_config.return_value = default_config

        client = APIClient()

        assert client.config == default_config
        mock_get_config.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self, api_client):
        """비동기 컨텍스트 매니저 테스트"""
        async with api_client as client:
            assert client is api_client

        # 컨텍스트 매니저 종료 후 클라이언트가 닫혔는지 확인은
        # httpx 내부 구현에 의존하므로 생략

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_send_analysis_success(self, mock_post, api_client):
        """분석 데이터 전송 성공 테스트"""
        # Mock 응답 설정
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "analysis_id": "test-123",
            "status": "accepted",
            "message": "Analysis started",
        }
        mock_post.return_value = mock_response

        # 테스트 데이터
        analysis_data = {
            "repository_info": {"vcs_type": "git", "path": "/test/repo"},
            "changes_text": "Test changes",
            "cli_version": "1.0.0",
            "analysis_timestamp": "2023-01-01T00:00:00",
        }

        # 진행 상황 콜백 Mock
        progress_callback = Mock()

        result = await api_client.send_analysis(analysis_data, progress_callback)

        assert result["analysis_id"] == "test-123"
        assert result["status"] == "accepted"

        # 요청이 올바르게 호출되었는지 확인
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "/api/v1/analysis"

        # 진행 상황 콜백이 호출되었는지 확인
        assert progress_callback.call_count > 0

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_send_analysis_network_error(self, mock_post, api_client):
        """분석 데이터 전송 네트워크 오류 테스트"""
        mock_post.side_effect = httpx.NetworkError("Connection failed")

        analysis_data = {"test": "data"}

        with pytest.raises(NetworkError) as exc_info:
            await api_client.send_analysis(analysis_data)

        assert "네트워크 연결 오류" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_send_analysis_timeout(self, mock_post, api_client):
        """분석 데이터 전송 타임아웃 테스트"""
        mock_post.side_effect = httpx.TimeoutException("Request timeout")

        analysis_data = {"test": "data"}

        with pytest.raises(APIError) as exc_info:
            await api_client.send_analysis(analysis_data)

        assert "시간이 초과되었습니다" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_get_analysis_status_success(self, mock_get, api_client):
        """분석 상태 조회 성공 테스트"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "analysis_id": "test-123",
            "status": "completed",
            "progress": 100,
        }
        mock_get.return_value = mock_response

        result = await api_client.get_analysis_status("test-123")

        assert result["analysis_id"] == "test-123"
        assert result["status"] == "completed"

        mock_get.assert_called_once_with("/api/v1/analysis/test-123/status")

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.stream")
    async def test_download_result_success(self, mock_stream, api_client, tmp_path):
        """결과 파일 다운로드 성공 테스트"""
        # Mock 스트림 응답
        mock_response = AsyncMock()
        mock_response.is_success = True
        mock_response.headers = {"content-length": "1024"}

        # 올바른 async iterator 설정
        async def mock_aiter_bytes(chunk_size=None):
            yield b"test data chunk"

        mock_response.aiter_bytes = mock_aiter_bytes

        mock_stream.return_value.__aenter__.return_value = mock_response

        # 다운로드 경로
        download_path = tmp_path / "result.zip"

        result = await api_client.download_result(
            "https://example.com/result.zip", download_path
        )

        assert result == download_path
        assert download_path.exists()
        assert download_path.read_bytes() == b"test data chunk"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.stream")
    async def test_download_result_auto_path(self, mock_stream, api_client, tmp_path):
        """자동 경로 생성 다운로드 테스트"""
        mock_response = AsyncMock()
        mock_response.is_success = True
        mock_response.headers = {"content-length": "100"}

        # 올바른 async iterator 설정
        async def mock_aiter_bytes(chunk_size=None):
            yield b"data"

        mock_response.aiter_bytes = mock_aiter_bytes

        mock_stream.return_value.__aenter__.return_value = mock_response

        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = tmp_path

            result = await api_client.download_result("https://example.com/result.zip")

            assert result is not None
            assert str(result).startswith(str(tmp_path))
            assert str(result).endswith(".zip")

    @pytest.mark.asyncio
    async def test_handle_response_success(self, api_client):
        """응답 처리 성공 테스트"""
        mock_response = Mock()
        mock_response.is_success = True

        # 예외가 발생하지 않아야 함
        await api_client._handle_response(mock_response)

    @pytest.mark.asyncio
    async def test_handle_response_400_validation_error(self, api_client):
        """400 응답 처리 테스트"""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "message": "Validation failed",
            "details": ["field required"],
        }

        with pytest.raises(ValidationError) as exc_info:
            await api_client._handle_response(mock_response)

        assert exc_info.value.status_code == 400
        assert "Validation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_response_401_auth_error(self, api_client):
        """401 응답 처리 테스트"""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Unauthorized"}

        with pytest.raises(AuthenticationError) as exc_info:
            await api_client._handle_response(mock_response)

        assert exc_info.value.status_code == 401
        assert "인증이 필요합니다" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_response_403_auth_error(self, api_client):
        """403 응답 처리 테스트"""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 403
        mock_response.json.return_value = {"message": "Forbidden"}

        with pytest.raises(AuthenticationError) as exc_info:
            await api_client._handle_response(mock_response)

        assert exc_info.value.status_code == 403
        assert "접근 권한이 없습니다" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_response_404_error(self, api_client):
        """404 응답 처리 테스트"""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "Not found"}

        with pytest.raises(APIError) as exc_info:
            await api_client._handle_response(mock_response)

        assert exc_info.value.status_code == 404
        assert "찾을 수 없습니다" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_response_500_server_error(self, api_client):
        """500 응답 처리 테스트"""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 500
        mock_response.json.return_value = {"message": "Internal server error"}

        with pytest.raises(APIError) as exc_info:
            await api_client._handle_response(mock_response)

        assert exc_info.value.status_code == 500
        assert "서버 내부 오류" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_response_json_decode_error(self, api_client):
        """JSON 디코딩 오류 응답 처리 테스트"""
        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 400
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        with pytest.raises(APIError) as exc_info:
            await api_client._handle_response(mock_response)

        assert exc_info.value.status_code == 400
        assert "HTTP 400 오류" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_health_check_success(self, mock_get, api_client):
        """서버 상태 확인 성공 테스트"""
        mock_response = Mock()
        mock_response.is_success = True
        mock_get.return_value = mock_response

        result = await api_client.health_check()

        assert result is True
        mock_get.assert_called_once_with("/api/v1/health")

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_health_check_failure(self, mock_get, api_client):
        """서버 상태 확인 실패 테스트"""
        mock_get.side_effect = httpx.NetworkError("Connection failed")

        result = await api_client.health_check()

        assert result is False

    def test_get_timestamp(self, api_client):
        """타임스탬프 생성 테스트"""
        timestamp = api_client._get_timestamp()

        assert isinstance(timestamp, str)
        assert len(timestamp) == 15  # YYYYMMDD_HHMMSS 형식
        assert "_" in timestamp

    @pytest.mark.asyncio
    async def test_close(self, api_client):
        """클라이언트 종료 테스트"""
        with patch.object(api_client.client, "aclose") as mock_close:
            await api_client.close()
            mock_close.assert_called_once()


class TestConvenienceFunctions:
    """편의 함수 테스트"""

    @patch("ts_cli.api_client.APIClient")
    @patch("ts_cli.api_client.asyncio.run")
    def test_test_connection_sync_success(self, mock_asyncio_run, mock_api_client):
        """동기 연결 테스트 성공"""
        mock_asyncio_run.return_value = True

        result = test_connection_sync()

        assert result is True
        mock_asyncio_run.assert_called_once()

    @patch("ts_cli.api_client.APIClient")
    @patch("ts_cli.api_client.asyncio.run")
    def test_test_connection_sync_failure(self, mock_asyncio_run, mock_api_client):
        """동기 연결 테스트 실패"""
        mock_asyncio_run.return_value = False

        result = test_connection_sync()

        assert result is False
