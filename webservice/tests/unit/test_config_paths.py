#!/usr/bin/env python3
"""
설정 파일 경로 관리 시스템 테스트 스크립트

환경변수 기반 설정 로딩과 경로 해결 로직을 테스트합니다.
"""
import os
import sys
import tempfile
import json
from pathlib import Path

# src 모듈 import를 위한 경로 추가
sys.path.append(str(Path(__file__).parent / "src"))

from app.core.config_loader import load_config, verify_environment, _is_development_environment
from app.core.paths import get_data_root, verify_data_directories

def test_environment_detection():
    """Environment detection test"""
    print("=== Environment Detection Test ===")
    is_dev = _is_development_environment()
    print(f"Is Development: {is_dev}")
    print(f"site-packages path: {'site-packages' in str(Path(__file__).resolve())}")
    print()

def test_paths():
    """Path system test"""
    print("=== Path System Test ===")
    
    env_path = os.getenv('WEBSERVICE_DATA_PATH')
    print(f"WEBSERVICE_DATA_PATH env var: {env_path}")
    
    data_root = get_data_root()
    print(f"Data root path: {data_root}")
    print(f"Data root exists: {data_root.exists()}")
    
    directories_ok = verify_data_directories()
    print(f"Directories writable: {directories_ok}")
    print()

def test_config_loading():
    """Config loading test"""
    print("=== Config Loading Test ===")
    
    try:
        config = load_config()
        if config:
            print("[OK] Config loading success")
            print(f"RAG enabled: {config.get('rag', {}).get('enabled', False)}")
        else:
            print("[ERROR] Config loading failed")
    except Exception as e:
        print(f"[ERROR] Config loading error: {e}")
    print()

def test_environment_verification():
    """Environment verification test"""
    print("=== Environment Verification Test ===")
    
    verification = verify_environment()
    print(f"Environment type: {verification['environment_type']}")
    print(f"Env var set: {verification['webservice_data_path_set']}")
    print(f"Env var value: {verification['webservice_data_path_value']}")
    print(f"Config path resolved: {verification['config_path_resolved']}")
    print(f"Resolved config path: {verification.get('resolved_config_path')}")
    print(f"Directories writable: {verification['directories_writable']}")
    
    if verification['issues']:
        print("[WARNING] Found issues:")
        for issue in verification['issues']:
            print(f"  - {issue}")
    else:
        print("[OK] All verifications passed")
    print()

def test_with_temp_environment():
    """Test with temporary environment"""
    print("=== Temporary Environment Test ===")
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create temporary config file
        config_data = {
            "model_name": "test-model",
            "rag": {
                "enabled": True,
                "embedding_model": "test-embedding"
            }
        }
        
        config_file = temp_path / "config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        
        # Set environment variable
        original_env = os.environ.get('WEBSERVICE_DATA_PATH')
        os.environ['WEBSERVICE_DATA_PATH'] = str(temp_path)
        
        try:
            print(f"Temp env var set: {temp_path}")
            
            # Test config loading
            config = load_config()
            if config and config.get('model_name') == 'test-model':
                print("[OK] Temp env config loading success")
            else:
                print("[ERROR] Temp env config loading failed")
                
        finally:
            # Restore environment variable
            if original_env:
                os.environ['WEBSERVICE_DATA_PATH'] = original_env
            else:
                os.environ.pop('WEBSERVICE_DATA_PATH', None)
    print()

def main():
    """메인 테스트 실행"""
    print("Config Path Management System Test")
    print("=" * 50)
    
    test_environment_detection()
    test_paths()
    test_config_loading()
    test_environment_verification()
    test_with_temp_environment()
    
    print("Test Complete")

if __name__ == "__main__":
    main()