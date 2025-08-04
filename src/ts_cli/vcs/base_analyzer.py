"""
VCS 저장소 분석기 추상 기반 클래스

전략 패턴을 사용하여 다양한 VCS 시스템을 지원하기 위한 추상 인터페이스를 정의합니다.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional


class RepositoryAnalyzer(ABC):
    """
    저장소 분석기 추상 기반 클래스
    
    모든 VCS 분석기는 이 클래스를 상속받아 구현해야 합니다.
    """
    
    def __init__(self, path: Path) -> None:
        """
        분석기 초기화
        
        Args:
            path: 분석할 저장소 경로
        """
        self.path = path
        self.repo_path = path.resolve()
    
    @abstractmethod
    def validate_repository(self) -> bool:
        """
        저장소 유효성 검증
        
        Returns:
            저장소가 유효하면 True, 그렇지 않으면 False
        """
        pass
    
    @abstractmethod
    def get_changes(self) -> str:
        """
        저장소의 변경사항 분석 텍스트를 반환
        
        Returns:
            분석된 변경사항 텍스트
            
        Raises:
            RepositoryError: 저장소 분석 중 오류 발생시
        """
        pass
    
    @abstractmethod
    def get_repository_info(self) -> Dict[str, Any]:
        """
        저장소 기본 정보 반환
        
        Returns:
            저장소 정보를 담은 딕셔너리
        """
        pass
    
    def get_vcs_type(self) -> str:
        """
        VCS 타입 반환
        
        Returns:
            VCS 타입 문자열 (예: 'git', 'svn', 'hg')
        """
        return self.__class__.__name__.lower().replace('analyzer', '')
    
    def __str__(self) -> str:
        """문자열 표현"""
        return f"{self.__class__.__name__}({self.repo_path})"
    
    def __repr__(self) -> str:
        """개발자 표현"""
        return f"{self.__class__.__name__}(path='{self.repo_path}')"


class RepositoryError(Exception):
    """
    저장소 분석 중 발생하는 오류를 나타내는 예외 클래스
    """
    
    def __init__(self, message: str, path: Optional[Path] = None) -> None:
        """
        RepositoryError 초기화
        
        Args:
            message: 오류 메시지
            path: 오류가 발생한 저장소 경로
        """
        self.message = message
        self.path = path
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        """오류 메시지 포맷팅"""
        if self.path:
            return f"저장소 분석 오류 ({self.path}): {self.message}"
        return f"저장소 분석 오류: {self.message}"


class UnsupportedVCSError(RepositoryError):
    """
    지원하지 않는 VCS 타입에 대한 예외 클래스
    """
    pass


class InvalidRepositoryError(RepositoryError):
    """
    유효하지 않은 저장소에 대한 예외 클래스
    """
    pass