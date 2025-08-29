"""
VCS (Version Control System) 분석기 팩토리 모듈

전략 패턴을 사용하여 다양한 VCS 시스템을 지원합니다.
"""

from pathlib import Path
from typing import Optional

from .base_analyzer import RepositoryAnalyzer
from .git_analyzer import GitAnalyzer
from .svn_analyzer import SVNAnalyzer


def get_analyzer(path: Path) -> Optional[RepositoryAnalyzer]:
    """
    저장소 경로를 분석하여 적절한 VCS 분석기를 반환합니다.

    Args:
        path: 분석할 저장소 경로

    Returns:
        적절한 VCS 분석기 인스턴스 또는 None (지원하지 않는 VCS인 경우)
    """
    if not path.exists() or not path.is_dir():
        return None

    # Git 저장소 확인
    git_dir = path / ".git"
    if git_dir.exists():
        return GitAnalyzer(path)

    # SVN 저장소 확인
    svn_dir = path / ".svn"
    if svn_dir.exists():
        return SVNAnalyzer(path)

    # 향후 다른 VCS 지원 추가 가능
    # if (path / ".hg").exists():
    #     return MercurialAnalyzer(path)

    return None


def get_supported_vcs_types() -> list[str]:
    """
    지원하는 VCS 타입 목록을 반환합니다.

    Returns:
        지원하는 VCS 타입 문자열 리스트
    """
    return ["git", "svn"]


__all__ = [
    "get_analyzer",
    "get_supported_vcs_types",
    "RepositoryAnalyzer",
    "GitAnalyzer",
    "SVNAnalyzer",
]
