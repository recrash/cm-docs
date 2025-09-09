"""
SVN 분석기 테스트

SVNAnalyzer 클래스의 기능을 검증하는 단위 테스트입니다.
"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from ts_cli.vcs.svn_analyzer import SVNAnalyzer
from ts_cli.vcs.base_analyzer import RepositoryError


class TestSVNAnalyzer:
    """SVNAnalyzer 테스트 클래스"""

    def setup_method(self):
        """테스트 메서드 실행 전 설정"""
        self.test_path = Path("/test/svn/repo")
        self.analyzer = SVNAnalyzer(self.test_path)

    def test_init(self):
        """SVNAnalyzer 초기화 테스트"""
        assert self.analyzer.path == self.test_path
        assert self.analyzer.repo_path == self.test_path.resolve()

    def test_get_vcs_type(self):
        """VCS 타입 반환 테스트"""
        assert self.analyzer.get_vcs_type() == "svn"

    @patch("ts_cli.vcs.svn_analyzer.subprocess.run")
    def test_validate_repository_success(self, mock_run):
        """유효한 SVN 저장소 검증 테스트"""
        # .svn 디렉토리 존재 모의
        with patch.object(Path, "exists", return_value=True):
            # svn info 명령어 성공 모의
            mock_run.return_value = Mock(stdout="URL: http://svn.example.com/repo\n")
            
            result = self.analyzer.validate_repository()
            
            assert result is True
            mock_run.assert_called_once()

    def test_validate_repository_no_svn_dir(self):
        """SVN 디렉토리가 없는 경우 테스트"""
        with patch.object(Path, "exists", return_value=False):
            result = self.analyzer.validate_repository()
            assert result is False

    @patch("ts_cli.vcs.svn_analyzer.subprocess.run")
    def test_validate_repository_command_fails(self, mock_run):
        """SVN 명령어 실행 실패 테스트"""
        with patch.object(Path, "exists", return_value=True):
            mock_run.side_effect = subprocess.CalledProcessError(1, ["svn", "info"])
            
            result = self.analyzer.validate_repository()
            assert result is False

    @patch("ts_cli.vcs.svn_analyzer.SVNAnalyzer._run_svn_command")
    def test_get_changes_success(self, mock_run_command):
        """변경사항 분석 성공 테스트"""
        # SVN 명령어 결과 모의
        mock_run_command.side_effect = [
            "URL: http://svn.example.com/repo\nRevision: 123\n",  # svn info
            "M    modified_file.py\nA    new_file.py\n",  # svn status
            "--- modified_file.py\t(revision 122)\n+++ modified_file.py\t(working copy)\n@@ -1,3 +1,4 @@\n+new line\n",  # svn diff
            "r123 | user | 2023-12-01 | 1 line\nChanged modified_file.py\n"  # svn log
        ]
        
        result = self.analyzer.get_changes()
        
        assert "SVN 저장소 정보" in result
        assert "Working Directory 상태" in result
        assert "Working Directory vs HEAD 차이점" in result
        assert "최근 커밋 로그" in result
        assert "modified_file.py" in result
        assert mock_run_command.call_count == 4

    @patch("ts_cli.vcs.svn_analyzer.SVNAnalyzer._run_svn_command")
    def test_get_changes_no_changes(self, mock_run_command):
        """변경사항이 없는 경우 테스트"""
        mock_run_command.side_effect = [
            "URL: http://svn.example.com/repo\nRevision: 123\n",  # svn info
            "",  # svn status (변경사항 없음)
            "",  # svn diff (차이점 없음)
            None  # svn log (실행되지 않음)
        ]
        
        result = self.analyzer.get_changes()
        
        assert "SVN 저장소 정보" in result
        # status와 diff가 비어있어도 info는 포함됨
        assert "URL:" in result

    @patch("ts_cli.vcs.svn_analyzer.SVNAnalyzer._run_svn_command")
    def test_get_changes_svn_error(self, mock_run_command):
        """SVN 명령어 오류 테스트"""
        mock_run_command.side_effect = subprocess.CalledProcessError(
            1, ["svn", "info"], stderr=b"svn: E155007: Working copy not found"
        )
        
        with pytest.raises(RepositoryError) as exc_info:
            self.analyzer.get_changes()
        
        assert "SVN 명령어 실행 실패" in str(exc_info.value)

    @patch("ts_cli.vcs.svn_analyzer.SVNAnalyzer._run_svn_command")
    def test_get_repository_info_success(self, mock_run_command):
        """저장소 정보 수집 성공 테스트"""
        mock_run_command.side_effect = [
            "URL: http://svn.example.com/repo\nRevision: 123\nRepository Root: http://svn.example.com\n",  # svn info
            "M    modified_file.py\nA    new_file.py\nD    deleted_file.py\n"  # svn status
        ]
        
        info = self.analyzer.get_repository_info()
        
        assert info["vcs_type"] == "svn"
        assert info["repository_url"] == "http://svn.example.com/repo"
        assert info["current_revision"] == "123"
        assert info["repository_root"] == "http://svn.example.com"
        assert info["modified_files_count"] == 1
        assert info["added_files_count"] == 1
        assert info["deleted_files_count"] == 1
        assert info["has_changes"] is True

    @patch("ts_cli.vcs.svn_analyzer.SVNAnalyzer._run_svn_command")
    def test_get_repository_info_no_changes(self, mock_run_command):
        """변경사항이 없는 저장소 정보 테스트"""
        mock_run_command.side_effect = [
            "URL: http://svn.example.com/repo\nRevision: 123\n",  # svn info
            ""  # svn status (변경사항 없음)
        ]
        
        info = self.analyzer.get_repository_info()
        
        assert info["has_changes"] is False
        assert info["modified_files_count"] == 0
        assert info["added_files_count"] == 0
        assert info["deleted_files_count"] == 0

    def test_run_svn_command_success(self):
        """SVN 명령어 실행 성공 테스트"""
        with patch("ts_cli.vcs.svn_analyzer.subprocess.run") as mock_run:
            with patch.object(Path, "exists", return_value=True):
                mock_run.return_value = Mock(stdout="test output")
                
                result = self.analyzer._run_svn_command(["svn", "info"])
                
                assert result == "test output"
                mock_run.assert_called_once_with(
                    ["svn", "info"],
                    cwd=str(self.test_path),
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    timeout=30,
                    check=True
                )

    def test_run_svn_command_repo_not_exists(self):
        """저장소 경로가 존재하지 않는 경우 테스트"""
        with patch.object(Path, "exists", return_value=False):
            with pytest.raises(RepositoryError) as exc_info:
                self.analyzer._run_svn_command(["svn", "info"])
            
            assert "저장소 경로가 존재하지 않습니다" in str(exc_info.value)

    def test_run_svn_command_timeout(self):
        """SVN 명령어 타임아웃 테스트"""
        with patch("ts_cli.vcs.svn_analyzer.subprocess.run") as mock_run:
            with patch.object(Path, "exists", return_value=True):
                mock_run.side_effect = subprocess.TimeoutExpired(["svn", "info"], 30)
                
                with pytest.raises(RepositoryError) as exc_info:
                    self.analyzer._run_svn_command(["svn", "info"])
                
                assert "SVN 명령어 타임아웃" in str(exc_info.value)

    def test_run_svn_command_not_found(self):
        """SVN 명령어가 설치되지 않은 경우 테스트"""
        with patch("ts_cli.vcs.svn_analyzer.subprocess.run") as mock_run:
            with patch.object(Path, "exists", return_value=True):
                error = subprocess.CalledProcessError(127, ["svn", "info"])
                error.stderr = b"command not found"
                mock_run.side_effect = error
                
                with pytest.raises(RepositoryError) as exc_info:
                    self.analyzer._run_svn_command(["svn", "info"])
                
                assert "SVN 명령어가 설치되지 않았습니다" in str(exc_info.value)
                assert "TortoiseSVN" in str(exc_info.value)
                assert "brew install subversion" in str(exc_info.value)

    def test_run_svn_command_general_error(self):
        """일반적인 SVN 오류 테스트"""
        with patch("ts_cli.vcs.svn_analyzer.subprocess.run") as mock_run:
            with patch.object(Path, "exists", return_value=True):
                error = subprocess.CalledProcessError(1, ["svn", "info"])
                error.stderr = b"svn: E155007: Working copy not found"
                mock_run.side_effect = error
                
                with pytest.raises(RepositoryError) as exc_info:
                    self.analyzer._run_svn_command(["svn", "info"])
                
                assert "SVN 명령어 실행 실패" in str(exc_info.value)
                assert "Working copy not found" in str(exc_info.value)