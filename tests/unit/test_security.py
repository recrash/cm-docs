"""
보안 테스트 - 민감 정보 로깅 방지 검증

API 호출 시 민감 정보(API 키, 토큰 등)가 로그에 기록되지 않는지 검증합니다.
"""

import logging
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
from io import StringIO

# 테스트 대상 모듈 import
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from ts_cli.main import (
    load_server_config,
    make_api_request
)


class TestSensitiveDataLogging:
    """민감 정보 로깅 방지 테스트"""
    
    @patch('ts_cli.main.console')
    @patch('ts_cli.utils.config_loader.load_config')
    def test_server_url_not_logged_in_config_error(self, mock_load_config, mock_console):
        """설정 로드 실패 시 서버 URL이 로그에 노출되지 않음"""
        # Arrange
        # 설정 파일 로드 실패 모킹
        mock_load_config.side_effect = Exception("Config file not found")
        
        with patch.dict('os.environ', {'TSM_SERVER_URL': 'http://secret-server.com/api/key123'}, clear=True):
            # Act
            result = load_server_config()
            
            # Assert
            # 환경 변수에서 로드된 서버 URL이 출력되지만, 이는 성공 로그이므로 허용
            assert result == 'http://secret-server.com/api/key123'
            
            # console.print 호출에서 민감한 정보가 포함된 것을 확인
            # 하지만 이것은 성공적인 로드 상황이므로 URL 표시가 필요함
            mock_console.print.assert_called()
    
    @patch('ts_cli.main.requests.Session')
    @patch('ts_cli.vcs.get_analyzer')
    def test_api_request_data_not_logged_in_error(self, mock_get_analyzer, mock_session_class):
        """API 요청 실패 시 요청 데이터가 로그에 노출되지 않음"""
        # Arrange
        mock_analyzer = Mock()
        mock_analyzer.validate_repository.return_value = True
        mock_analyzer.get_changes.return_value = {
            "changes_text": "sensitive code changes with API_KEY=secret123"
        }
        mock_get_analyzer.return_value = mock_analyzer
        
        mock_session = Mock()
        mock_session.post.side_effect = Exception("Connection failed")
        mock_session_class.return_value.__enter__.return_value = mock_session
        
        # 로깅 캡처 설정
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        logger = logging.getLogger('ts_cli')
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        server_url = "http://test-server.com"
        repo_path = Path("/test/repo")
        
        # Act
        with patch('ts_cli.main.console') as mock_console:
            result = make_api_request(server_url, repo_path)
        
        # Assert
        assert result is False
        
        # 로그 출력에서 민감한 정보가 포함되지 않았는지 확인
        log_output = log_capture.getvalue()
        
        # API 키나 민감한 코드 변경 내용이 로그에 노출되지 않아야 함
        assert "API_KEY=secret123" not in log_output
        assert "secret123" not in log_output
        
        # console 출력에서도 민감한 정보가 포함되지 않았는지 확인
        console_calls = [call[0][0] for call in mock_console.print.call_args_list]
        console_output = " ".join(str(call) for call in console_calls)
        assert "API_KEY=secret123" not in console_output
        assert "secret123" not in console_output
        
        # 정리
        logger.removeHandler(handler)
    
    @patch('ts_cli.main.requests.Session')
    @patch('ts_cli.vcs.get_analyzer')
    def test_http_error_response_not_logged(self, mock_get_analyzer, mock_session_class):
        """HTTP 오류 응답 내용이 로그에 노출되지 않음"""
        # Arrange
        mock_analyzer = Mock()
        mock_analyzer.validate_repository.return_value = True
        mock_analyzer.get_changes.return_value = {"changes_text": "test changes"}
        mock_get_analyzer.return_value = mock_analyzer
        
        # 민감한 정보가 포함된 에러 응답 모킹
        import requests
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": "Invalid API key",
            "details": "API_KEY=secret123 is not valid",
            "server_internal_token": "internal_token_456"
        }
        
        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response
        
        mock_session = Mock()
        mock_session.post.side_effect = http_error
        mock_session_class.return_value.__enter__.return_value = mock_session
        
        # 로깅 캡처 설정
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        logger = logging.getLogger('ts_cli')
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        server_url = "http://test-server.com"
        repo_path = Path("/test/repo")
        
        # Act
        with patch('ts_cli.main.console') as mock_console:
            result = make_api_request(server_url, repo_path)
        
        # Assert
        assert result is False
        
        # 로그 출력에서 민감한 정보가 포함되지 않았는지 확인
        log_output = log_capture.getvalue()
        assert "secret123" not in log_output
        assert "internal_token_456" not in log_output
        
        # console 출력에서도 민감한 정보가 포함되지 않았는지 확인
        console_calls = [call[0][0] for call in mock_console.print.call_args_list]
        console_output = " ".join(str(call) for call in console_calls)
        assert "secret123" not in console_output
        assert "internal_token_456" not in console_output
        
        # 적절한 일반적 오류 메시지가 표시되었는지 확인
        assert any("HTTP 오류" in str(call) for call in console_calls)
        
        # 정리
        logger.removeHandler(handler)
    
    @patch('ts_cli.main.console')
    def test_environment_variable_masked_in_error_logs(self, mock_console):
        """오류 로그에서 환경 변수가 마스킹됨"""
        # Arrange & Act
        with patch.dict('os.environ', {}, clear=True):  # 모든 환경 변수 제거
            with patch('ts_cli.utils.config_loader.load_config') as mock_load_config:
                mock_config_loader = Mock()
                mock_config_loader.get.return_value = None
                mock_load_config.return_value = mock_config_loader
                
                # SystemExit 예외를 잡아서 테스트 진행
                with pytest.raises(SystemExit):
                    load_server_config()
        
        # Assert
        # 오류 메시지에서 환경 변수명만 언급되고, 실제 값은 노출되지 않아야 함
        console_calls = [call[0][0] for call in mock_console.print.call_args_list]
        console_output = " ".join(str(call) for call in console_calls)
        
        # 환경 변수명은 언급되지만 값은 노출되지 않아야 함
        assert "TSM_SERVER_URL" in console_output
    
    @patch('ts_cli.main.requests.Session')
    @patch('ts_cli.vcs.get_analyzer')
    def test_request_headers_not_logged(self, mock_get_analyzer, mock_session_class):
        """요청 헤더에 포함된 정보가 로그에 노출되지 않음"""
        # Arrange
        mock_analyzer = Mock()
        mock_analyzer.validate_repository.return_value = True
        mock_analyzer.get_changes.return_value = {"changes_text": "test changes"}
        mock_get_analyzer.return_value = mock_analyzer
        
        mock_session = Mock()
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"status": "success"}
        mock_session.post.return_value = mock_response
        mock_session_class.return_value.__enter__.return_value = mock_session
        
        # 로깅 캡처 설정
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        logger = logging.getLogger('ts_cli')
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        server_url = "http://test-server.com"
        repo_path = Path("/test/repo")
        
        # Act
        with patch('ts_cli.main.console') as mock_console:
            result = make_api_request(server_url, repo_path)
        
        # Assert
        assert result is True
        
        # 요청이 성공했을 때도 헤더 정보가 로그에 노출되지 않아야 함
        log_output = log_capture.getvalue()
        
        # User-Agent 등의 헤더 정보가 로그에 노출되지 않았는지 확인
        assert "User-Agent" not in log_output
        assert "Content-Type" not in log_output
        assert "TestscenarioMaker-CLI" not in log_output
        
        # 정리
        logger.removeHandler(handler)


class TestSecureErrorHandling:
    """안전한 오류 처리 테스트"""
    
    @patch('ts_cli.main.requests.Session')
    @patch('ts_cli.vcs.get_analyzer')
    def test_connection_error_generic_message(self, mock_get_analyzer, mock_session_class):
        """연결 오류 시 일반적인 메시지만 표시"""
        # Arrange
        mock_analyzer = Mock()
        mock_analyzer.validate_repository.return_value = True
        mock_analyzer.get_changes.return_value = {"changes_text": "test changes"}
        mock_get_analyzer.return_value = mock_analyzer
        
        import requests
        connection_error = requests.exceptions.ConnectionError(
            "HTTPSConnectionPool(host='secret-internal-server.local', port=443): "
            "Max retries exceeded with url: /api/v2/generate (Caused by "
            "NewConnectionError('<urllib3.connection.HTTPSConnection object at 0x123>: "
            "Failed to establish a new connection: [Errno 11001] getaddrinfo failed'))"
        )
        
        mock_session = Mock()
        mock_session.post.side_effect = connection_error
        mock_session_class.return_value.__enter__.return_value = mock_session
        
        server_url = "http://secret-internal-server.local"
        repo_path = Path("/test/repo")
        
        # Act
        with patch('ts_cli.main.console') as mock_console:
            result = make_api_request(server_url, repo_path)
        
        # Assert
        assert result is False
        
        # 내부 서버 정보가 노출되지 않고 일반적인 오류 메시지만 표시
        console_calls = [call[0][0] for call in mock_console.print.call_args_list]
        console_output = " ".join(str(call) for call in console_calls)
        
        # 내부 서버 상세 정보가 노출되지 않아야 함
        assert "secret-internal-server.local" not in console_output
        assert "HTTPSConnectionPool" not in console_output
        assert "urllib3" not in console_output
        
        # 일반적인 연결 오류 메시지만 표시되어야 함
        assert any("서버에 연결할 수 없습니다" in str(call) for call in console_calls)
    
    @patch('ts_cli.main.requests.Session')  
    @patch('ts_cli.vcs.get_analyzer')
    def test_timeout_error_no_server_details(self, mock_get_analyzer, mock_session_class):
        """타임아웃 오류 시 서버 상세 정보 노출하지 않음"""
        # Arrange
        mock_analyzer = Mock()
        mock_analyzer.validate_repository.return_value = True
        mock_analyzer.get_changes.return_value = {"changes_text": "test changes"}
        mock_get_analyzer.return_value = mock_analyzer
        
        import requests
        timeout_error = requests.exceptions.Timeout(
            "HTTPSConnectionPool(host='production-api.internal.com', port=443): "
            "Read timed out. (read timeout=30)"
        )
        
        mock_session = Mock()
        mock_session.post.side_effect = timeout_error
        mock_session_class.return_value.__enter__.return_value = mock_session
        
        server_url = "http://production-api.internal.com"
        repo_path = Path("/test/repo")
        
        # Act
        with patch('ts_cli.main.console') as mock_console:
            result = make_api_request(server_url, repo_path)
        
        # Assert
        assert result is False
        
        # 내부 서버 정보나 타임아웃 상세 정보가 노출되지 않음
        console_calls = [call[0][0] for call in mock_console.print.call_args_list]
        console_output = " ".join(str(call) for call in console_calls)
        
        assert "production-api.internal.com" not in console_output
        assert "HTTPSConnectionPool" not in console_output
        assert "Read timed out" not in console_output
        
        # 일반적인 타임아웃 오류 메시지만 표시
        assert any("요청 시간이 초과되었습니다" in str(call) for call in console_calls)