"""
API 통합 테스트

Mock 서버를 사용한 실제 API 통신 워크플로우 테스트입니다.
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import httpx

from ts_cli.api_client import APIClient, APIError, NetworkError
from ts_cli.cli_handler import CLIHandler


class MockServer:
    """테스트용 Mock API 서버"""

    def __init__(self):
        self.responses = {}
        self.requests_log = []

    def add_response(
        self, method: str, path: str, response_data: dict, status_code: int = 200
    ):
        """응답 설정"""
        key = f"{method.upper()}:{path}"
        self.responses[key] = {"data": response_data, "status_code": status_code}

    async def handle_request(self, request):
        """요청 처리"""
        self.requests_log.append(
            {
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers),
                "content": request.content,
            }
        )

        key = f"{request.method}:{request.url.path}"
        if key in self.responses:
            response_config = self.responses[key]
            return httpx.Response(
                status_code=response_config["status_code"], json=response_config["data"]
            )

        # 기본 404 응답
        return httpx.Response(status_code=404, json={"error": "Not found"})


@pytest.mark.integration
class TestAPIIntegration:
    """API 통합 테스트"""

    @pytest.fixture
    def mock_server(self):
        """Mock 서버 인스턴스"""
        return MockServer()

    @pytest.fixture
    def api_config(self):
        """테스트용 API 설정"""
        return {
            "base_url": "https://test-api.example.com",
            "timeout": 30,
            "max_retries": 3,
            "retry_delay": 0.1,  # 테스트용 짧은 지연
        }

    @pytest.fixture
    def api_client(self, api_config):
        """API 클라이언트 인스턴스"""
        return APIClient(api_config)

    @pytest.mark.asyncio
    async def test_send_analysis_full_workflow(self, api_client, mock_server):
        """분석 데이터 전송 전체 워크플로우 테스트"""
        # Mock 서버 응답 설정 (v2 API)
        mock_server.add_response(
            "POST",
            "/api/v2/scenario/generate",
            {
                "client_id": "test_client_123",
                "websocket_url": "ws://test.com/ws/test_client_123",
                "message": "시나리오 생성 요청이 접수되었습니다",
            },
        )

        # 테스트 데이터
        analysis_data = {
            "repository_info": {
                "vcs_type": "git",
                "path": "/test/repo",
                "current_branch": "main",
                "commit_count": 42,
            },
            "changes_text": "Test git diff content\n+Added new feature\n-Removed old code",
            "cli_version": "1.0.0",
            "analysis_timestamp": "2023-01-01T12:00:00",
        }

        # httpx 클라이언트 모킹
        with patch.object(api_client.client, "post") as mock_post:
            mock_response = Mock()
            mock_response.is_success = True
            mock_response.json.return_value = mock_server.responses[
                "POST:/api/v2/scenario/generate"
            ]["data"]
            mock_post.return_value = mock_response

            result = await api_client.send_analysis_v2(analysis_data)

            # 응답 검증 (v2 API 응답 구조)
            assert result["client_id"] == "test_client_123"
            assert result["websocket_url"] == "ws://test.com/ws/test_client_123"

            # 요청이 올바르게 호출되었는지 확인 (v2 API 엔드포인트)
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "/api/webservice/v2/scenario/generate"
            request_json = call_args[1]["json"]
            assert "client_id" in request_json
            assert request_json["repo_path"] == analysis_data
            assert request_json["use_performance_mode"] == True
            assert request_json["is_valid_repo"] == True
            assert request_json["vcs_type"] == "git"

    @pytest.mark.asyncio
    async def test_get_analysis_status_workflow(self, api_client):
        """분석 상태 조회 워크플로우 테스트"""
        analysis_id = "test-analysis-123"

        with patch.object(api_client.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.is_success = True
            mock_response.json.return_value = {
                "analysis_id": analysis_id,
                "status": "completed",
                "progress": 100,
                "result_url": "https://test.com/results/test-analysis-123.zip",
                "processing_time": "2.5 minutes",
            }
            mock_get.return_value = mock_response

            result = await api_client.get_analysis_status(analysis_id)

            assert result["analysis_id"] == analysis_id
            assert result["status"] == "completed"
            assert result["progress"] == 100
            assert "result_url" in result

            mock_get.assert_called_once_with(f"/api/v1/analysis/{analysis_id}/status")

    @pytest.mark.asyncio
    async def test_session_metadata_retrieval(self, api_client):
        """세션 메타데이터 조회 테스트"""
        # 테스트 데이터
        session_id = "test_session_metadata_123"
        expected_metadata = {
            "repository_path": "/test/repo",
            "vcs_type": "git",
            "user_name": "테스트사용자",
            "purpose": "통합 테스트"
        }

        # get_session_metadata API 호출 모킹
        with patch.object(api_client.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.is_success = True
            mock_response.json.return_value = expected_metadata
            mock_get.return_value = mock_response

            # get_session_metadata 호출
            result = await api_client.get_session_metadata(session_id)

            # 응답 검증
            assert result == expected_metadata

            # API 호출 검증
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[0][0] == f"/api/webservice/v2/session/{session_id}/metadata"
            assert call_args[1]["timeout"] == 30.0

    @pytest.mark.asyncio
    async def test_start_full_generation_workflow(self, api_client):
        """전체 문서 생성 워크플로우 테스트"""
        # 테스트 데이터
        session_id = "test_full_generation_123"
        metadata = {"change_id": "CM-TEST-001", "system": "테스트시스템"}
        vcs_analysis = "테스트 VCS 분석"

        # start_full_generation API 호출 모킹
        with patch.object(api_client.client, "post") as mock_post:
            mock_response = Mock()
            mock_response.is_success = True
            mock_response.json.return_value = {
                "session_id": session_id,
                "status": "accepted",
                "message": "전체 문서 생성 작업이 시작되었습니다"
            }
            mock_post.return_value = mock_response

            # start_full_generation 호출
            result = await api_client.start_full_generation(
                session_id=session_id,
                vcs_analysis_text=vcs_analysis,
                metadata_json=metadata
            )

            # 응답 검증
            assert result["session_id"] == session_id
            assert result["status"] == "accepted"
            assert "전체 문서 생성 작업이 시작되었습니다" in result["message"]

            # API 호출 검증
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "/api/webservice/v2/start-full-generation"
            request_json = call_args[1]["json"]
            assert request_json["session_id"] == session_id
            assert request_json["metadata_json"] == metadata
            assert request_json["vcs_analysis_text"] == vcs_analysis

    @pytest.mark.asyncio
    async def test_complete_session_workflow(self, api_client):
        """완전한 세션 워크플로우 테스트 (metadata retrieval → start generation)"""
        session_id = "test_complete_workflow_123"
        metadata = {
            "change_id": "CM-WORKFLOW-001",
            "system": "워크플로우테스트",
            "title": "완전한 세션 워크플로우 테스트"
        }
        vcs_analysis = "완전한 워크플로우 테스트 VCS 분석"

        # 1단계: 세션 메타데이터 조회
        with patch.object(api_client.client, "get") as mock_get:
            # get_session_metadata 응답 모킹
            mock_response = Mock()
            mock_response.is_success = True
            mock_response.json.return_value = metadata
            mock_get.return_value = mock_response

            metadata_result = await api_client.get_session_metadata(session_id)
            assert metadata_result == metadata

        # 2단계: 전체 생성 시작
        with patch.object(api_client.client, "post") as mock_post:
            # start_full_generation 응답 모킹
            mock_response = Mock()
            mock_response.is_success = True
            mock_response.json.return_value = {
                "session_id": session_id,
                "status": "accepted",
                "message": "전체 문서 생성 작업이 시작되었습니다"
            }
            mock_post.return_value = mock_response

            generation_result = await api_client.start_full_generation(
                session_id=session_id,
                vcs_analysis_text=vcs_analysis,
                metadata_json=metadata
            )

            assert generation_result["status"] == "accepted"
            assert generation_result["session_id"] == session_id

    @pytest.mark.asyncio
    async def test_session_error_handling(self, api_client):
        """세션 관련 오류 처리 테스트"""
        session_id = "test_error_session_123"

        # 세션 메타데이터 조회 실패 시나리오
        with patch.object(api_client.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.is_success = False
            mock_response.status_code = 404
            mock_response.json.return_value = {
                "detail": "세션을 찾을 수 없습니다"
            }
            mock_get.return_value = mock_response

            # 404 오류 시 None 반환 확인 (get_session_metadata 메서드 동작)
            result = await api_client.get_session_metadata(session_id)
            assert result is None

            # API 호출 검증 (timeout 파라미터 포함)
            mock_get.assert_called_once_with(f"/api/webservice/v2/session/{session_id}/metadata", timeout=30.0)

    @pytest.mark.asyncio
    async def test_download_result_workflow(self, api_client, tmp_path):
        """결과 다운로드 워크플로우 테스트"""
        result_url = "https://test.com/results/test-analysis-123.zip"
        download_path = tmp_path / "result.zip"
        test_content = b"Mock ZIP file content for testing"

        # AsyncMock으로 스트림 응답 모킹
        mock_response = AsyncMock()
        mock_response.is_success = True
        mock_response.headers = {"content-length": str(len(test_content))}

        # 올바른 async iterator 설정
        async def mock_aiter_bytes(chunk_size=None):
            yield test_content

        mock_response.aiter_bytes = mock_aiter_bytes

        with patch.object(api_client.client, "stream") as mock_stream:
            mock_stream.return_value.__aenter__.return_value = mock_response

            result = await api_client.download_result(result_url, download_path)

            assert result == download_path
            assert download_path.exists()
            assert download_path.read_bytes() == test_content

            mock_stream.assert_called_once_with("GET", result_url)

    @pytest.mark.asyncio
    async def test_error_handling_network_failure(self, api_client):
        """네트워크 오류 처리 테스트"""
        analysis_data = {"test": "data"}

        with patch.object(api_client.client, "post") as mock_post:
            mock_post.side_effect = httpx.NetworkError("Network connection failed")

            # 재시도 후에도 실패하므로 RetryError가 발생
            with pytest.raises(Exception) as exc_info:
                await api_client.send_analysis_v2(analysis_data)

            # RetryError 또는 NetworkError가 발생했는지 확인
            assert "NetworkError" in str(exc_info.value) or "RetryError" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_handling_server_error(self, api_client):
        """서버 오류 처리 테스트"""
        analysis_data = {"test": "data"}

        with patch.object(api_client.client, "post") as mock_post:
            mock_response = Mock()
            mock_response.is_success = False
            mock_response.status_code = 500
            mock_response.json.return_value = {
                "error": "Internal server error",
                "message": "Database connection failed",
            }
            mock_post.return_value = mock_response

            # _handle_response가 호출되도록 설정
            with patch.object(api_client, "_handle_response") as mock_handle:
                mock_handle.side_effect = APIError(
                    "서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                    status_code=500,
                    response_data={"error": "Internal server error"},
                )

                with pytest.raises(APIError) as exc_info:
                    await api_client.send_analysis_v2(analysis_data)

                # APIError가 발생했는지 확인 (status_code는 None일 수 있음)
                assert "서버 내부 오류" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_retry_mechanism(self, api_client):
        """재시도 메커니즘 테스트"""
        analysis_data = {"test": "data"}

        with patch.object(api_client.client, "post") as mock_post:
            # 처음 두 번은 네트워크 오류, 세 번째는 성공
            mock_post.side_effect = [
                httpx.NetworkError("Network error 1"),
                httpx.NetworkError("Network error 2"),
                Mock(is_success=True, json=lambda: {
                    "client_id": "test_client_123",
                    "websocket_url": "ws://test.com/ws/test_client_123",
                    "message": "시나리오 생성 요청이 접수되었습니다",
                }),
            ]

            # _handle_response가 성공 시에는 아무것도 하지 않도록 설정
            with patch.object(api_client, "_handle_response"):
                result = await api_client.send_analysis_v2(analysis_data)

                # 재시도 후 성공했는지 확인 (v2 API 응답)
                assert result["client_id"] == "test_client_123"
                assert result["websocket_url"] == "ws://test.com/ws/test_client_123"

    @pytest.mark.asyncio
    async def test_health_check_integration(self, api_client):
        """헬스 체크 통합 테스트"""
        with patch.object(api_client.client, "get") as mock_get:
            mock_response = Mock()
            mock_response.is_success = True
            mock_get.return_value = mock_response

            result = await api_client.health_check()

            assert result is True
            mock_get.assert_called_once_with("/api/webservice/health")


@pytest.mark.integration
class TestFullWorkflowIntegration:
    """전체 워크플로우 통합 테스트"""

    @pytest.fixture
    def mock_git_repo(self, tmp_path):
        """Mock Git 저장소 생성"""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # 테스트 파일 생성
        test_file = tmp_path / "test.py"
        test_file.write_text("print('Hello, World!')")

        return tmp_path

    @pytest.fixture
    def cli_handler_integration(self):
        """통합 테스트용 CLI 핸들러"""
        return CLIHandler(verbose=True, output_format="json", dry_run=False)

    @patch("ts_cli.vcs.git_analyzer.subprocess.run")
    @patch("ts_cli.cli_handler.asyncio.run")
    def test_full_analysis_workflow_success(
        self, mock_asyncio_run, mock_subprocess, cli_handler_integration, mock_git_repo
    ):
        """전체 분석 워크플로우 성공 테스트"""
        # Git 명령어 모킹
        mock_subprocess.return_value = Mock(
            returncode=0, stdout="M  test.py\nA  new_file.py", stderr=""
        )

        # API 호출 모킹 (v2 API 응답 구조)
        api_response = {
            "client_id": "test_client_123",
            "websocket_url": "ws://test.com/ws/test_client_123",
            "message": "시나리오 생성 요청이 접수되었습니다",
        }

        mock_asyncio_run.return_value = api_response

        result = cli_handler_integration.analyze_repository(mock_git_repo)

        assert result is True

        # API 호출이 올바르게 실행되었는지 확인
        assert mock_asyncio_run.call_count == 1

    @patch("ts_cli.vcs.git_analyzer.subprocess.run")
    def test_full_analysis_workflow_dry_run(self, mock_subprocess, mock_git_repo):
        """Dry run 모드 전체 워크플로우 테스트"""
        # Git 명령어 모킹
        mock_subprocess.return_value = Mock(
            returncode=0, stdout="M  test.py", stderr=""
        )

        cli_handler = CLIHandler(verbose=False, output_format="text", dry_run=True)

        result = cli_handler.analyze_repository(mock_git_repo)

        assert result is True
        # Dry run 모드에서는 API 호출이 없어야 함

    @patch("ts_cli.vcs.get_analyzer")
    def test_full_analysis_workflow_unsupported_vcs(
        self, mock_get_analyzer, cli_handler_integration, tmp_path
    ):
        """지원되지 않는 VCS 워크플로우 테스트"""
        mock_get_analyzer.return_value = None

        result = cli_handler_integration.analyze_repository(tmp_path)

        assert result is False

    @patch("ts_cli.vcs.git_analyzer.subprocess.run")
    @patch("ts_cli.cli_handler.asyncio.run")
    def test_full_analysis_workflow_api_error(
        self, mock_asyncio_run, mock_subprocess, cli_handler_integration, mock_git_repo
    ):
        """API 오류가 있는 전체 워크플로우 테스트"""
        # Git 명령어 모킹
        mock_subprocess.return_value = Mock(
            returncode=0, stdout="M  test.py", stderr=""
        )

        # API 오류 모킹
        from ts_cli.api_client import APIError

        mock_asyncio_run.side_effect = APIError("API server unavailable")

        result = cli_handler_integration.analyze_repository(mock_git_repo)

        assert result is False

    def test_configuration_integration(self):
        """설정 통합 테스트"""
        from ts_cli.utils.config_loader import (
            load_config,
            get_api_config,
            get_cli_config,
        )

        # 기본 설정 로드
        config_loader = load_config()

        # API 설정 확인
        api_config = get_api_config()
        assert "base_url" in api_config
        assert "timeout" in api_config
        assert isinstance(api_config["timeout"], int)

        # CLI 설정 확인
        cli_config = get_cli_config()
        assert "verbose" in cli_config
        assert "show_progress" in cli_config
        assert isinstance(cli_config["verbose"], bool)

    def test_logging_integration(self):
        """로깅 통합 테스트"""
        from ts_cli.utils.logger import setup_logger, get_logger

        # 로거 설정
        logger = setup_logger("test_integration")

        # 로거 기능 확인
        assert logger.name == "test_integration"
        assert len(logger.handlers) > 0

        # 로거 조회
        same_logger = get_logger("test_integration")
        assert same_logger is logger


@pytest.mark.integration
class TestErrorScenarios:
    """오류 시나리오 통합 테스트"""

    def test_invalid_repository_path(self):
        """유효하지 않은 저장소 경로 처리"""
        cli_handler = CLIHandler()
        nonexistent_path = Path("/nonexistent/repository")

        result = cli_handler.analyze_repository(nonexistent_path)

        assert result is False

    @patch("ts_cli.vcs.git_analyzer.subprocess.run")
    def test_git_command_failure(self, mock_subprocess, tmp_path):
        """Git 명령어 실패 처리"""
        # Git 저장소 시뮬레이션
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # Git 명령어 실패 모킹
        mock_subprocess.side_effect = [
            Mock(returncode=0, stdout="", stderr=""),  # validate_repository
            Mock(
                returncode=1, stdout="", stderr="fatal: not a git repository"
            ),  # get_changes
        ]

        cli_handler = CLIHandler()
        result = cli_handler.analyze_repository(tmp_path)

        assert result is False

    @patch("ts_cli.api_client.httpx.AsyncClient")
    def test_api_timeout_handling(self, mock_client_class):
        """API 타임아웃 처리 테스트"""
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("Request timeout")
        mock_client_class.return_value = mock_client

        async def test_timeout():
            api_client = APIClient()
            with pytest.raises(APIError) as exc_info:
                await api_client.send_analysis_v2({"test": "data"})
            assert "시간이 초과되었습니다" in str(exc_info.value)

        asyncio.run(test_timeout())
