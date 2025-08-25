"""
경로 관리 서비스

환경 변수 기반 경로 관리를 위한 유틸리티 함수들
프로덕션 환경에서는 AUTODOC_DATA_PATH 환경 변수를 사용
"""
import os
from pathlib import Path


def get_data_root() -> Path:
    """
    AUTODOC_DATA_PATH 환경 변수에서 데이터 루트 경로를 가져옵니다.
    
    우선순위:
    1. 환경변수 AUTODOC_DATA_PATH (프로덕션)
    2. 기본 경로: <autodoc_service>/data (개발환경)
    
    Returns:
        Path: 데이터 루트 디렉터리 경로
    """
    env_path = os.getenv("AUTODOC_DATA_PATH")
    if env_path:
        return Path(env_path).resolve()
    
    # 개발환경 기본값: autodoc_service 루트 디렉터리의 data 폴더
    current_file = Path(__file__).resolve()
    autodoc_root = current_file.parent.parent.parent
    return autodoc_root / "data"


def get_templates_dir() -> Path:
    """템플릿 디렉터리 경로 반환
    
    Returns:
        Path: 템플릿 디렉터리 경로 (자동 생성됨)
    """
    templates_dir = get_data_root() / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    return templates_dir


def get_documents_dir() -> Path:
    """문서 출력 디렉터리 경로 반환
    
    Returns:
        Path: 문서 출력 디렉터리 경로 (자동 생성됨)
    """
    documents_dir = get_data_root() / "documents"
    documents_dir.mkdir(parents=True, exist_ok=True)
    return documents_dir


def get_logs_dir() -> Path:
    """로그 디렉터리 경로 반환
    
    Returns:
        Path: 로그 디렉터리 경로 (자동 생성됨)
    """
    logs_dir = get_data_root() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def verify_template_exists(template_name: str) -> Path:
    """템플릿 파일 존재 여부 확인 및 경로 반환
    
    Args:
        template_name: 템플릿 파일명 (예: 'template.docx')
        
    Returns:
        Path: 템플릿 파일 경로
        
    Raises:
        FileNotFoundError: 템플릿 파일이 존재하지 않는 경우
    """
    template_path = get_templates_dir() / template_name
    if not template_path.exists():
        raise FileNotFoundError(
            f"템플릿 파일을 찾을 수 없습니다: {template_path}\n"
            f"템플릿 디렉터리: {get_templates_dir()}"
        )
    return template_path


def verify_documents_writable() -> bool:
    """문서 디렉터리 쓰기 권한 확인"""
    try:
        doc_dir = get_documents_dir()
        test_file = doc_dir / ".write_test"
        test_file.touch()
        test_file.unlink()
        return True
    except (PermissionError, OSError):
        return False