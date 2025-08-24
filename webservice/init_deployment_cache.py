"""배포 환경용 초기 캐시 파일 생성 스크립트"""
import json
import os
from datetime import datetime
from pathlib import Path

def create_initial_cache():
    """배포 환경에 빈 캐시 파일을 생성"""
    
    # 환경변수에서 데이터 경로 가져오기
    webservice_data_path = os.environ.get('WEBSERVICE_DATA_PATH', 'C:/deploys/data/webservice')
    cache_file_path = Path(webservice_data_path) / "indexed_files_cache.json"
    
    print(f"캐시 파일 생성 경로: {cache_file_path}")
    
    # 디렉토리 생성
    cache_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 초기 캐시 데이터
    initial_cache = {
        "cache_version": "1.0",
        "last_updated": datetime.now().isoformat(),
        "indexed_files": {}
    }
    
    # 캐시 파일 생성
    with open(cache_file_path, 'w', encoding='utf-8') as f:
        json.dump(initial_cache, f, indent=2, ensure_ascii=False)
    
    print(f"초기 캐시 파일 생성 완료: {cache_file_path}")
    print("이 파일은 배포 시에 첫 실행에서만 사용되고 이후에는 자동으로 업데이트됩니다.")

if __name__ == "__main__":
    create_initial_cache()