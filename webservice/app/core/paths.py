"""
webservice 경로 관리 서비스

환경 변수 기반 경로 관리를 위한 유틸리티 함수들
프로덕션 환경에서는 WEBSERVICE_DATA_PATH 환경 변수를 사용
"""
import os
from pathlib import Path
from typing import Optional


def get_data_root() -> Path:
    """
    WEBSERVICE_DATA_PATH 환경 변수에서 데이터 루트 경로를 가져옵니다.
    
    우선순위:
    1. 환경변수 WEBSERVICE_DATA_PATH (프로덕션)
    2. 기본 경로: <webservice>/data (개발환경)
    
    Returns:
        Path: 데이터 루트 디렉터리 경로
    """
    env_path = os.getenv("WEBSERVICE_DATA_PATH")
    if env_path:
        return Path(env_path).resolve()
    
    # 개발환경 기본값: webservice 루트 디렉터리의 data 폴더
    current_file = Path(__file__).resolve()
    webservice_root = current_file.parent.parent
    return webservice_root / "data"


def get_logs_dir() -> Path:
    """로그 디렉터리 경로 반환
    
    Returns:
        Path: 로그 디렉터리 경로 (자동 생성됨)
    """
    logs_dir = get_data_root() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_models_dir() -> Path:
    """AI 모델 디렉터리 경로 반환
    
    Returns:
        Path: 모델 디렉터리 경로 (자동 생성됨)
    """
    models_dir = get_data_root() / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    return models_dir


def get_documents_dir() -> Path:
    """문서 출력 디렉터리 경로 반환
    
    Returns:
        Path: 문서 출력 디렉터리 경로 (자동 생성됨)
    """
    documents_dir = get_data_root() / "documents"
    documents_dir.mkdir(parents=True, exist_ok=True)
    return documents_dir


def get_templates_dir() -> Path:
    """템플릿 디렉터리 경로 반환
    
    Returns:
        Path: 템플릿 디렉터리 경로 (자동 생성됨)
    """
    templates_dir = get_data_root() / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    return templates_dir


def get_prompts_dir() -> Path:
    """프롬프트 디렉터리 경로 반환
    
    Returns:
        Path: 프롬프트 디렉터리 경로 (자동 생성됨)
    """
    prompts_dir = get_data_root() / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    return prompts_dir


def get_outputs_dir() -> Path:
    """Excel 출력 디렉터리 경로 반환
    
    Returns:
        Path: 출력 디렉터리 경로 (자동 생성됨)
    """
    outputs_dir = get_data_root() / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    return outputs_dir


def get_vector_db_dir() -> Path:
    """벡터 데이터베이스 디렉터리 경로 반환
    
    Returns:
        Path: 벡터 DB 디렉터리 경로 (자동 생성됨)
    """
    vector_db_dir = get_data_root() / "db"
    vector_db_dir.mkdir(parents=True, exist_ok=True)
    return vector_db_dir


def get_default_model_path() -> Path:
    """기본 임베딩 모델 경로 반환
    
    Returns:
        Path: 기본 임베딩 모델 경로
    """
    return get_models_dir() / "ko-sroberta-multitask"


def verify_data_directories() -> bool:
    """모든 데이터 디렉터리가 쓰기 가능한지 확인
    
    Returns:
        bool: 모든 디렉터리가 쓰기 가능한 경우 True
    """
    directories = [
        get_logs_dir(),
        get_models_dir(),
        get_documents_dir(),
        get_templates_dir(),
        get_prompts_dir(),
        get_outputs_dir(),
        get_vector_db_dir()
    ]
    
    for directory in directories:
        try:
            test_file = directory / ".write_test"
            test_file.touch()
            test_file.unlink()
        except (PermissionError, OSError):
            return False
    
    return True