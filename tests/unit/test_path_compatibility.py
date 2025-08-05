"""
크로스플랫폼 경로 호환성 테스트

pathlib.Path 사용과 subprocess 상호작용 테스트입니다.
"""

import pytest
import subprocess
import platform
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from ts_cli.utils.config_loader import ConfigLoader
from ts_cli.vcs.git_analyzer import GitAnalyzer


class TestPathCompatibility:
    """크로스플랫폼 경로 호환성 테스트"""

    @pytest.fixture
    def temp_directory(self):
        """임시 디렉토리 생성"""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            yield temp_dir
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_pathlib_path_creation(self, temp_directory):
        """pathlib.Path 생성 테스트"""
        # 절대 경로
        abs_path = temp_directory / "test_file.txt"
        assert isinstance(abs_path, Path)
        assert abs_path.parent == temp_directory

        # 중첩 경로
        nested_path = temp_directory / "subdir" / "nested_file.txt"
        assert isinstance(nested_path, Path)
        assert nested_path.name == "nested_file.txt"

    def test_pathlib_path_string_conversion(self, temp_directory):
        """Path 객체의 문자열 변환 테스트"""
        test_path = temp_directory / "test.txt"

        # str() 변환
        path_str = str(test_path)
        assert isinstance(path_str, str)
        assert len(path_str) > 0

        # 플랫폼별 구분자 확인
        if platform.system() == "Windows":
            # Windows는 백슬래시 또는 포워드슬래시 모두 허용
            assert "\\" in path_str or "/" in path_str
        else:
            # Unix 계열은 포워드슬래시
            assert "/" in path_str

    def test_pathlib_file_operations(self, temp_directory):
        """pathlib를 사용한 파일 연산 테스트"""
        test_file = temp_directory / "test.txt"
        test_content = "Hello, Cross-Platform World!"

        # 파일 생성
        test_file.write_text(test_content, encoding="utf-8")
        assert test_file.exists()
        assert test_file.is_file()

        # 파일 읽기
        content = test_file.read_text(encoding="utf-8")
        assert content == test_content

        # 디렉토리 생성
        sub_dir = temp_directory / "subdir"
        sub_dir.mkdir(exist_ok=True)
        assert sub_dir.exists()
        assert sub_dir.is_dir()

    def test_subprocess_with_pathlib_cwd(self, temp_directory):
        """subprocess에서 pathlib Path를 cwd로 사용하는 테스트"""
        # 테스트 파일 생성
        test_file = temp_directory / "test.txt"
        test_file.write_text("test content")

        # subprocess.run에서 Path 객체를 str()로 변환하여 사용
        result = subprocess.run(
            ["python", "-c", "import os; print(os.getcwd())"],
            cwd=str(temp_directory),  # Path 객체를 문자열로 변환
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        output_path = Path(result.stdout.strip())
        assert output_path.resolve() == temp_directory.resolve()

    @pytest.mark.skipif(platform.system() == "Windows", reason="Unix 전용 테스트")
    def test_unix_path_operations(self, temp_directory):
        """Unix 계열 시스템 전용 경로 테스트"""
        # 심볼릭 링크 테스트 (Unix에서만 지원)
        original_file = temp_directory / "original.txt"
        link_file = temp_directory / "link.txt"

        original_file.write_text("original content")

        try:
            link_file.symlink_to(original_file)
            assert link_file.is_symlink()
            assert link_file.resolve() == original_file.resolve()
        except (OSError, NotImplementedError):
            # 심볼릭 링크를 지원하지 않는 파일시스템
            pytest.skip("Symbolic links not supported")

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows 전용 테스트")
    def test_windows_path_operations(self, temp_directory):
        """Windows 전용 경로 테스트"""
        # Windows 드라이브 문자 테스트
        abs_path = temp_directory.resolve()
        path_str = str(abs_path)

        # Windows 경로는 드라이브 문자로 시작
        if ":" in path_str:
            drive, rest = path_str.split(":", 1)
            assert len(drive) == 1  # 단일 문자 드라이브
            assert drive.isalpha()  # 알파벳 문자

    def test_config_loader_path_handling(self, temp_directory):
        """ConfigLoader의 경로 처리 테스트"""
        config_file = temp_directory / "test_config.ini"
        config_content = """
[api]
base_url = https://test.example.com
timeout = 30

[cli]
verbose = false
"""
        config_file.write_text(config_content)

        # ConfigLoader에 Path 객체 전달
        loader = ConfigLoader(config_file)

        assert loader.config_path == config_file
        assert loader.get("api", "base_url") == "https://test.example.com"
        assert loader.get("api", "timeout", value_type=int) == 30

    def test_git_analyzer_path_handling(self, temp_directory):
        """GitAnalyzer의 경로 처리 테스트"""
        # Git 저장소가 아닌 디렉토리로 테스트
        analyzer = GitAnalyzer(temp_directory)

        # repo_path가 Path 객체인지 확인
        assert isinstance(analyzer.repo_path, Path)
        # resolve()를 사용하여 심볼릭 링크 해결 후 비교
        assert analyzer.repo_path.resolve() == temp_directory.resolve()

        # validate_repository는 실패해야 함 (Git 저장소가 아니므로)
        assert not analyzer.validate_repository()

    def test_relative_path_resolution(self, temp_directory):
        """상대 경로 해결 테스트"""
        # 현재 디렉토리에서 상대 경로 생성
        current_dir = Path.cwd()

        # temp_directory로부터 상대 경로 계산
        try:
            relative_path = temp_directory.relative_to(current_dir)

            # 상대 경로를 절대 경로로 해결
            resolved_path = (current_dir / relative_path).resolve()
            assert resolved_path == temp_directory.resolve()

        except ValueError:
            # temp_directory가 current_dir의 하위 디렉토리가 아닌 경우
            # 이는 정상적인 상황임 (임시 디렉토리는 보통 다른 위치에 생성됨)
            pytest.skip("Temporary directory not relative to current directory")

    def test_path_joining_cross_platform(self, temp_directory):
        """크로스플랫폼 경로 결합 테스트"""
        # pathlib를 사용한 경로 결합
        path1 = temp_directory / "dir1"
        path2 = path1 / "dir2"
        path3 = path2 / "file.txt"

        # 모든 경로가 Path 객체인지 확인
        assert isinstance(path1, Path)
        assert isinstance(path2, Path)
        assert isinstance(path3, Path)

        # 경로 구조 확인
        assert path3.parent == path2
        assert path2.parent == path1
        assert path1.parent == temp_directory

        # 문자열 변환 후 구분자 확인
        path_str = str(path3)
        assert "dir1" in path_str
        assert "dir2" in path_str
        assert "file.txt" in path_str

    def test_path_normalization(self, temp_directory):
        """경로 정규화 테스트"""
        # 중복 구분자가 있는 경로
        redundant_path = temp_directory / "dir1" / ".." / "dir2" / "file.txt"
        normalized_path = redundant_path.resolve()

        # 정규화된 경로는 .. 을 포함하지 않아야 함
        path_str = str(normalized_path)
        assert ".." not in path_str

        # 실제 경로 구조 확인
        expected_path = temp_directory / "dir2" / "file.txt"
        assert normalized_path == expected_path.resolve()

    @patch("subprocess.run")
    def test_subprocess_cwd_string_conversion(self, mock_run, temp_directory):
        """subprocess.run에서 cwd 매개변수의 문자열 변환 테스트"""
        # GitAnalyzer의 _run_git_command 메서드 테스트
        analyzer = GitAnalyzer(temp_directory)

        # mock subprocess.run 설정
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "mock output"
        mock_run.return_value = mock_result

        # _run_git_command 호출
        result = analyzer._run_git_command(["git", "status"], check_repo=False)

        # subprocess.run이 호출되었는지 확인
        mock_run.assert_called_once()
        call_args = mock_run.call_args

        # cwd가 문자열로 전달되었는지 확인
        assert "cwd" in call_args.kwargs
        cwd_value = call_args.kwargs["cwd"]
        assert isinstance(cwd_value, str)
        # resolve()된 경로끼리 비교
        assert Path(cwd_value).resolve() == temp_directory.resolve()

    def test_path_existence_checks(self, temp_directory):
        """경로 존재 확인 테스트"""
        # 존재하는 디렉토리
        assert temp_directory.exists()
        assert temp_directory.is_dir()
        assert not temp_directory.is_file()

        # 존재하지 않는 파일
        nonexistent_file = temp_directory / "nonexistent.txt"
        assert not nonexistent_file.exists()
        assert not nonexistent_file.is_file()
        assert not nonexistent_file.is_dir()

        # 파일 생성 후 확인
        test_file = temp_directory / "test.txt"
        test_file.write_text("test")
        assert test_file.exists()
        assert test_file.is_file()
        assert not test_file.is_dir()

    def test_path_permissions(self, temp_directory):
        """경로 권한 테스트"""
        test_file = temp_directory / "perm_test.txt"
        test_file.write_text("permission test")

        # 파일이 읽기 가능한지 확인
        assert test_file.is_file()
        content = test_file.read_text()
        assert content == "permission test"

        # 플랫폼별 권한 테스트
        if platform.system() != "Windows":
            # Unix 계열에서는 실행 권한 테스트 가능
            import stat

            current_mode = test_file.stat().st_mode
            assert stat.S_ISREG(current_mode)  # 일반 파일인지 확인


class TestPathEdgeCases:
    """경로 처리 엣지 케이스 테스트"""

    def test_empty_path_handling(self):
        """빈 경로 처리 테스트"""
        # 빈 문자열로 Path 생성은 현재 디렉토리를 가리키므로 예외가 발생하지 않음
        # 대신 None으로 Path 생성 시도
        with pytest.raises(TypeError):
            Path(None)

    def test_special_characters_in_path(self, tmp_path):
        """경로에 특수 문자가 포함된 경우 테스트"""
        # 공백이 포함된 경로
        space_dir = tmp_path / "dir with spaces"
        space_dir.mkdir()
        assert space_dir.exists()

        # 특수 문자가 포함된 파일명 (플랫폼에 따라 제한이 다름)
        special_chars = ["test_file", "test-file", "test.file"]

        for char_name in special_chars:
            test_file = space_dir / char_name
            test_file.write_text("test content")
            assert test_file.exists()

            # 문자열 변환이 올바르게 작동하는지 확인
            path_str = str(test_file)
            assert isinstance(path_str, str)

    def test_very_long_path_handling(self, tmp_path):
        """매우 긴 경로 처리 테스트"""
        # 플랫폼별 경로 길이 제한 고려
        max_name_length = 50  # 보수적인 길이 사용

        long_name = "a" * max_name_length
        long_path = tmp_path / long_name

        try:
            long_path.mkdir()
            assert long_path.exists()

            # 중첩된 긴 경로
            nested_long_path = long_path / long_name / "file.txt"
            nested_long_path.parent.mkdir(exist_ok=True)
            nested_long_path.write_text("test")
            assert nested_long_path.exists()

        except OSError:
            # 플랫폼에서 지원하지 않는 경로 길이
            pytest.skip("Platform does not support long paths")

    def test_unicode_path_handling(self, tmp_path):
        """유니코드 경로 처리 테스트"""
        # 한글 경로
        korean_dir = tmp_path / "한글디렉토리"
        korean_file = korean_dir / "한글파일.txt"

        try:
            korean_dir.mkdir()
            korean_file.write_text("한글 내용", encoding="utf-8")

            assert korean_dir.exists()
            assert korean_file.exists()

            # 파일 내용 확인
            content = korean_file.read_text(encoding="utf-8")
            assert content == "한글 내용"

            # 문자열 변환 확인
            path_str = str(korean_file)
            assert isinstance(path_str, str)

        except (UnicodeError, OSError):
            # 플랫폼에서 유니코드 경로를 지원하지 않는 경우
            pytest.skip("Platform does not support unicode paths")
