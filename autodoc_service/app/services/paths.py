"""
경로 관리 서비스

템플릿 및 문서 경로 관리를 위한 유틸리티 함수들
"""
import os
from pathlib import Path
from typing import Optional


def get_autodoc_root() -> Path:
    """autodoc_service 루트 디렉터리 경로 반환"""
    current_file = Path(__file__).resolve()
    # /app/services/paths.py -> /autodoc_service/
    return current_file.parent.parent.parent


def get_templates_dir() -> Path:
    """템플릿 디렉터리 경로 반환
    
    우선순위:
    1. 환경변수 AUTODOC_TPL_DIR
    2. 기본 경로: <autodoc_service>/templates
    """
    env_path = os.environ.get('AUTODOC_TPL_DIR')
    if env_path:
        return Path(env_path).resolve()
    
    return get_autodoc_root() / "templates"


def get_documents_dir() -> Path:
    """문서 출력 디렉터리 경로 반환
    
    없으면 자동 생성
    """
    doc_dir = get_autodoc_root() / "documents"
    doc_dir.mkdir(parents=True, exist_ok=True)
    return doc_dir


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