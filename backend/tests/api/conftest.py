"""
FastAPI 테스트를 위한 공통 설정
"""

import pytest
import os
import sys
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# 백엔드 모듈 import를 위한 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from backend.main import app

@pytest.fixture
def client():
    """FastAPI 테스트 클라이언트"""
    return TestClient(app)

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
    """모든 외부 의존성을 자동으로 Mock"""
    
    with patch('src.config_loader.load_config') as mock_load_config, \
         patch('src.git_analyzer.get_git_analysis_text') as mock_git_analyzer, \
         patch('src.llm_handler.call_ollama_llm') as mock_llm_handler, \
         patch('src.excel_writer.save_results_to_excel') as mock_excel_writer, \
         patch('src.excel_writer._copy_template') as mock_copy_template, \
         patch('src.excel_writer._generate_filename') as mock_generate_filename, \
         patch('src.prompt_loader.create_final_prompt') as mock_create_prompt, \
         patch('src.prompt_loader.add_git_analysis_to_rag') as mock_add_rag, \
         patch('src.prompt_loader.get_rag_info') as mock_get_rag_info, \
         patch('src.prompt_loader.get_rag_manager') as mock_get_rag_manager, \
         patch('src.prompt_loader.get_feedback_manager') as mock_get_feedback_manager, \
         patch('src.prompt_loader.get_prompt_enhancer') as mock_get_prompt_enhancer, \
         patch('src.feedback_manager.FeedbackManager') as mock_feedback_manager, \
         patch('src.vector_db.rag_manager.RAGManager') as mock_rag_manager_class, \
         patch('os.path.isdir') as mock_isdir, \
         patch('pathlib.Path.exists') as mock_path_exists, \
         patch('pathlib.Path.mkdir') as mock_path_mkdir, \
         patch('requests.post') as mock_requests_post, \
         patch('openpyxl.load_workbook') as mock_load_workbook, \
         patch('shutil.copy') as mock_shutil_copy:
        
        # 기본 Mock 설정
        mock_load_config.return_value = {
            "model_name": "qwen3:8b",
            "timeout": 600,
            "repo_path": "/test/repo",
            "rag": {"enabled": True}
        }
        
        mock_git_analyzer.return_value = "Mock git analysis"
        mock_llm_handler.return_value = """
        <json>
        {
            "Scenario Description": "Mock scenario",
            "Test Scenario Name": "Mock test name",
            "Test Cases": []
        }
        </json>
        """
        mock_excel_writer.return_value = "/test/output/20241201_120000_테스트_시나리오_결과.xlsx"
        mock_create_prompt.return_value = "Mock prompt for testing"
        mock_add_rag.return_value = 5
        mock_get_rag_info.return_value = {"chroma_info": {"count": 10}}
        mock_isdir.return_value = True
        mock_path_exists.return_value = True
        mock_path_mkdir.return_value = None
        mock_copy_template.return_value = True
        mock_generate_filename.return_value = "/test/output/20241201_120000_테스트_시나리오_결과.xlsx"
        mock_shutil_copy.return_value = None
        
        # Excel Workbook Mock
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_workbook.active = mock_sheet
        mock_load_workbook.return_value = mock_workbook
        
        # Requests Mock
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": """
        <json>
        {
            "Scenario Description": "Mock scenario",
            "Test Scenario Name": "Mock test name",
            "Test Cases": []
        }
        </json>
        """}
        mock_response.raise_for_status.return_value = None
        mock_requests_post.return_value = mock_response
        
        # RAG Manager Mock
        mock_rag_manager_instance = MagicMock()
        mock_rag_manager_class.return_value = mock_rag_manager_instance
        mock_get_rag_manager.return_value = mock_rag_manager_instance
        
        # Feedback Manager Mock
        mock_feedback_manager_instance = MagicMock()
        mock_feedback_manager.return_value = mock_feedback_manager_instance
        mock_get_feedback_manager.return_value = mock_feedback_manager_instance
        mock_feedback_manager_instance.get_feedback_stats.return_value = {
            "total_feedback": 0,
            "category_distribution": {},
            "average_scores": {}
        }
        
        # Prompt Enhancer Mock
        mock_prompt_enhancer_instance = MagicMock()
        mock_get_prompt_enhancer.return_value = mock_prompt_enhancer_instance
        
        yield {
            'load_config': mock_load_config,
            'git_analyzer': mock_git_analyzer,
            'llm_handler': mock_llm_handler,
            'excel_writer': mock_excel_writer,
            'create_final_prompt': mock_create_prompt,
            'add_rag': mock_add_rag,
            'get_rag_info': mock_get_rag_info,
            'get_rag_manager': mock_get_rag_manager,
            'get_feedback_manager': mock_get_feedback_manager,
            'get_prompt_enhancer': mock_get_prompt_enhancer,
            'feedback_manager': mock_feedback_manager,
            'rag_manager_class': mock_rag_manager_class,
            'isdir': mock_isdir,
            'path_exists': mock_path_exists,
            'path_mkdir': mock_path_mkdir,
            'requests_post': mock_requests_post,
            'load_workbook': mock_load_workbook,
            'shutil_copy': mock_shutil_copy,
            'copy_template': mock_copy_template,
            'generate_filename': mock_generate_filename
        }