# src/config_loader.py
import json

def load_config(path="config.json"):
    """설정 파일을 읽어와 파이썬 딕셔너리로 반환합니다."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"오류: 설정 파일('{path}')을 찾을 수 없습니다.")
        return None