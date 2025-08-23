# src/config_loader.py
import json
import os
import logging

logger = logging.getLogger(__name__)

def load_config(path="config.json"):
    """설정 파일을 읽어와 파이썬 딕셔너리로 반환합니다."""
    try:
        # 상대 경로인 경우 프로젝트 루트에서 찾기
        if not os.path.isabs(path):
            # 현재 파일의 디렉토리에서 프로젝트 루트로 이동
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)  # src/ 상위 디렉토리
            path = os.path.join(project_root, path)
        
        with open(path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            return config_data
    except FileNotFoundError:
        logger.error(f"오류: 설정 파일('{path}')을 찾을 수 없습니다.")
        return None