#!/usr/bin/env python3
"""
사전 임베딩 모델 다운로드 스크립트

폐쇄망 환경에서 사용하기 위해 한국어 임베딩 모델을 미리 다운로드합니다.
환경 변수 WEBSERVICE_DATA_PATH 기반 경로를 사용합니다.
인터넷 연결이 가능한 환경에서 실행한 후, 전체 data/models/ 폴더를 폐쇄망으로 복사하세요.
"""

import os
import sys
from pathlib import Path

# src 모듈을 임포트하기 위해 경로 추가
current_dir = Path(__file__).parent
webservice_root = current_dir.parent
sys.path.append(str(webservice_root))

try:
    from src.paths import get_models_dir, get_default_model_path
except ImportError:
    # 경로 설정 실패시 기본 경로 사용
    print("⚠️ 경로 모듈 임포트 실패, 기본 경로 사용")
    def get_models_dir():
        return Path("./data/models")
    def get_default_model_path():
        return Path("./data/models/ko-sroberta-multitask")

from sentence_transformers import SentenceTransformer

def download_embedding_model():
    """한국어 임베딩 모델을 환경변수 기반 경로에 다운로드"""
    
    model_name = "jhgan/ko-sroberta-multitask"
    local_path = get_default_model_path()
    
    print(f"한국어 임베딩 모델 다운로드 시작: {model_name}")
    print(f"저장 위치: {os.path.abspath(local_path)}")
    
    try:
        # 모델 다운로드 및 로컬 저장
        print("모델 다운로드 중... (시간이 걸릴 수 있습니다)")
        model = SentenceTransformer(model_name)
        
        # 로컬 디렉토리에 저장 (pathlib 사용)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        model.save(str(local_path))
        
        print(f"✅ 모델이 성공적으로 다운로드되었습니다: {local_path}")
        print(f"📁 폴더 크기: {get_folder_size(local_path):.1f} MB")
        
        # 테스트
        print("\n🧪 모델 테스트 중...")
        test_texts = ["안녕하세요", "테스트 문장입니다"]
        embeddings = model.encode(test_texts)
        print(f"✅ 테스트 성공! 임베딩 차원: {embeddings.shape}")
        
        # 폐쇄망 배포 가이드
        print("\n📋 다음 단계:")
        print("1. 전체 data/models/ 폴더를 폐쇄망 환경으로 복사")
        print("2. 폐쇄망 환경에서 WEBSERVICE_DATA_PATH 환경변수 설정:")
        print('   예: WEBSERVICE_DATA_PATH=C:\\deploys\\data\\webservice')
        print("3. 또는 config.json에서 다음과 같이 설정:")
        print('   "local_embedding_model_path": "모델경로"')
        print("4. 앱을 재시작하면 로컬 모델이 사용됩니다")
        
        return True
        
    except Exception as e:
        print(f"❌ 모델 다운로드 실패: {e}")
        print("\n🔍 문제 해결 방법:")
        print("1. 인터넷 연결 확인")
        print("2. 디스크 용량 확인 (약 500MB 필요)")
        print("3. HuggingFace 서버 상태 확인")
        return False

def get_folder_size(folder_path):
    """폴더 크기 계산 (MB)"""
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                total_size += os.path.getsize(filepath)
        return total_size / (1024 * 1024)  # MB로 변환
    except:
        return 0

def main():
    print("=" * 60)
    print("🤖 TestscenarioMaker 임베딩 모델 다운로드 도구")
    print("=" * 60)
    
    # 필요한 패키지 확인
    try:
        import sentence_transformers
        print(f"✅ sentence-transformers 버전: {sentence_transformers.__version__}")
    except ImportError:
        print("❌ sentence-transformers가 설치되지 않았습니다.")
        print("다음 명령어로 설치하세요: pip install sentence-transformers")
        sys.exit(1)
    
    # 모델 다운로드
    success = download_embedding_model()
    
    if success:
        print("\n🎉 모든 작업이 완료되었습니다!")
        sys.exit(0)
    else:
        print("\n💥 작업이 실패했습니다.")
        sys.exit(1)

if __name__ == "__main__":
    main()