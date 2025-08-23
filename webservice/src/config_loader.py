# src/config_loader.py
import json
import os
import logging

logger = logging.getLogger(__name__)

def load_config(path="config.json"):
    """설정 파일을 읽어와 파이썬 딕셔너리로 반환합니다."""
    try:
        # 기본 경로인 경우 하이브리드 경로 사용 (Production 우선, Development 대체)
        if path == "config.json":
            from pathlib import Path
            config_path = None
            
            # 1순위: Production 환경 (WEBSERVICE_DATA_PATH 환경변수 기반)
            env_path = os.getenv('WEBSERVICE_DATA_PATH')
            if env_path:
                try:
                    config_path = Path(env_path) / "config.json"
                    if not config_path.exists():
                        config_path = None
                except Exception:
                    config_path = None
            
            # 2순위: Development 환경 (코드 기준 상대 경로)
            if not config_path or not config_path.exists():
                try:
                    # src 폴더에서 webservice 폴더로 이동
                    src_dir = Path(__file__).parent  # src 폴더
                    webservice_root = src_dir.parent  # webservice 폴더
                    config_path = webservice_root / "config.json"
                except Exception:
                    config_path = Path("config.json")  # fallback
            
            path = str(config_path)
        
        # 명시적 경로가 상대 경로인 경우 프로젝트 루트에서 찾기
        elif not os.path.isabs(path):
            # 현재 파일의 디렉토리에서 프로젝트 루트로 이동
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)  # src/ 상위 디렉토리
            path = os.path.join(project_root, path)
        
        logger.info(f"[CONFIG_DEBUG] 해결된 설정 파일 경로: {path}")
        logger.info(f"[CONFIG_DEBUG] 현재 작업 디렉토리: {os.getcwd()}")
        logger.info(f"[CONFIG_DEBUG] 파일 존재 여부: {os.path.exists(path)}")
        
        with open(path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            rag_enabled = config_data.get('rag', {}).get('enabled', False)
            logger.info(f"[CONFIG_DEBUG] RAG enabled 설정값: {rag_enabled}")
            logger.info(f"[CONFIG_DEBUG] RAG 전체 설정: {config_data.get('rag', {})}")
            return config_data
    except FileNotFoundError:
        logger.error(f"오류: 설정 파일('{path}')을 찾을 수 없습니다.")
        return None

def get_data_directory_path():
    """데이터 디렉토리 루트 경로를 반환합니다 (환경변수 우선, 개발환경 fallback)"""
    import os
    from pathlib import Path
    
    # 1순위: Production 환경 (WEBSERVICE_DATA_PATH 환경변수 기반)
    env_path = os.getenv('WEBSERVICE_DATA_PATH')
    if env_path and Path(env_path).exists():
        return str(Path(env_path))
    
    # 2순위: Development 환경 (webservice/data/ 폴더)
    try:
        # src 폴더에서 webservice 폴더로 이동
        src_dir = Path(__file__).parent  # src 폴더
        webservice_root = src_dir.parent  # webservice 폴더
        data_path = webservice_root / "data"
        return str(data_path)
    except Exception:
        return "data"  # fallback