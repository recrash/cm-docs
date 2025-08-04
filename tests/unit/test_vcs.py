"""
VCS 모듈 단위 테스트

전략 패턴으로 구현된 VCS 분석기들의 테스트입니다.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import subprocess

from ts_cli.vcs import get_analyzer, get_supported_vcs_types
from ts_cli.vcs.base_analyzer import RepositoryAnalyzer, RepositoryError, InvalidRepositoryError
from ts_cli.vcs.git_analyzer import GitAnalyzer


class TestVCSFactory:
    """VCS 팩토리 함수 테스트"""
    
    def test_get_analyzer_with_git_repository(self, tmp_path):
        """Git 저장소에 대한 분석기 반환 테스트"""
        # Git 저장소 시뮬레이션
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        
        analyzer = get_analyzer(tmp_path)
        
        assert analyzer is not None
        assert isinstance(analyzer, GitAnalyzer)
        assert analyzer.repo_path == tmp_path.resolve()
    
    def test_get_analyzer_with_non_git_repository(self, tmp_path):
        """Git이 아닌 디렉토리에 대한 테스트"""
        # 일반 디렉토리 (VCS 없음)
        analyzer = get_analyzer(tmp_path)
        
        assert analyzer is None
    
    def test_get_analyzer_with_nonexistent_path(self):
        """존재하지 않는 경로에 대한 테스트"""
        nonexistent_path = Path("/nonexistent/path")
        analyzer = get_analyzer(nonexistent_path)
        
        assert analyzer is None
    
    def test_get_analyzer_with_file_path(self, tmp_path):
        """파일 경로에 대한 테스트"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        analyzer = get_analyzer(test_file)
        
        assert analyzer is None
    
    def test_get_supported_vcs_types(self):
        """지원되는 VCS 타입 목록 테스트"""
        supported_types = get_supported_vcs_types()
        
        assert isinstance(supported_types, list)
        assert "git" in supported_types
        assert len(supported_types) >= 1


class TestGitAnalyzer:
    """Git 분석기 테스트"""
    
    @pytest.fixture
    def mock_git_repo(self, tmp_path):
        """Mock Git 저장소 생성"""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        return tmp_path
    
    @pytest.fixture
    def git_analyzer(self, mock_git_repo):
        """GitAnalyzer 인스턴스 생성"""
        return GitAnalyzer(mock_git_repo)
    
    def test_git_analyzer_initialization(self, mock_git_repo):
        """GitAnalyzer 초기화 테스트"""
        analyzer = GitAnalyzer(mock_git_repo)
        
        assert analyzer.path == mock_git_repo
        assert analyzer.repo_path == mock_git_repo.resolve()
        assert analyzer.get_vcs_type() == "git"
    
    @patch('ts_cli.vcs.git_analyzer.subprocess.run')
    def test_validate_repository_success(self, mock_run, git_analyzer):
        """저장소 유효성 검사 성공 케이스"""
        # subprocess.run 모킹 (git status 성공)
        mock_run.return_value = Mock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        result = git_analyzer.validate_repository()
        
        assert result is True
        mock_run.assert_called_once()
        
        # git status 명령어 호출 확인
        call_args = mock_run.call_args[0][0]
        assert "git" in call_args
        assert "status" in call_args
    
    @patch('ts_cli.vcs.git_analyzer.subprocess.run')
    def test_validate_repository_failure(self, mock_run, git_analyzer):
        """저장소 유효성 검사 실패 케이스"""
        # subprocess.run 모킹 (git status 실패)
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="fatal: not a git repository"
        )
        
        result = git_analyzer.validate_repository()
        
        assert result is False
    
    def test_validate_repository_without_git_dir(self, tmp_path):
        """`.git` 디렉토리가 없는 경우 테스트"""
        analyzer = GitAnalyzer(tmp_path)
        
        result = analyzer.validate_repository()
        
        assert result is False
    
    @patch('ts_cli.vcs.git_analyzer.GitAnalyzer.validate_repository')
    @patch('ts_cli.vcs.git_analyzer.GitAnalyzer._get_latest_commit_info')
    @patch('ts_cli.vcs.git_analyzer.GitAnalyzer._get_working_directory_changes')
    @patch('ts_cli.vcs.git_analyzer.GitAnalyzer._get_diff_from_head')
    def test_get_changes_success(
        self, 
        mock_diff, 
        mock_working, 
        mock_commit, 
        mock_validate, 
        git_analyzer
    ):
        """변경사항 분석 성공 케이스"""
        # Mock 설정
        mock_validate.return_value = True
        mock_commit.return_value = "커밋: abc123\n작성자: Test User\n메시지: Test commit"
        mock_working.return_value = "M  test.py\nA  new_file.py"
        mock_diff.return_value = "diff --git a/test.py b/test.py\n+new line"
        
        result = git_analyzer.get_changes()
        
        assert "최근 커밋 정보" in result
        assert "작업 디렉토리 변경사항" in result
        assert "HEAD와의 차이점" in result
        assert "Test commit" in result
        assert "new line" in result
    
    @patch('ts_cli.vcs.git_analyzer.GitAnalyzer.validate_repository')
    def test_get_changes_invalid_repository(self, mock_validate, git_analyzer):
        """유효하지 않은 저장소에 대한 변경사항 분석 테스트"""
        mock_validate.return_value = False
        
        with pytest.raises(InvalidRepositoryError):
            git_analyzer.get_changes()
    
    @patch('ts_cli.vcs.git_analyzer.GitAnalyzer.validate_repository')
    @patch('ts_cli.vcs.git_analyzer.GitAnalyzer._get_latest_commit_info')
    @patch('ts_cli.vcs.git_analyzer.GitAnalyzer._get_working_directory_changes')
    @patch('ts_cli.vcs.git_analyzer.GitAnalyzer._get_diff_from_head')
    def test_get_changes_no_changes(
        self, 
        mock_diff, 
        mock_working, 
        mock_commit, 
        mock_validate, 
        git_analyzer
    ):
        """변경사항이 없는 경우 테스트"""
        mock_validate.return_value = True
        mock_commit.return_value = None
        mock_working.return_value = None
        mock_diff.return_value = None
        
        result = git_analyzer.get_changes()
        
        assert result == "변경사항이 없습니다. 작업 디렉토리가 깨끗합니다."
    
    @patch('ts_cli.vcs.git_analyzer.subprocess.run')
    def test_run_git_command_success(self, mock_run, git_analyzer):
        """Git 명령어 실행 성공 테스트"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="test output",
            stderr=""
        )
        
        result = git_analyzer._run_git_command(["git", "status"], check_repo=False)
        
        assert result == "test output"
        mock_run.assert_called_once()
    
    @patch('ts_cli.vcs.git_analyzer.subprocess.run')
    def test_run_git_command_failure(self, mock_run, git_analyzer):
        """Git 명령어 실행 실패 테스트"""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="error message"
        )
        
        result = git_analyzer._run_git_command(["git", "status"], check_repo=False)
        
        assert result is None
    
    @patch('ts_cli.vcs.git_analyzer.subprocess.run')
    def test_run_git_command_timeout(self, mock_run, git_analyzer):
        """Git 명령어 실행 타임아웃 테스트"""
        mock_run.side_effect = subprocess.TimeoutExpired(["git", "status"], 30)
        
        result = git_analyzer._run_git_command(["git", "status"], check_repo=False)
        
        assert result is None
    
    def test_parse_git_status(self, git_analyzer):
        """Git 상태 코드 파싱 테스트"""
        test_cases = [
            ("A ", "추가됨 (Staged)"),
            ("M ", "수정됨 (Staged)"),
            ("D ", "삭제됨 (Staged)"),
            (" M", "수정됨 (Unstaged)"),
            ("??", "추적되지 않음"),
            ("MM", "수정됨 (Staged + Unstaged)"),
            ("XY", "알 수 없는 상태 (XY)"),
        ]
        
        for status_code, expected in test_cases:
            result = git_analyzer._parse_git_status(status_code)
            assert result == expected
    
    @patch('ts_cli.vcs.git_analyzer.GitAnalyzer.validate_repository')
    @patch('ts_cli.vcs.git_analyzer.GitAnalyzer._get_current_branch')
    @patch('ts_cli.vcs.git_analyzer.GitAnalyzer._get_remote_url')
    @patch('ts_cli.vcs.git_analyzer.GitAnalyzer._get_commit_count')
    @patch('ts_cli.vcs.git_analyzer.GitAnalyzer._get_status_summary')
    def test_get_repository_info_success(
        self,
        mock_status,
        mock_count,
        mock_remote,
        mock_branch,
        mock_validate,
        git_analyzer
    ):
        """저장소 정보 조회 성공 테스트"""
        mock_validate.return_value = True
        mock_branch.return_value = "main"
        mock_remote.return_value = "https://github.com/test/repo.git"
        mock_count.return_value = 42
        mock_status.return_value = {"has_changes": False}
        
        result = git_analyzer.get_repository_info()
        
        assert result["vcs_type"] == "git"
        assert result["is_valid"] is True
        assert result["current_branch"] == "main"
        assert result["remote_url"] == "https://github.com/test/repo.git"
        assert result["commit_count"] == 42
        assert result["has_changes"] is False
    
    @patch('ts_cli.vcs.git_analyzer.GitAnalyzer.validate_repository')
    def test_get_repository_info_invalid(self, mock_validate, git_analyzer):
        """유효하지 않은 저장소 정보 조회 테스트"""
        mock_validate.return_value = False
        
        result = git_analyzer.get_repository_info()
        
        assert result == {}


class TestRepositoryErrors:
    """저장소 오류 클래스 테스트"""
    
    def test_repository_error_without_path(self):
        """경로 없는 RepositoryError 테스트"""
        error = RepositoryError("Test error message")
        
        assert str(error) == "저장소 분석 오류: Test error message"
        assert error.message == "Test error message"
        assert error.path is None
    
    def test_repository_error_with_path(self):
        """경로 있는 RepositoryError 테스트"""
        test_path = Path("/test/path")
        error = RepositoryError("Test error message", test_path)
        
        assert str(error) == f"저장소 분석 오류 ({test_path}): Test error message"
        assert error.message == "Test error message"
        assert error.path == test_path
    
    def test_invalid_repository_error_inheritance(self):
        """InvalidRepositoryError 상속 테스트"""
        error = InvalidRepositoryError("Invalid repo")
        
        assert isinstance(error, RepositoryError)
        assert "Invalid repo" in str(error)