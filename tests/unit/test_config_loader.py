"""
설정 로더 단위 테스트

ConfigParser 기반 설정 관리 시스템의 테스트입니다.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path
import configparser

from ts_cli.utils.config_loader import (
    ConfigLoader,
    load_config,
    get_config,
    get_api_config,
    get_cli_config,
)


class TestConfigLoader:
    """ConfigLoader 클래스 테스트"""

    @pytest.fixture
    def temp_config_content(self):
        """테스트용 설정 파일 내용"""
        return """
[api]
base_url = https://test.example.com
timeout = 60
max_retries = 5

[cli]
verbose = true
output_format = json

[logging]
level = DEBUG
file_enabled = true
"""

    @pytest.fixture
    def temp_config_file(self, tmp_path, temp_config_content):
        """임시 설정 파일 생성"""
        config_file = tmp_path / "test_config.ini"
        config_file.write_text(temp_config_content)
        return config_file

    def test_config_loader_with_existing_file(self, temp_config_file):
        """기존 설정 파일로 ConfigLoader 초기화 테스트"""
        loader = ConfigLoader(temp_config_file)

        assert loader.config_path == temp_config_file
        assert loader.get("api", "base_url") == "https://test.example.com"
        assert loader.get("api", "timeout", value_type=int) == 60
        assert loader.get("cli", "verbose", value_type=bool) is True

    def test_config_loader_with_nonexistent_file(self, tmp_path):
        """존재하지 않는 설정 파일로 초기화 테스트"""
        nonexistent_file = tmp_path / "nonexistent.ini"

        loader = ConfigLoader(nonexistent_file)

        # 기본값이 로드되어야 함
        assert loader.get("api", "base_url") == "http://localhost:8000"
        assert loader.get("api", "timeout", value_type=int) == 30

    def test_config_loader_default_path_resolution(self):
        """기본 경로 해결 테스트"""
        with patch("pathlib.Path.cwd") as mock_cwd, patch(
            "pathlib.Path.exists"
        ) as mock_exists:

            mock_cwd.return_value = Path("/test")
            mock_exists.return_value = False

            loader = ConfigLoader()

            # 경로가 결정되었는지 확인
            assert loader.config_path is not None

    def test_get_with_default_value(self, temp_config_file):
        """기본값과 함께 설정 조회 테스트"""
        loader = ConfigLoader(temp_config_file)

        # 존재하는 키
        result = loader.get("api", "base_url", "default_value")
        assert result == "https://test.example.com"

        # 존재하지 않는 키
        result = loader.get("api", "nonexistent", "default_value")
        assert result == "default_value"

        # 존재하지 않는 섹션
        result = loader.get("nonexistent", "key", "default_value")
        assert result == "default_value"

    def test_get_with_type_conversion(self, temp_config_file):
        """타입 변환과 함께 설정 조회 테스트"""
        loader = ConfigLoader(temp_config_file)

        # 정수 변환
        timeout = loader.get("api", "timeout", value_type=int)
        assert timeout == 60
        assert isinstance(timeout, int)

        # 불린 변환
        verbose = loader.get("cli", "verbose", value_type=bool)
        assert verbose is True
        assert isinstance(verbose, bool)

        # 부동소수점 변환
        loader.set("api", "retry_delay", "1.5")
        delay = loader.get("api", "retry_delay", value_type=float)
        assert delay == 1.5
        assert isinstance(delay, float)

    def test_get_boolean_conversion_cases(self, tmp_path):
        """불린 변환 다양한 케이스 테스트"""
        loader = ConfigLoader()

        # True 케이스들
        true_cases = ["true", "True", "TRUE", "1", "yes", "YES", "on", "ON"]
        for case in true_cases:
            loader.set("test", "bool_value", case)
            result = loader.get("test", "bool_value", value_type=bool)
            assert result is True, f"'{case}' should be True"

        # False 케이스들
        false_cases = ["false", "False", "FALSE", "0", "no", "NO", "off", "OFF"]
        for case in false_cases:
            loader.set("test", "bool_value", case)
            result = loader.get("test", "bool_value", value_type=bool)
            assert result is False, f"'{case}' should be False"

    def test_get_with_invalid_type_conversion(self, temp_config_file):
        """잘못된 타입 변환 테스트"""
        loader = ConfigLoader(temp_config_file)

        # 숫자가 아닌 값을 int로 변환
        loader.set("test", "invalid_int", "not_a_number")
        result = loader.get("test", "invalid_int", default=42, value_type=int)
        assert result == 42  # 기본값 반환

    def test_set_and_get(self, tmp_path):
        """설정 값 설정 및 조회 테스트"""
        loader = ConfigLoader()

        # 새로운 섹션과 키 설정
        loader.set("new_section", "new_key", "new_value")

        result = loader.get("new_section", "new_key")
        assert result == "new_value"

    def test_set_exception_handling(self, tmp_path):
        """설정 값 설정 시 예외 처리 테스트"""
        loader = ConfigLoader()

        # 존재하지 않는 섹션에 대해 ConfigParser 예외 시뮬레이션
        with patch.object(
            loader.config, "add_section", side_effect=Exception("Config error")
        ):
            # 예외가 발생해도 프로그램이 중단되지 않아야 함
            loader.set("nonexistent_section", "key", "value")

            # 값이 설정되지 않았는지 확인
            result = loader.get("nonexistent_section", "key", "default")
            assert result == "default"

    def test_save_success(self, tmp_path):
        """설정 파일 저장 성공 테스트"""
        config_file = tmp_path / "save_test.ini"
        loader = ConfigLoader(config_file)

        loader.set("test", "key", "value")
        result = loader.save()

        assert result is True
        assert config_file.exists()

        # 저장된 내용 확인
        saved_content = config_file.read_text()
        assert "[test]" in saved_content
        assert "key = value" in saved_content

    def test_save_failure(self, tmp_path):
        """설정 파일 저장 실패 테스트"""
        # 읽기 전용 디렉토리에 저장 시도
        readonly_file = tmp_path / "readonly.ini"
        loader = ConfigLoader(readonly_file)

        # 파일 쓰기 실패 시뮬레이션
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            result = loader.save()
            assert result is False

    def test_get_section(self, temp_config_file):
        """섹션 전체 조회 테스트"""
        loader = ConfigLoader(temp_config_file)

        api_section = loader.get_section("api")

        assert isinstance(api_section, dict)
        assert "base_url" in api_section
        assert "timeout" in api_section
        assert api_section["base_url"] == "https://test.example.com"

    def test_get_section_nonexistent(self, temp_config_file):
        """존재하지 않는 섹션 조회 테스트"""
        loader = ConfigLoader(temp_config_file)

        result = loader.get_section("nonexistent")

        assert result == {}

    def test_get_section_exception(self, temp_config_file):
        """섹션 조회 시 예외 처리 테스트"""
        loader = ConfigLoader(temp_config_file)

        with patch.object(
            loader.config, "items", side_effect=Exception("Config error")
        ):
            result = loader.get_section("api")
            assert result == {}

    def test_get_all_sections(self, temp_config_file):
        """모든 섹션 조회 테스트"""
        loader = ConfigLoader(temp_config_file)

        all_sections = loader.get_all_sections()

        assert isinstance(all_sections, dict)
        assert "api" in all_sections
        assert "cli" in all_sections
        assert "logging" in all_sections

        # API 섹션 내용 확인
        api_section = all_sections["api"]
        assert api_section["base_url"] == "https://test.example.com"

    def test_create_default_config(self, tmp_path):
        """기본 설정 파일 생성 테스트"""
        config_file = tmp_path / "new_config.ini"

        loader = ConfigLoader(config_file)

        # 기본 설정이 로드되었는지 확인
        assert loader.get("api", "base_url") == "http://localhost:8000"
        assert loader.get("cli", "verbose", value_type=bool) is False
        assert loader.get("logging", "level") == "INFO"

    def test_load_default_values(self, tmp_path):
        """기본값 로드 테스트"""
        loader = ConfigLoader()
        loader._load_default_values()

        # 기본값들이 올바르게 설정되었는지 확인
        assert loader.config.has_section("api")
        assert loader.config.has_section("cli")
        assert loader.config.has_section("logging")
        assert loader.config.has_section("vcs")

        assert loader.config.get("api", "base_url") == "http://localhost:8000"
        assert loader.config.get("cli", "verbose") == "false"
        assert loader.config.get("logging", "level") == "INFO"

    def test_cross_platform_path_handling(self, tmp_path):
        """크로스플랫폼 경로 처리 테스트"""
        import platform

        # 서브디렉토리가 있는 경로
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "cross_platform.ini"

        config_content = """
[api]
base_url = https://cross-platform.test.com
timeout = 25

[paths]
data_dir = /tmp/data
log_dir = ./logs
"""
        config_file.write_text(config_content)

        # ConfigLoader에 Path 객체 전달
        loader = ConfigLoader(config_file)

        # 경로가 올바르게 처리되는지 확인
        assert loader.config_path == config_file
        assert loader.config_path.exists()

        # 설정값 확인
        assert loader.get("api", "base_url") == "https://cross-platform.test.com"
        assert loader.get("api", "timeout", value_type=int) == 25

        # 경로 문자열 변환 확인
        config_path_str = str(loader.config_path)
        assert isinstance(config_path_str, str)

        # 플랫폼별 구분자 확인
        if platform.system() == "Windows":
            # Windows는 백슬래시 또는 포워드슬래시
            assert "\\" in config_path_str or "/" in config_path_str
        else:
            # Unix 계열은 포워드슬래시
            assert "/" in config_path_str

    def test_path_resolution_hierarchy(self, tmp_path):
        """경로 해결 계층 구조 테스트"""
        # 여러 위치에 config 파일 생성
        cwd_config = tmp_path / "config.ini"
        package_config = tmp_path / "config" / "config.ini"

        # config 디렉토리 생성
        (tmp_path / "config").mkdir()

        # 서로 다른 내용의 config 파일들
        cwd_config.write_text(
            """
[api]
base_url = https://cwd.test.com
"""
        )

        package_config.write_text(
            """
[api]  
base_url = https://package.test.com
"""
        )

        # Mock을 사용하여 Path.cwd() 오버라이드
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            loader = ConfigLoader()

            # 현재 디렉토리의 config.ini가 우선되어야 함
            assert loader.get("api", "base_url") == "https://cwd.test.com"

    def test_unicode_config_path(self, tmp_path):
        """유니코드 경로 처리 테스트"""
        # 한글 디렉토리 및 파일명
        unicode_dir = tmp_path / "한글설정"
        unicode_file = unicode_dir / "설정.ini"

        try:
            unicode_dir.mkdir()

            config_content = """
[api]
base_url = https://unicode.test.com
timeout = 60

[한글섹션]
한글키 = 한글값
"""
            unicode_file.write_text(config_content, encoding="utf-8")

            # 유니코드 경로로 ConfigLoader 생성
            loader = ConfigLoader(unicode_file)

            assert loader.config_path == unicode_file
            assert loader.get("api", "base_url") == "https://unicode.test.com"
            assert loader.get("한글섹션", "한글키") == "한글값"

        except (UnicodeError, OSError):
            # 플랫폼에서 유니코드 경로를 지원하지 않는 경우
            pytest.skip("Platform does not support unicode paths")


class TestModuleFunctions:
    """모듈 수준 함수 테스트"""

    def test_load_config_global_instance(self, tmp_path):
        """전역 설정 로더 인스턴스 테스트"""
        config_file = tmp_path / "global_test.ini"
        config_file.write_text("[api]\nbase_url = https://global.test.com")

        # 첫 번째 호출로 인스턴스 생성
        loader1 = load_config(config_file)
        assert loader1.get("api", "base_url") == "https://global.test.com"

        # 두 번째 호출로 같은 인스턴스 반환
        loader2 = load_config()
        assert loader2 is loader1

        # 새로운 경로로 호출하면 새 인스턴스 생성
        new_config_file = tmp_path / "new_global_test.ini"
        loader3 = load_config(new_config_file)
        assert loader3 is not loader1

    def test_get_config_without_initialization(self):
        """초기화 없이 get_config 호출 테스트"""
        # 전역 인스턴스 초기화
        with patch("ts_cli.utils.config_loader._config_loader", None):
            loader = get_config()
            assert loader is not None

    @patch("ts_cli.utils.config_loader.get_config")
    def test_get_api_config(self, mock_get_config):
        """API 설정 조회 테스트"""
        mock_loader = Mock()
        mock_loader.get.side_effect = lambda section, key, default=None, value_type=str: {
            ("api", "base_url"): "https://api.test.com",
            ("api", "timeout"): 45 if value_type == int else "45",
            ("api", "max_retries"): 5 if value_type == int else "5",
            ("api", "retry_delay"): 2.0 if value_type == float else "2.0",
        }.get(
            (section, key), default
        )

        mock_get_config.return_value = mock_loader

        config = get_api_config()

        assert config["base_url"] == "https://api.test.com"
        assert config["timeout"] == 45
        assert config["max_retries"] == 5
        assert config["retry_delay"] == 2.0

    @patch("ts_cli.utils.config_loader.get_config")
    def test_get_cli_config(self, mock_get_config):
        """CLI 설정 조회 테스트"""
        mock_loader = Mock()
        mock_loader.get.side_effect = lambda section, key, default=None, value_type=str: {
            ("cli", "default_output_format"): "json",
            ("cli", "verbose"): True if value_type == bool else "true",
            ("cli", "show_progress"): False if value_type == bool else "false",
        }.get(
            (section, key), default
        )

        mock_get_config.return_value = mock_loader

        config = get_cli_config()

        assert config["default_output_format"] == "json"
        assert config["verbose"] is True
        assert config["show_progress"] is False
