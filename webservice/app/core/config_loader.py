# src/config_loader.py
import json
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def _is_development_environment():
    """개발환경 여부 판단 (패키지 설치 여부로 구분)"""
    try:
        # __file__이 site-packages에 있으면 프로덕션 환경
        return 'site-packages' not in str(Path(__file__).resolve())
    except Exception:
        return True  # 안전한 fallback

def _resolve_config_path():
    """설정 파일 경로를 해결합니다."""
    # 1순위: Production 환경 (WEBSERVICE_DATA_PATH 환경변수 기반)
    env_path = os.getenv('WEBSERVICE_DATA_PATH')
    logger.info(f"[CONFIG_DEBUG] WEBSERVICE_DATA_PATH 환경변수: {env_path}")
    
    if env_path:
        try:
            config_path = Path(env_path) / "config.json"
            logger.info(f"[CONFIG_DEBUG] 환경변수 기반 경로 확인: {config_path}")
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
            # 개발환경: app/core에서 webservice 폴더로 이동
            core_dir = Path(__file__).parent  # app/core 폴더
            app_dir = core_dir.parent  # app 폴더  
            webservice_root = app_dir.parent  # webservice 폴더  
            config_path = webservice_root / "config.json"
            logger.info(f"[CONFIG_DEBUG] 개발환경 기반 경로 확인: {config_path}")
            
            if config_path.exists():
                logger.info(f"[CONFIG_DEBUG] 개발환경 설정 파일 사용: {config_path}")
                return str(config_path)
            else:
                logger.warning(f"[CONFIG_DEBUG] 개발환경 설정 파일이 존재하지 않음: {config_path}")
                
                # 추가 검색: 현재 작업 디렉토리에서 config.json 찾기
                cwd_config = Path.cwd() / "config.json"
                logger.info(f"[CONFIG_DEBUG] 현재 작업 디렉토리 경로 확인: {cwd_config}")
                if cwd_config.exists():
                    logger.info(f"[CONFIG_DEBUG] 현재 작업 디렉토리에서 설정 파일 사용: {cwd_config}")
                    return str(cwd_config)
                
        except Exception as e:
            logger.error(f"[CONFIG_DEBUG] 개발환경 경로 처리 중 오류: {e}")
    else:
        logger.info("[CONFIG_DEBUG] 프로덕션 환경에서는 환경변수만 허용")
    
    # 설정 파일을 찾을 수 없는 경우
    if env_path:
        error_msg = f"환경변수 WEBSERVICE_DATA_PATH가 설정되었지만 설정 파일을 찾을 수 없습니다: {env_path}/config.json"
    else:
        error_msg = "환경변수 WEBSERVICE_DATA_PATH가 설정되지 않았고, 설정 파일을 찾을 수 없습니다."
    
    logger.error(f"[CONFIG_DEBUG] {error_msg}")
    raise FileNotFoundError(error_msg)

def load_config(path="config.json"):
    """설정 파일을 읽어와 파이썬 딕셔너리로 반환합니다."""
    try:
        # 기본 경로인 경우 표준 경로 해결 로직 사용
        if path == "config.json":
            resolved_path = _resolve_config_path()
        # 명시적 경로가 상대 경로인 경우 프로젝트 루트에서 찾기
        elif not os.path.isabs(path):
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)  # src/ 상위 디렉토리
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
        return None
    except json.JSONDecodeError as e:
        logger.error(f"설정 파일 JSON 파싱 오류: {e}")
        return None
    except Exception as e:
        logger.error(f"설정 파일 로딩 중 예상치 못한 오류: {e}")
        return None

def get_data_directory_path():
    """데이터 디렉토리 루트 경로를 반환합니다 (paths.py 활용)"""
    from .paths import get_data_root
    return str(get_data_root())

def verify_environment():
    """환경변수와 디렉토리 설정 검증"""
    from .paths import verify_data_directories
    
    env_path = os.getenv('WEBSERVICE_DATA_PATH')
    is_production = not _is_development_environment()
    
    result = {
        'environment_type': 'production' if is_production else 'development',
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
        if not env_path:
            result['issues'].append("프로덕션 환경에서 WEBSERVICE_DATA_PATH 환경변수가 설정되지 않았습니다.")
        elif not Path(env_path).exists():
            result['issues'].append(f"WEBSERVICE_DATA_PATH 경로가 존재하지 않습니다: {env_path}")
    
    # 디렉토리 쓰기 권한 검증
    if not result['directories_writable']:
        result['issues'].append("일부 데이터 디렉토리에 쓰기 권한이 없습니다.")
    
    return result