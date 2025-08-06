"""
main.py의 동기 방식 기능들에 대한 단위 테스트

URL 파싱, 플랫폼별 경로 변환, 설정 fallback 로직을 테스트합니다.
"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

# 테스트 대상 모듈 import
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from ts_cli.main import (
    load_server_config,
    parse_url_parameters,
    validate_repository_path,
    make_api_request
)


class TestLoadServerConfig:
    """서버 설정 로딩 로직 테스트"""
    
    @patch('ts_cli.utils.config_loader.load_config')
    @patch.dict(os.environ, {}, clear=True)
    def test_load_from_config_file_success(self, mock_load_config):
        """config.ini 파일에서 서버 URL 로드 성공"""
        # Arrange
        mock_config_loader = Mock()
        mock_config_loader.get.return_value = "http://config-server.com"
        mock_load_config.return_value = mock_config_loader
        
        # Act
        result = load_server_config()
        
        # Assert
        assert result == "http://config-server.com"
        mock_config_loader.get.assert_called_once_with("api", "base_url")
    
    @patch('ts_cli.utils.config_loader.load_config')
    @patch.dict(os.environ, {'TSM_SERVER_URL': 'http://env-server.com'})
    def test_load_from_env_when_config_fails(self, mock_load_config):
        """설정 파일 로드 실패 시 환경 변수에서 로드"""
        # Arrange
        mock_config_loader = Mock()
        mock_config_loader.get.return_value = None  # 설정 파일에 없음
        mock_load_config.return_value = mock_config_loader
        
        # Act
        result = load_server_config()
        
        # Assert
        assert result == "http://env-server.com"
    
    @patch('ts_cli.utils.config_loader.load_config')
    @patch.dict(os.environ, {'TSM_SERVER_URL': 'http://env-server.com'})
    def test_load_from_env_when_config_exception(self, mock_load_config):
        """설정 파일 로드 예외 발생 시 환경 변수에서 로드"""
        # Arrange
        mock_load_config.side_effect = Exception("Config file error")
        
        # Act
        result = load_server_config()
        
        # Assert
        assert result == "http://env-server.com"
    
    @patch('ts_cli.utils.config_loader.load_config')
    @patch.dict(os.environ, {}, clear=True)  # 모든 환경 변수 제거
    def test_load_failure_exits_with_code_1(self, mock_load_config):
        """설정 로드 실패 시 종료 코드 1로 종료"""
        # Arrange
        mock_config_loader = Mock()
        mock_config_loader.get.return_value = None
        mock_load_config.return_value = mock_config_loader
        
        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            load_server_config()
        assert exc_info.value.code == 1


class TestParseUrlParameters:
    """URL 파라미터 파싱 로직 테스트"""
    
    @patch('ts_cli.main.platform.system', return_value='Windows')
    def test_parse_windows_path(self, mock_platform):
        """Windows 경로 파싱 테스트"""
        # Arrange
        url = "testscenariomaker://C:/Users/test/repo?clientId=123"
        
        # Act
        repo_path, client_id = parse_url_parameters(url)
        
        # Assert
        assert str(repo_path) == r"C:\Users\test\repo"
        assert client_id == "123"
    
    @patch('ts_cli.main.platform.system', return_value='Darwin')
    def test_parse_macos_path(self, mock_platform):
        """macOS 경로 파싱 테스트"""
        # Arrange
        url = "testscenariomaker:///Users/test/repo?clientId=456"
        
        # Act
        repo_path, client_id = parse_url_parameters(url)
        
        # Assert
        assert str(repo_path) == "/Users/test/repo"
        assert client_id == "456"
    
    @patch('ts_cli.main.platform.system', return_value='Linux')
    def test_parse_linux_path(self, mock_platform):
        """Linux 경로 파싱 테스트"""
        # Arrange
        url = "testscenariomaker:///home/test/repo"
        
        # Act
        repo_path, client_id = parse_url_parameters(url)
        
        # Assert
        assert str(repo_path) == "/home/test/repo"
        assert client_id is None
    
    def test_parse_url_encoded_path(self):
        """URL 인코딩된 경로 파싱 테스트"""
        # Arrange
        url = "testscenariomaker:///Users/test/repo%20with%20spaces"
        
        # Act
        repo_path, client_id = parse_url_parameters(url)
        
        # Assert
        assert "repo with spaces" in str(repo_path)
    
    def test_parse_invalid_url_raises_error(self):
        """잘못된 URL 파싱 시 오류 발생"""
        # Arrange
        url = "invalid://url"
        
        # Act & Assert
        with pytest.raises(ValueError, match="URL 파싱 실패"):
            parse_url_parameters(url)


class TestValidateRepositoryPath:
    """저장소 경로 검증 로직 테스트"""
    
    def test_validate_existing_git_repo_success(self, tmp_path):
        """유효한 Git 저장소 검증 성공"""
        # Arrange
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        (repo_path / ".git").mkdir()
        
        # Act & Assert (예외가 발생하지 않으면 성공)
        validate_repository_path(repo_path)
    
    def test_validate_nonexistent_path_exits(self):
        """존재하지 않는 경로 검증 시 종료"""
        # Arrange
        repo_path = Path("/nonexistent/path")
        
        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            validate_repository_path(repo_path)
        assert exc_info.value.code == 1
    
    def test_validate_file_path_exits(self, tmp_path):
        """파일 경로 검증 시 종료"""
        # Arrange
        file_path = tmp_path / "test_file.txt"
        file_path.write_text("test")
        
        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            validate_repository_path(file_path)
        assert exc_info.value.code == 1
    
    def test_validate_non_git_directory_exits(self, tmp_path):
        """Git 저장소가 아닌 디렉토리 검증 시 종료"""
        # Arrange
        repo_path = tmp_path / "not_git_repo"
        repo_path.mkdir()
        
        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            validate_repository_path(repo_path)
        assert exc_info.value.code == 1


class TestMakeApiRequest:
    """API 요청 로직 테스트"""
    
    @patch('ts_cli.main.requests.Session')
    @patch('ts_cli.vcs.get_analyzer')
    def test_api_request_success(self, mock_get_analyzer, mock_session_class):
        """API 요청 성공 테스트"""
        # Arrange
        mock_analyzer = Mock()
        mock_analyzer.validate_repository.return_value = True
        mock_analyzer.get_changes.return_value = {"changes_text": "test changes"}
        mock_get_analyzer.return_value = mock_analyzer
        
        mock_session = Mock()
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"download_url": "http://example.com/result"}
        mock_session.post.return_value = mock_response
        mock_session_class.return_value.__enter__.return_value = mock_session
        
        server_url = "http://test-server.com"
        repo_path = Path("/test/repo")
        
        # Act
        result = make_api_request(server_url, repo_path)
        
        # Assert
        assert result is True
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert call_args[0][0] == "http://test-server.com/api/v2/generate"
        assert "analysis_text" in call_args[1]["json"]
    
    @patch('ts_cli.main.requests.Session')
    @patch('ts_cli.vcs.get_analyzer')
    def test_api_request_invalid_repo(self, mock_get_analyzer, mock_session_class):
        """유효하지 않은 저장소로 API 요청 시 실패"""
        # Arrange
        mock_analyzer = Mock()
        mock_analyzer.validate_repository.return_value = False
        mock_get_analyzer.return_value = mock_analyzer
        
        server_url = "http://test-server.com"
        repo_path = Path("/invalid/repo")
        
        # Act
        result = make_api_request(server_url, repo_path)
        
        # Assert
        assert result is False
    
    @patch('ts_cli.main.requests.Session')
    @patch('ts_cli.vcs.get_analyzer')
    def test_api_request_connection_error(self, mock_get_analyzer, mock_session_class):
        """연결 오류 시 API 요청 실패"""
        # Arrange
        mock_analyzer = Mock()
        mock_analyzer.validate_repository.return_value = True
        mock_analyzer.get_changes.return_value = {"changes_text": "test changes"}
        mock_get_analyzer.return_value = mock_analyzer
        
        mock_session = Mock()
        mock_session.post.side_effect = Exception("Connection error")
        mock_session_class.return_value.__enter__.return_value = mock_session
        
        server_url = "http://test-server.com"
        repo_path = Path("/test/repo")
        
        # Act
        result = make_api_request(server_url, repo_path)
        
        # Assert
        assert result is False


@pytest.mark.parametrize("platform_name,expected_path", [
    ("Windows", r"C:\Users\test\repo"),
    ("Darwin", "/Users/test/repo"),
    ("Linux", "/home/test/repo"),
])
@patch('ts_cli.main.platform.system')
def test_platform_specific_path_parsing(mock_platform, platform_name, expected_path):
    """플랫폼별 경로 파싱 파라미터화 테스트"""
    # Arrange
    mock_platform.return_value = platform_name
    if platform_name == "Windows":
        url = "testscenariomaker://C:/Users/test/repo"
    else:
        if platform_name == "Darwin":
            url = "testscenariomaker:///Users/test/repo"
        else:  # Linux
            url = "testscenariomaker:///home/test/repo"
    
    # Act
    repo_path, client_id = parse_url_parameters(url)
    
    # Assert
    assert str(repo_path) == expected_path


class TestSettingsFallbackPriority:
    """설정 fallback 우선순위 테스트"""
    
    @patch.dict(os.environ, {'TSM_SERVER_URL': 'http://env-server.com'})
    @patch('ts_cli.utils.config_loader.load_config')
    def test_config_file_takes_priority_over_env(self, mock_load_config):
        """설정 파일이 환경 변수보다 우선순위가 높음"""
        # Arrange
        mock_config_loader = Mock()
        mock_config_loader.get.return_value = "http://config-server.com"
        mock_load_config.return_value = mock_config_loader
        
        # Act
        result = load_server_config()
        
        # Assert
        assert result == "http://config-server.com"  # 환경 변수가 아닌 설정 파일 값
    
    @patch.dict(os.environ, {}, clear=True)
    @patch('ts_cli.utils.config_loader.load_config')
    def test_only_env_var_used_when_config_empty(self, mock_load_config):
        """설정 파일이 비어있을 때만 환경 변수 사용"""
        # Arrange
        os.environ['TSM_SERVER_URL'] = 'http://env-only.com'
        mock_config_loader = Mock()
        mock_config_loader.get.return_value = ""  # 빈 값
        mock_load_config.return_value = mock_config_loader
        
        # Act
        result = load_server_config()
        
        # Assert
        assert result == "http://env-only.com"