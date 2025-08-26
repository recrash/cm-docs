"""
git_analyzer.py 모듈 테스트
"""
import pytest
import git
from unittest.mock import Mock, patch, MagicMock
from app.core.git_analyzer import get_git_analysis_text


class TestGitAnalyzer:
    """Git 분석기 테스트"""
    
    @patch('src.git_analyzer.git.Repo')
    def test_successful_git_analysis(self, mock_repo_class):
        """성공적인 Git 분석 테스트"""
        # Mock 설정
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        
        # 커밋 Mock 설정
        mock_base_commit = Mock()
        mock_base_commit.hexsha = "abc123"
        mock_head_commit = Mock()
        mock_head_commit.hexsha = "def456"
        
        mock_repo.merge_base.return_value = [mock_base_commit]
        mock_repo.commit.return_value = mock_head_commit
        
        # 커밋 목록 Mock
        mock_commit1 = Mock()
        mock_commit1.summary = "feat: 새 기능 추가"
        mock_commit2 = Mock()
        mock_commit2.summary = "fix: 버그 수정"
        
        mock_repo.iter_commits.return_value = [mock_commit2, mock_commit1]
        
        # diff Mock
        mock_diff = Mock()
        mock_diff.a_path = "src/test.py"
        mock_diff.diff = b"+def new_function():\n+    return True"
        
        mock_base_commit.diff.return_value = [mock_diff]
        
        result = get_git_analysis_text("/test/repo")
        
        assert "### 커밋 메시지 목록:" in result
        assert "feat: 새 기능 추가" in result
        assert "fix: 버그 수정" in result
        assert "### 주요 코드 변경 내용 (diff):" in result
        assert "src/test.py" in result
        assert "+def new_function():" in result
    
    @patch('src.git_analyzer.git.Repo')
    def test_no_merge_base_found(self, mock_repo_class):
        """공통 조상을 찾을 수 없는 경우 테스트"""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.merge_base.return_value = []
        
        result = get_git_analysis_text("/test/repo")
        
        assert "오류: 공통 조상을 찾을 수 없습니다." in result
    
    @patch('src.git_analyzer.git.Repo')
    def test_git_repo_not_found(self, mock_repo_class):
        """Git 저장소를 찾을 수 없는 경우 테스트"""
        mock_repo_class.side_effect = git.exc.InvalidGitRepositoryError("Not a git repository")
        
        result = get_git_analysis_text("/invalid/repo")
        
        assert "Git 분석 중 오류 발생:" in result
        assert "Not a git repository" in result
    
    @patch('src.git_analyzer.git.Repo')
    def test_long_diff_truncation(self, mock_repo_class):
        """긴 diff 내용 잘림 테스트"""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        
        # 기본 설정
        mock_base_commit = Mock()
        mock_base_commit.hexsha = "abc123"
        mock_head_commit = Mock()
        mock_head_commit.hexsha = "def456"
        
        mock_repo.merge_base.return_value = [mock_base_commit]
        mock_repo.commit.return_value = mock_head_commit
        mock_repo.iter_commits.return_value = []
        
        # 긴 diff 생성 (20줄 넘게)
        long_diff_lines = [f"+line {i}" for i in range(25)]
        long_diff_content = "\n".join(long_diff_lines)
        
        mock_diff = Mock()
        mock_diff.a_path = "src/long_file.py"
        mock_diff.diff = long_diff_content.encode('utf-8')
        
        mock_base_commit.diff.return_value = [mock_diff]
        
        result = get_git_analysis_text("/test/repo")
        
        assert "src/long_file.py" in result
        assert "... (내용 생략) ..." in result
        assert "+line 19" in result  # 20줄까지는 포함
        assert "+line 24" not in result  # 21줄부터는 제외
    
    @patch('src.git_analyzer.git.Repo')
    def test_unicode_handling_in_diff(self, mock_repo_class):
        """diff에서 유니코드 처리 테스트"""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        
        # 기본 설정
        mock_base_commit = Mock()
        mock_base_commit.hexsha = "abc123"
        mock_head_commit = Mock()
        mock_head_commit.hexsha = "def456"
        
        mock_repo.merge_base.return_value = [mock_base_commit]
        mock_repo.commit.return_value = mock_head_commit
        mock_repo.iter_commits.return_value = []
        
        # 한글이 포함된 diff
        korean_diff = "+한글 주석 추가\n+def 함수():"
        
        mock_diff = Mock()
        mock_diff.a_path = "src/korean.py"
        mock_diff.diff = korean_diff.encode('utf-8')
        
        mock_base_commit.diff.return_value = [mock_diff]
        
        result = get_git_analysis_text("/test/repo")
        
        assert "한글 주석 추가" in result
        assert "def 함수():" in result
    
    @patch('src.git_analyzer.git.Repo')
    def test_multiple_commits_ordering(self, mock_repo_class):
        """여러 커밋의 순서 테스트"""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        
        # 기본 설정
        mock_base_commit = Mock()
        mock_head_commit = Mock()
        mock_repo.merge_base.return_value = [mock_base_commit]
        mock_repo.commit.return_value = mock_head_commit
        
        # 커밋 순서 테스트 (역순으로 반환되는 것을 시간순으로 정렬)
        mock_commit1 = Mock()
        mock_commit1.summary = "첫 번째 커밋"
        mock_commit2 = Mock()
        mock_commit2.summary = "두 번째 커밋"
        mock_commit3 = Mock()
        mock_commit3.summary = "세 번째 커밋"
        
        # iter_commits는 최신부터 반환하므로 역순
        mock_repo.iter_commits.return_value = [mock_commit3, mock_commit2, mock_commit1]
        mock_base_commit.diff.return_value = []
        
        result = get_git_analysis_text("/test/repo")
        
        # reversed()로 인해 시간순으로 정렬되어야 함
        commit_section = result.split("### 주요 코드 변경 내용")[0]
        first_pos = commit_section.find("첫 번째 커밋")
        second_pos = commit_section.find("두 번째 커밋")
        third_pos = commit_section.find("세 번째 커밋")
        
        assert first_pos < second_pos < third_pos