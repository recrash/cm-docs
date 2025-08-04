"""
CLI 핸들러 단위 테스트

비즈니스 로직 핸들러의 테스트입니다.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path
import json

from ts_cli.cli_handler import CLIHandler
from ts_cli.vcs.base_analyzer import InvalidRepositoryError, RepositoryError
from ts_cli.api_client import APIError, NetworkError


class TestCLIHandler:
    """CLI 핸들러 테스트"""
    
    @pytest.fixture
    def cli_handler(self):
        """기본 CLI 핸들러 인스턴스"""
        return CLIHandler(verbose=False, output_format='text', dry_run=False)
    
    @pytest.fixture
    def cli_handler_verbose(self):
        """상세 모드 CLI 핸들러 인스턴스"""
        return CLIHandler(verbose=True, output_format='text', dry_run=False)
    
    @pytest.fixture
    def cli_handler_dry_run(self):
        """Dry run 모드 CLI 핸들러 인스턴스"""
        return CLIHandler(verbose=False, output_format='text', dry_run=True)
    
    @pytest.fixture
    def cli_handler_json(self):
        """JSON 출력 모드 CLI 핸들러 인스턴스"""
        return CLIHandler(verbose=False, output_format='json', dry_run=False)
    
    @pytest.fixture
    def mock_analyzer(self):
        """Mock VCS 분석기"""
        analyzer = Mock()
        analyzer.get_vcs_type.return_value = "git"
        analyzer.validate_repository.return_value = True
        analyzer.get_repository_info.return_value = {
            "vcs_type": "git",
            "path": "/test/repo",
            "current_branch": "main",
            "commit_count": 10,
            "has_changes": True
        }
        analyzer.get_changes.return_value = "Test changes content"
        return analyzer
    
    def test_cli_handler_initialization(self):
        """CLI 핸들러 초기화 테스트"""
        handler = CLIHandler(verbose=True, output_format='json', dry_run=True)
        
        assert handler.verbose is True
        assert handler.output_format == 'json'
        assert handler.dry_run is True
        assert handler._api_client is None  # 지연 초기화
    
    @patch('ts_cli.cli_handler.get_analyzer')
    def test_validate_repository_success(self, mock_get_analyzer, cli_handler, mock_analyzer, tmp_path):
        """저장소 유효성 검사 성공 테스트"""
        mock_get_analyzer.return_value = mock_analyzer
        
        result = cli_handler._validate_repository(tmp_path)
        
        assert result == mock_analyzer
        mock_get_analyzer.assert_called_once_with(tmp_path)
        mock_analyzer.validate_repository.assert_called_once()
    
    @patch('ts_cli.cli_handler.get_analyzer')
    def test_validate_repository_not_supported(self, mock_get_analyzer, cli_handler, tmp_path):
        """지원되지 않는 저장소 타입 테스트"""
        mock_get_analyzer.return_value = None
        
        result = cli_handler._validate_repository(tmp_path)
        
        assert result is None
    
    @patch('ts_cli.cli_handler.get_analyzer')
    def test_validate_repository_invalid(self, mock_get_analyzer, cli_handler, mock_analyzer, tmp_path):
        """유효하지 않은 저장소 테스트"""
        mock_analyzer.validate_repository.return_value = False
        mock_get_analyzer.return_value = mock_analyzer
        
        result = cli_handler._validate_repository(tmp_path)
        
        assert result is None
    
    def test_validate_repository_nonexistent_path(self, cli_handler):
        """존재하지 않는 경로 테스트"""
        nonexistent_path = Path("/nonexistent/path")
        
        result = cli_handler._validate_repository(nonexistent_path)
        
        assert result is None
    
    def test_analyze_changes_success(self, cli_handler, mock_analyzer):
        """변경사항 분석 성공 테스트"""
        result = cli_handler._analyze_changes(mock_analyzer)
        
        assert result is not None
        assert result["repository_info"] == mock_analyzer.get_repository_info.return_value
        assert result["changes_text"] == "Test changes content"
        assert "analysis_timestamp" in result
        assert "cli_version" in result
        
        mock_analyzer.get_repository_info.assert_called_once()
        mock_analyzer.get_changes.assert_called_once()
    
    def test_analyze_changes_repository_error(self, cli_handler, mock_analyzer):
        """저장소 오류 발생 테스트"""
        mock_analyzer.get_changes.side_effect = RepositoryError("Test error")
        
        result = cli_handler._analyze_changes(mock_analyzer)
        
        assert result is None
    
    def test_analyze_changes_exception(self, cli_handler, mock_analyzer):
        """예상치 못한 오류 발생 테스트"""
        mock_analyzer.get_changes.side_effect = Exception("Unexpected error")
        
        result = cli_handler._analyze_changes(mock_analyzer)
        
        assert result is None
    
    @patch('ts_cli.cli_handler.asyncio.run')
    def test_send_to_api_success(self, mock_asyncio_run, cli_handler):
        """API 전송 성공 테스트"""
        # Mock API 응답
        mock_response = {
            "analysis_id": "test-123",
            "status": "completed",
            "result_url": "https://example.com/result.zip"
        }
        mock_asyncio_run.return_value = mock_response
        
        analysis_result = {
            "repository_info": {"vcs_type": "git"},
            "changes_text": "test changes",
            "analysis_timestamp": "2023-01-01T00:00:00",
            "cli_version": "1.0.0"
        }
        
        result = cli_handler._send_to_api(analysis_result)
        
        assert result == mock_response
        mock_asyncio_run.assert_called_once()
    
    @patch('ts_cli.cli_handler.asyncio.run')
    def test_send_to_api_error(self, mock_asyncio_run, cli_handler):
        """API 전송 오류 테스트"""
        mock_asyncio_run.side_effect = APIError("API Error")
        
        analysis_result = {"test": "data"}
        result = cli_handler._send_to_api(analysis_result)
        
        assert result is None
    
    @patch('ts_cli.cli_handler.asyncio.run')
    def test_download_result_success(self, mock_asyncio_run, cli_handler):
        """결과 다운로드 성공 테스트"""
        mock_path = Path("/test/result.zip")
        mock_asyncio_run.return_value = mock_path
        
        api_response = {"result_url": "https://example.com/result.zip"}
        result = cli_handler._download_result(api_response)
        
        assert result is True
        assert api_response["download_path"] == str(mock_path)
    
    def test_download_result_no_url(self, cli_handler):
        """다운로드 URL이 없는 경우 테스트"""
        api_response = {}
        result = cli_handler._download_result(api_response)
        
        assert result is True  # 오류가 아니므로 True
    
    @patch('ts_cli.cli_handler.asyncio.run')
    def test_download_result_error(self, mock_asyncio_run, cli_handler):
        """결과 다운로드 오류 테스트"""
        mock_asyncio_run.side_effect = APIError("Download failed")
        
        api_response = {"result_url": "https://example.com/result.zip"}
        result = cli_handler._download_result(api_response)
        
        assert result is False
    
    def test_display_dry_run_result_text_format(self, cli_handler, capsys):
        """Dry run 결과 텍스트 형식 출력 테스트"""
        analysis_result = {
            "repository_info": {
                "path": "/test/repo",
                "vcs_type": "git",
                "current_branch": "main",
                "commit_count": 10
            },
            "changes_text": "Test changes"
        }
        
        cli_handler._display_dry_run_result(analysis_result)
        
        # 출력이 정상적으로 수행되었는지 확인 (Rich 출력은 직접 검증하기 어려움)
        # 주로 예외가 발생하지 않았는지 확인
    
    def test_display_dry_run_result_json_format(self, cli_handler_json):
        """Dry run 결과 JSON 형식 출력 테스트"""
        analysis_result = {
            "repository_info": {"vcs_type": "git"},
            "changes_text": "Test changes"
        }
        
        # JSON 출력 모드에서 예외가 발생하지 않는지 확인
        cli_handler_json._display_dry_run_result(analysis_result)
    
    def test_display_final_result_text_format(self, cli_handler):
        """최종 결과 텍스트 형식 출력 테스트"""
        api_response = {
            "analysis_id": "test-123",
            "status": "completed",
            "processing_time": "5.2s",
            "download_path": "/test/result.zip"
        }
        
        cli_handler._display_final_result(api_response)
    
    def test_display_final_result_json_format(self, cli_handler_json):
        """최종 결과 JSON 형식 출력 테스트"""
        api_response = {
            "analysis_id": "test-123",
            "status": "completed"
        }
        
        cli_handler_json._display_final_result(api_response)
    
    def test_get_current_timestamp(self, cli_handler):
        """현재 타임스탬프 생성 테스트"""
        timestamp = cli_handler._get_current_timestamp()
        
        assert isinstance(timestamp, str)
        assert "T" in timestamp  # ISO 형식 확인
    
    def test_get_cli_version(self, cli_handler):
        """CLI 버전 조회 테스트"""
        version = cli_handler._get_cli_version()
        
        assert isinstance(version, str)
        assert len(version) > 0
    
    @patch('ts_cli.cli_handler.CLIHandler._validate_repository')
    @patch('ts_cli.cli_handler.CLIHandler._analyze_changes')
    @patch('ts_cli.cli_handler.CLIHandler._display_dry_run_result')
    def test_analyze_repository_dry_run_success(
        self,
        mock_display,
        mock_analyze,
        mock_validate,
        cli_handler_dry_run,
        mock_analyzer,
        tmp_path
    ):
        """Dry run 모드 성공 테스트"""
        mock_validate.return_value = mock_analyzer
        mock_analyze.return_value = {"test": "data"}
        
        result = cli_handler_dry_run.analyze_repository(tmp_path)
        
        assert result is True
        mock_validate.assert_called_once_with(tmp_path)
        mock_analyze.assert_called_once_with(mock_analyzer)
        mock_display.assert_called_once()
    
    @patch('ts_cli.cli_handler.CLIHandler._validate_repository')
    def test_analyze_repository_validation_failure(
        self,
        mock_validate,
        cli_handler,
        tmp_path
    ):
        """저장소 검증 실패 테스트"""
        mock_validate.return_value = None
        
        result = cli_handler.analyze_repository(tmp_path)
        
        assert result is False
    
    @patch('ts_cli.cli_handler.CLIHandler._validate_repository')
    @patch('ts_cli.cli_handler.CLIHandler._analyze_changes')
    def test_analyze_repository_analysis_failure(
        self,
        mock_analyze,
        mock_validate,
        cli_handler,
        mock_analyzer,
        tmp_path
    ):
        """변경사항 분석 실패 테스트"""
        mock_validate.return_value = mock_analyzer
        mock_analyze.return_value = None
        
        result = cli_handler.analyze_repository(tmp_path)
        
        assert result is False
    
    @patch('ts_cli.cli_handler.CLIHandler._validate_repository')
    @patch('ts_cli.cli_handler.CLIHandler._analyze_changes')
    @patch('ts_cli.cli_handler.CLIHandler._send_to_api')
    @patch('ts_cli.cli_handler.CLIHandler._download_result')
    @patch('ts_cli.cli_handler.CLIHandler._display_final_result')
    def test_analyze_repository_full_success(
        self,
        mock_display,
        mock_download,
        mock_send,
        mock_analyze,
        mock_validate,
        cli_handler,
        mock_analyzer,
        tmp_path
    ):
        """전체 워크플로우 성공 테스트"""
        # Mock 설정
        mock_validate.return_value = mock_analyzer
        mock_analyze.return_value = {"test": "analysis"}
        mock_send.return_value = {"analysis_id": "test-123"}
        mock_download.return_value = True
        
        result = cli_handler.analyze_repository(tmp_path)
        
        assert result is True
        mock_validate.assert_called_once()
        mock_analyze.assert_called_once()
        mock_send.assert_called_once()
        mock_download.assert_called_once()
        mock_display.assert_called_once()
    
    @patch('ts_cli.cli_handler.CLIHandler._validate_repository')
    def test_analyze_repository_keyboard_interrupt(
        self,
        mock_validate,
        cli_handler,
        tmp_path
    ):
        """키보드 인터럽트 처리 테스트"""
        mock_validate.side_effect = KeyboardInterrupt()
        
        result = cli_handler.analyze_repository(tmp_path)
        
        assert result is False
    
    @patch('ts_cli.cli_handler.CLIHandler._validate_repository')
    def test_analyze_repository_unexpected_exception(
        self,
        mock_validate,
        cli_handler,
        tmp_path
    ):
        """예상치 못한 예외 처리 테스트"""
        mock_validate.side_effect = Exception("Unexpected error")
        
        result = cli_handler.analyze_repository(tmp_path)
        
        assert result is False
    
    def test_api_client_lazy_initialization(self, cli_handler):
        """API 클라이언트 지연 초기화 테스트"""
        # 처음에는 None
        assert cli_handler._api_client is None
        
        # 프로퍼티 접근시 초기화됨
        api_client = cli_handler.api_client
        assert api_client is not None
        assert cli_handler._api_client is api_client
        
        # 두 번째 접근시에는 같은 인스턴스 반환
        api_client2 = cli_handler.api_client
        assert api_client2 is api_client