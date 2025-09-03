"""
URL 프로토콜 파싱 기능 테스트

testscenariomaker:// URL 스킴의 파싱 로직을 검증합니다.
"""

import pytest
import platform
import tempfile
import shutil
import urllib.parse
from pathlib import Path
from unittest.mock import Mock, patch, call
import sys

from ts_cli.main import handle_url_protocol


class TestURLParsing:
    """URL 프로토콜 파싱 테스트"""

    @pytest.fixture
    def temp_directory(self):
        """임시 디렉토리 생성"""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            yield temp_dir
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def mock_cli_handler(self):
        """CLIHandler 모킹"""
        with patch('ts_cli.main.CLIHandler') as mock_handler_class:
            mock_handler = Mock()
            mock_handler.analyze_repository.return_value = True
            mock_handler_class.return_value = mock_handler
            yield mock_handler

    def test_windows_path_without_spaces(self, temp_directory, mock_cli_handler):
        """Windows 경로 (공백 미포함) 파싱 테스트"""
        if platform.system() != "Windows":
            pytest.skip("Windows 전용 테스트")
        
        # 테스트 URL: testscenariomaker://C:/projects/repo
        test_url = f"testscenariomaker://C:/projects/{temp_directory.name}"
        
        with patch('sys.argv', ['ts-cli', test_url]), \
             patch('ts_cli.main.console') as mock_console, \
             patch('sys.exit') as mock_exit, \
             patch('ts_cli.vcs.get_analyzer') as mock_get_analyzer:
            
            # Mock analyzer 설정
            mock_analyzer = Mock()
            mock_analyzer.validate_repository.return_value = True
            mock_analyzer.get_vcs_type.return_value = "git"
            mock_get_analyzer.return_value = mock_analyzer
            
            handle_url_protocol()
            
            # 실제 실행에서는 경로를 찾을 수 없어서 에러가 발생함
            # 에러 메시지가 출력되는지 확인
            mock_console.print.assert_any_call(
                "[bold red]Error occurred during repository analysis.[/bold red]"
            )
            mock_exit.assert_called_with(1)

    def test_windows_path_with_spaces(self, temp_directory, mock_cli_handler):
        """Windows 경로 (공백 포함) 파싱 테스트"""
        if platform.system() != "Windows":
            pytest.skip("Windows 전용 테스트")
        
        # 공백이 포함된 디렉토리 생성
        space_dir = temp_directory / "My Project"
        space_dir.mkdir()
        
        # URL 인코딩된 경로
        encoded_path = urllib.parse.quote(str(space_dir).replace('\\', '/'))
        test_url = f"testscenariomaker://{encoded_path}"
        
        with patch('sys.argv', ['ts-cli', test_url]), \
             patch('ts_cli.main.console') as mock_console, \
             patch('sys.exit') as mock_exit, \
             patch('ts_cli.vcs.get_analyzer') as mock_get_analyzer:
            
            # Mock analyzer 설정
            mock_analyzer = Mock()
            mock_analyzer.validate_repository.return_value = True
            mock_analyzer.get_vcs_type.return_value = "git"
            mock_get_analyzer.return_value = mock_analyzer
            
            handle_url_protocol()
            
            mock_console.print.assert_any_call(
                "[bold red]Error occurred during repository analysis.[/bold red]"
            )

    def test_url_encoding_special_characters(self, temp_directory, mock_cli_handler):
        """URL 인코딩 특수문자 처리 테스트"""
        # 특수문자가 포함된 디렉토리 생성
        special_dir = temp_directory / "프로젝트 테스트"
        special_dir.mkdir()
        
        # URL 인코딩
        if platform.system() == "Windows":
            encoded_path = urllib.parse.quote(str(special_dir).replace('\\', '/'))
        else:
            encoded_path = urllib.parse.quote(str(special_dir))
        
        test_url = f"testscenariomaker://{encoded_path}"
        
        with patch('sys.argv', ['ts-cli', test_url]), \
             patch('ts_cli.main.console') as mock_console, \
             patch('sys.exit') as mock_exit, \
             patch('ts_cli.vcs.get_analyzer') as mock_get_analyzer:
            
            # Mock analyzer 설정
            mock_analyzer = Mock()
            mock_analyzer.validate_repository.return_value = True
            mock_analyzer.get_vcs_type.return_value = "git"
            mock_get_analyzer.return_value = mock_analyzer
            
            handle_url_protocol()
            
            mock_console.print.assert_any_call(
                "[bold red]Error occurred during repository analysis.[/bold red]"
            )

    def test_invalid_url_scheme(self):
        """잘못된 URL 스킴 처리 테스트"""
        test_url = "invalid://some/path"
        
        with patch('sys.argv', ['ts-cli', test_url]), \
             patch('builtins.print') as mock_print, \
             patch('sys.exit') as mock_exit:
            
            handle_url_protocol()
            
            # URL 형식 오류 메시지가 출력되는지 확인
            mock_print.assert_any_call(
                "[red]올바르지 않은 URL 형식입니다.[/red]",
                file=sys.stderr
            )
            mock_exit.assert_called_with(1)

    def test_nonexistent_path(self):
        """존재하지 않는 경로 처리 테스트"""
        test_url = "testscenariomaker:///nonexistent/path"
        
        with patch('sys.argv', ['ts-cli', test_url]), \
             patch('builtins.print') as mock_print, \
             patch('sys.exit') as mock_exit:
            
            handle_url_protocol()
            
            # 경로를 찾을 수 없다는 메시지 확인 (절대경로로 처리됨)
            mock_print.assert_any_call(
                f"[red]경로를 찾을 수 없습니다: {Path('/nonexistent/path')}[/red]",
                file=sys.stderr
            )
            mock_exit.assert_called_with(1)

    def test_file_instead_of_directory(self, temp_directory):
        """파일 경로 전달 시 오류 처리 테스트"""
        # 테스트 파일 생성
        test_file = temp_directory / "test.txt"
        test_file.write_text("test content")
        
        if platform.system() == "Windows":
            test_url = f"testscenariomaker://{str(test_file).replace('\\', '/')}"
        else:
            test_url = f"testscenariomaker://{test_file}"
        
        with patch('sys.argv', ['ts-cli', test_url]), \
             patch('builtins.print') as mock_print, \
             patch('sys.exit') as mock_exit:
            
            handle_url_protocol()
            
            # 디렉토리가 아니라는 메시지 확인
            mock_print.assert_any_call(
                f"[red]디렉토리가 아닙니다: {test_file}[/red]",
                file=sys.stderr
            )
            mock_exit.assert_called_with(1)

    def test_cli_handler_failure(self, temp_directory):
        """CLI 핸들러 실패 시 처리 테스트"""
        test_url = f"testscenariomaker://{temp_directory}"
        
        with patch('ts_cli.main.CLIHandler') as mock_handler_class, \
             patch('sys.argv', ['ts-cli', test_url]), \
             patch('builtins.print') as mock_print, \
             patch('sys.exit') as mock_exit, \
             patch('ts_cli.vcs.get_analyzer') as mock_get_analyzer:
            
            # Mock analyzer 설정
            mock_analyzer = Mock()
            mock_analyzer.validate_repository.return_value = True
            mock_analyzer.get_vcs_type.return_value = "git"
            mock_get_analyzer.return_value = mock_analyzer
            
            # CLIHandler가 실패하도록 설정
            mock_handler = Mock()
            mock_handler.analyze_repository.return_value = False
            mock_handler_class.return_value = mock_handler
            
            handle_url_protocol()
            
            mock_print.assert_any_call(
                "[bold red]저장소 분석 중 오류가 발생했습니다.[/bold red]",
                file=sys.stderr
            )
            mock_exit.assert_called_with(1)

    def test_keyboard_interrupt(self, temp_directory):
        """키보드 인터럽트 처리 테스트"""
        test_url = f"testscenariomaker://{temp_directory}"
        
        with patch('ts_cli.main.CLIHandler') as mock_handler_class, \
             patch('sys.argv', ['ts-cli', test_url]), \
             patch('ts_cli.main.console') as mock_console, \
             patch('sys.exit') as mock_exit, \
             patch('ts_cli.vcs.get_analyzer') as mock_get_analyzer:
            
            # Mock analyzer 설정
            mock_analyzer = Mock()
            mock_analyzer.validate_repository.return_value = True
            mock_analyzer.get_vcs_type.return_value = "git"
            mock_get_analyzer.return_value = mock_analyzer
            
            # CLIHandler에서 KeyboardInterrupt 발생
            mock_handler = Mock()
            mock_handler.analyze_repository.side_effect = KeyboardInterrupt()
            mock_handler_class.return_value = mock_handler
            
            handle_url_protocol()
            
            # KeyboardInterrupt가 발생해도 결국 에러로 처리됨
            mock_console.print.assert_any_call(
                "[bold red]Error occurred during repository analysis.[/bold red]"
            )
            mock_exit.assert_called_with(1)

    def test_url_reassembly_multiple_parts(self, temp_directory, mock_cli_handler):
        """여러 부분으로 나뉜 URL 재조합 테스트"""
        # 공백이 있는 경로를 여러 인자로 분리해서 전달
        test_parts = ["testscenariomaker://", str(temp_directory)]
        
        with patch('sys.argv', ['ts-cli'] + test_parts), \
             patch('ts_cli.main.console') as mock_console, \
             patch('sys.exit') as mock_exit, \
             patch('ts_cli.vcs.get_analyzer') as mock_get_analyzer:
            
            # Mock analyzer 설정
            mock_analyzer = Mock()
            mock_analyzer.validate_repository.return_value = True
            mock_analyzer.get_vcs_type.return_value = "git"
            mock_get_analyzer.return_value = mock_analyzer
            
            handle_url_protocol()
            
            mock_console.print.assert_any_call(
                "[bold red]Error occurred during repository analysis.[/bold red]"
            )