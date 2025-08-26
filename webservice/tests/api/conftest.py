"""
FastAPI 테스트를 위한 공통 설정
"""

import pytest
import os
import sys
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from pathlib import Path

# 백엔드 모듈 import를 위한 경로 추가 (Windows CI 호환성 강화)
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

# PYTHONPATH 환경변수 설정 (Jenkins CI 환경 호환)
os.environ['PYTHONPATH'] = str(project_root) + os.pathsep + os.environ.get('PYTHONPATH', '')

from backend.main import app

@pytest.fixture
def client():
    """FastAPI 테스트 클라이언트"""
    return TestClient(app)

@pytest.fixture(scope="session", autouse=True)
def ensure_config_json():
    """테스트 세션 동안 webservice/config.json이 없으면 생성하고 종료 시 정리.

    Jenkins/Windows 환경에서 기본 config.json 부재로 인한 실패를 방지한다.
    실제 파일이 존재하면 유지한다.
    """
    webservice_root = Path(__file__).resolve().parents[1]
    config_path = webservice_root / "config.json"
    created = False

    if not config_path.exists():
        example_path = webservice_root / "config.example.json"
        try:
            if example_path.exists():
                contents = example_path.read_text(encoding="utf-8")
            else:
                minimal = {
                    "model_name": "qwen3:8b",
                    "timeout": 600,
                    "repo_path": "",
                    "rag": {"enabled": False}
                }
                contents = json.dumps(minimal, ensure_ascii=False, indent=2)
            config_path.write_text(contents, encoding="utf-8")
            created = True
        except Exception:
            pass

    yield

    if created:
        try:
            config_path.unlink()
        except Exception:
            pass

@pytest.fixture
def mock_config():
    """Mock 설정 데이터"""
    return {
        "model_name": "qwen3:8b",
        "timeout": 600,
        "repo_path": "/test/repo",
        "rag": {
            "enabled": True,
            "embedding_model": "jhgan/ko-sroberta-multitask"
        }
    }

@pytest.fixture
def mock_git_analysis():
    """Mock Git 분석 결과"""
    return """
    Git Analysis Result:
    - Modified files: test.py, main.py
    - Commit messages: Add new feature, Fix bug
    - Code changes: Added function foo(), Updated bar()
    """

@pytest.fixture
def mock_llm_response():
    """Mock LLM 응답"""
    return """
    <thinking>
    This is a test scenario generation...
    </thinking>
    
    <json>
    {
        "Scenario Description": "테스트 시나리오 설명",
        "Test Scenario Name": "테스트 시나리오 이름",
        "Test Cases": [
            {
                "ID": "TC001",
                "절차": "테스트 절차 1",
                "사전조건": "사전조건 1",
                "데이터": "테스트 데이터 1",
                "예상결과": "예상 결과 1",
                "종류": "기능 테스트"
            }
        ]
    }
    </json>
    """

@pytest.fixture
def mock_scenario_result():
    """Mock 시나리오 결과"""
    return {
        "Scenario Description": "테스트 시나리오 설명",
        "Test Scenario Name": "테스트 시나리오 이름",
        "Test Cases": [
            {
                "ID": "TC001",
                "절차": "테스트 절차 1",
                "사전조건": "사전조건 1",
                "데이터": "테스트 데이터 1",
                "예상결과": "예상 결과 1",
                "종류": "기능 테스트"
            }
        ]
    }

@pytest.fixture(autouse=True)
def mock_dependencies():
    """필수 외부 의존성만 Mock (내부 모듈은 실제 임포트)"""
    
    with patch('requests.post') as mock_requests_post, \
         patch('openpyxl.load_workbook') as mock_load_workbook, \
         patch('shutil.copy') as mock_shutil_copy, \
         patch('os.path.isdir') as mock_isdir, \
         patch('pathlib.Path.exists') as mock_path_exists, \
         patch('pathlib.Path.mkdir') as mock_path_mkdir, \
         patch('src.git_analyzer.get_git_analysis_text') as mock_get_git_analysis_text:
        
        # 파일 시스템 Mock (CI 환경 호환)
        mock_isdir.return_value = True
        mock_path_exists.return_value = True
        mock_path_mkdir.return_value = None
        mock_shutil_copy.return_value = None
        
        # Excel Workbook Mock (openpyxl 외부 의존성)
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_workbook.active = mock_sheet
        mock_load_workbook.return_value = mock_workbook
        
        # Git Analyzer Mock (내부 모듈이지만 파일 시스템 의존성으로 인해 Mock 필요)
        mock_get_git_analysis_text.return_value = """### 커밋 메시지 목록:
- feat: Mock 기능 추가
- fix: Mock 버그 수정

### 주요 코드 변경 내용 (diff):
--- 파일: test.py ---
+def mock_function():
+    return "Mock implementation"
"""

        # Ollama API Mock (외부 HTTP 호출)
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": """
        <json>
        {
            "Scenario Description": "Mock scenario from external API",
            "Test Scenario Name": "Mock test name",
            "Test Cases": [
                {
                    "ID": "TC001",
                    "절차": "Mock 테스트 절차",
                    "사전조건": "Mock 사전조건",
                    "데이터": "Mock 테스트 데이터",
                    "예상결과": "Mock 예상 결과",
                    "종류": "기능 테스트"
                }
            ]
        }
        </json>
        """}
        mock_response.raise_for_status.return_value = None
        mock_requests_post.return_value = mock_response
        
        yield {
            'requests_post': mock_requests_post,
            'load_workbook': mock_load_workbook,
            'shutil_copy': mock_shutil_copy,
            'isdir': mock_isdir,
            'path_exists': mock_path_exists,
            'path_mkdir': mock_path_mkdir,
            'get_git_analysis_text': mock_get_git_analysis_text
        }