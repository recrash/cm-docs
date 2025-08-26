"""
config_loader.py 모듈 테스트
"""
import pytest
import json
import os
from app.core.config_loader import load_config


class TestConfigLoader:
    """설정 파일 로더 테스트"""
    
    def test_load_valid_config(self, config_file, sample_config):
        """유효한 설정 파일 로딩 테스트"""
        result = load_config(config_file)
        
        assert result is not None
        assert result == sample_config
        assert result["repo_path"] == "/path/to/test/repo"
        assert result["model_name"] == "qwen3:8b"
        assert result["timeout"] == 600
    
    def test_load_nonexistent_config(self, temp_dir, capsys):
        """존재하지 않는 설정 파일 테스트"""
        nonexistent_path = os.path.join(temp_dir, "nonexistent.json")
        result = load_config(nonexistent_path)
        
        assert result is None
        captured = capsys.readouterr()
        assert "설정 파일" in captured.out
        assert "찾을 수 없습니다" in captured.out
    
    def test_load_invalid_json(self, temp_dir, capsys):
        """잘못된 JSON 형식 파일 테스트"""
        invalid_json_path = os.path.join(temp_dir, "invalid.json")
        with open(invalid_json_path, 'w') as f:
            f.write("invalid json content {")
        
        with pytest.raises(json.JSONDecodeError):
            load_config(invalid_json_path)
    
    def test_load_empty_config(self, temp_dir):
        """빈 설정 파일 테스트"""
        empty_config_path = os.path.join(temp_dir, "empty.json")
        with open(empty_config_path, 'w') as f:
            json.dump({}, f)
        
        result = load_config(empty_config_path)
        
        assert result == {}
    
    def test_load_config_with_unicode(self, temp_dir):
        """유니코드 포함 설정 파일 테스트"""
        unicode_config = {
            "repo_path": "/한글/경로",
            "description": "테스트 설명",
            "한글키": "한글값"
        }
        
        unicode_config_path = os.path.join(temp_dir, "unicode.json")
        with open(unicode_config_path, 'w', encoding='utf-8') as f:
            json.dump(unicode_config, f, ensure_ascii=False)
        
        result = load_config(unicode_config_path)
        
        assert result == unicode_config
        assert result["repo_path"] == "/한글/경로"
        assert result["한글키"] == "한글값"