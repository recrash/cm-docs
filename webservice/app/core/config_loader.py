# app/core/config_loader.py
import json
import os
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# 신규: 최우선 오버라이드(파일 경로 직접 지정)
ENV_OVERRIDE = "CMDOCS_CONFIG"
# 기존 호환: 데이터 루트
ENV_DATA_ROOT = "WEBSERVICE_DATA_PATH"

def _is_development_environment():
    """개발환경 여부 판단 (패키지 설치 여부로 구분)"""
    try:
        # __file__이 site-packages에 있으면 프로덕션 환경
        return 'site-packages' not in str(Path(__file__).resolve())
    except Exception:
        return True  # 안전한 fallback

def _find_repo_root(start: Optional[Path] = None) -> Path:
    """리포지토리 루트를 추정(.git 또는 pyproject.toml) — 실패 시 CWD"""
    p = (start or Path(__file__)).resolve()
    for parent in [p, *p.parents]:
        if (parent / ".git").exists() or (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd().resolve()

def _std_candidates() -> List[Path]:
    """리포 루트 기준 표준 위치들"""
    root = _find_repo_root()
    return [
        root / "webservice" / "config" / "config.ci.json",
        root / "webservice" / "config" / "config.test.json",
        root / "webservice" / "config" / "config.json",
        root / "config"     / "config.ci.json",
        root / "config"     / "config.test.json",
        root / "config"     / "config.json",
        root / "config.json",
    ]

def _resolve_config_path():
    """설정 파일 경로를 해결합니다."""
    tried: List[Path] = []

    # 0순위: 파일 직접 지정(CI/테스트/운영 어디서나 동일)
    env_override = os.getenv(ENV_OVERRIDE)
    logger.info(f"[CONFIG_DEBUG] {ENV_OVERRIDE}={env_override}")
    if env_override:
        p = Path(env_override).expanduser().resolve()
        logger.info(f"[CONFIG_DEBUG] 오버라이드 경로 확인: {p}")
        tried.append(p)
        if p.exists():
            logger.info(f"[CONFIG_DEBUG] 오버라이드 설정 파일 사용: {p}")
            return str(p)
        else:
            logger.warning(f"[CONFIG_DEBUG] 오버라이드 설정 파일이 존재하지 않음: {p}")

    # 1순위: 데이터 루트(운영 기본)
    env_path = os.getenv(ENV_DATA_ROOT)
    logger.info(f"[CONFIG_DEBUG] {ENV_DATA_ROOT}={env_path}")
    
    if env_path:
        try:
            config_path = Path(env_path).expanduser().resolve() / "config.json"
            logger.info(f"[CONFIG_DEBUG] 환경변수 기반 경로 확인: {config_path}")
            tried.append(config_path)
            if config_path.exists():
                logger.info(f"[CONFIG_DEBUG] 환경변수 기반 설정 파일 사용: {config_path}")
                return str(config_path)
            else:
                logger.warning(f"[CONFIG_DEBUG] 환경변수 기반 설정 파일이 존재하지 않음: {config_path}")
        except Exception as e:
            logger.error(f"[CONFIG_DEBUG] 환경변수 기반 경로 처리 중 오류: {e}")
    
    # 2순위: Development 환경에서만 상대 경로 허용
    if _is_development_environment():
        try:
            # 표준 후보들(리포 루트 기준)
            for cand in _std_candidates():
                logger.info(f"[CONFIG_DEBUG] 개발환경 기반 후보 확인: {cand}")
                tried.append(cand)
                if cand.exists():
                    logger.info(f"[CONFIG_DEBUG] 개발환경 설정 파일 사용: {cand}")
                    return str(cand)

            # 마지막: CWD/config.json
            cwd_config = Path.cwd().resolve() / "config.json"
            logger.info(f"[CONFIG_DEBUG] 현재 작업 디렉토리 경로 확인: {cwd_config}")
            tried.append(cwd_config)
            if cwd_config.exists():
                logger.info(f"[CONFIG_DEBUG] 현재 작업 디렉토리에서 설정 파일 사용: {cwd_config}")
                return str(cwd_config)
                
        except Exception as e:
            logger.error(f"[CONFIG_DEBUG] 개발환경 경로 처리 중 오류: {e}")
    else:
        logger.info("[CONFIG_DEBUG] 프로덕션 환경에서는 환경변수만 허용")
    
    # 설정 파일을 찾을 수 없는 경우
    if env_override:
        error_msg = (f"{ENV_OVERRIDE}가 설정되었지만 설정 파일을 찾을 수 없습니다: {env_override}\n"
                     f"Tried:\n" + "\n".join(str(t) for t in tried))
    elif env_path:
        error_msg = (f"{ENV_DATA_ROOT}가 설정되었지만 설정 파일을 찾을 수 없습니다: {env_path}/config.json\n"
                     f"Tried:\n" + "\n".join(str(t) for t in tried))
    else:
        error_msg = ("설정 파일을 찾을 수 없습니다(override/data_root 미설정). Tried:\n" 
                     + "\n".join(str(t) for t in tried))
    
    logger.error(f"[CONFIG_DEBUG] {error_msg}")
    raise FileNotFoundError(error_msg)

def load_config(path="config.json", *, strict: bool = False):
    """설정 파일을 읽어와 파이썬 딕셔너리로 반환합니다."""
    try:
        # 기본 경로인 경우 표준 경로 해결 로직 사용
        if path == "config.json":
            resolved_path = _resolve_config_path()
        # 명시적 경로가 상대 경로인 경우 프로젝트 루트에서 찾기
        elif not os.path.isabs(path):
            project_root = str(_find_repo_root())
            resolved_path = os.path.join(project_root, path)
        else:
            resolved_path = path
        
        logger.info(f"[CONFIG_DEBUG] 최종 해결된 설정 파일 경로: {resolved_path}")
        logger.info(f"[CONFIG_DEBUG] 현재 작업 디렉토리: {os.getcwd()}")
        logger.info(f"[CONFIG_DEBUG] 파일 존재 여부: {os.path.exists(resolved_path)}")
        
        with open(resolved_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            rag_enabled = config_data.get('rag', {}).get('enabled', False)
            logger.info(f"[CONFIG_DEBUG] RAG enabled 설정값: {rag_enabled}")
            logger.info(f"[CONFIG_DEBUG] RAG 전체 설정: {config_data.get('rag', {})}")
            return config_data
            
    except FileNotFoundError as e:
        logger.error(f"설정 파일을 찾을 수 없습니다: {e}")
        if strict:
            raise
        return None
    except json.JSONDecodeError as e:
        logger.error(f"설정 파일 JSON 파싱 오류: {e}")
        if strict:
            raise
        return None
    except Exception as e:
        logger.error(f"설정 파일 로딩 중 예상치 못한 오류: {e}")
        if strict:
            raise
        return None

def get_data_directory_path():
    """데이터 디렉토리 루트 경로를 반환합니다 (paths.py 활용)"""
    from .paths import get_data_root
    return str(get_data_root())

def verify_environment():
    """환경변수와 디렉토리 설정 검증"""
    from .paths import verify_data_directories
    
    env_override = os.getenv(ENV_OVERRIDE)
    env_path = os.getenv(ENV_DATA_ROOT)
    is_production = not _is_development_environment()
    
    result = {
        'environment_type': 'production' if is_production else 'development',
        'cmdocs_config_set': env_override is not None,
        'cmdocs_config_value': env_override,
        'webservice_data_path_set': env_path is not None,
        'webservice_data_path_value': env_path,
        'directories_writable': verify_data_directories(),
        'config_path_resolved': False,
        'issues': []
    }
    
    # 설정 파일 경로 검증
    try:
        config_path = _resolve_config_path()
        result['config_path_resolved'] = True
        result['resolved_config_path'] = config_path
    except FileNotFoundError as e:
        result['issues'].append(str(e))
        result['resolved_config_path'] = None
    
    # 프로덕션 환경 검증
    if is_production:
        if not env_override and not env_path:
            result['issues'].append(f"프로덕션 환경에서 {ENV_OVERRIDE} 또는 {ENV_DATA_ROOT} 환경변수가 설정되지 않았습니다.")
        elif env_path and not Path(env_path).exists():
            result['issues'].append(f"{ENV_DATA_ROOT} 경로가 존재하지 않습니다: {env_path}")
        elif env_override and not Path(env_override).exists():
            result['issues'].append(f"{ENV_OVERRIDE} 파일이 존재하지 않습니다: {env_override}")
    
    # 디렉토리 쓰기 권한 검증
    if not result['directories_writable']:
        result['issues'].append("일부 데이터 디렉토리에 쓰기 권한이 없습니다.")
    
    return result