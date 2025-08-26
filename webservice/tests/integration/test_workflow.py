"""
전체 워크플로우 통합 테스트
"""
import pytest
import tempfile
import os
import json
from unittest.mock import patch, Mock
from app.core.git_analyzer import get_git_analysis_text
from app.core.llm_handler import call_ollama_llm
from app.core.excel_writer import save_results_to_excel
from app.core.config_loader import load_config


class TestWorkflowIntegration:
    """워크플로우 통합 테스트"""
    
    def test_config_to_git_analysis_workflow(self, temp_dir, config_file):
        """설정 로딩부터 Git 분석까지의 워크플로우 테스트"""
        # 1. 설정 로딩
        config = load_config(config_file)
        assert config is not None
        
        # 2. Git 분석 (Mock 사용)
        with patch('src.git_analyzer.git.Repo') as mock_repo_class:
            # Mock 설정
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo
            
            mock_base_commit = Mock()
            mock_base_commit.hexsha = "abc123"
            mock_head_commit = Mock()
            mock_head_commit.hexsha = "def456"
            
            mock_repo.merge_base.return_value = [mock_base_commit]
            mock_repo.commit.return_value = mock_head_commit
            mock_repo.iter_commits.return_value = []
            mock_base_commit.diff.return_value = []
            
            # Git 분석 실행
            analysis_result = get_git_analysis_text(config["repo_path"])
            
            assert "### 커밋 메시지 목록:" in analysis_result
            assert "### 주요 코드 변경 내용 (diff):" in analysis_result
    
    @patch('src.llm_handler.requests.post')
    def test_llm_to_excel_workflow(self, mock_post, temp_dir, mock_excel_template):
        """LLM 호출부터 Excel 생성까지의 워크플로우 테스트"""
        # 1. LLM 호출 Mock 설정
        mock_response = Mock()
        mock_response.json.return_value = {
            'response': json.dumps({
                "Scenario Description": "통합 테스트 시나리오",
                "Test Scenario Name": "워크플로우 테스트",
                "Test Cases": [
                    {
                        "ID": "WF_001",
                        "절차": "1. 설정 로딩\\n2. Git 분석\\n3. Excel 생성",
                        "사전조건": "테스트 환경 구성",
                        "데이터": "test_data",
                        "예상결과": "성공적인 워크플로우 실행",
                        "종류": "통합 테스트"
                    }
                ]
            })
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # 2. LLM 호출
        llm_result = call_ollama_llm("test prompt", format="json")
        assert llm_result is not None
        
        # 3. JSON 파싱
        result_json = json.loads(llm_result)
        assert "Test Cases" in result_json
        
        # 4. Excel 저장
        outputs_dir = os.path.join(temp_dir, "outputs")
        os.makedirs(outputs_dir, exist_ok=True)
        
        with patch('src.excel_writer.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
            
            excel_path = save_results_to_excel(result_json, mock_excel_template)
            
            assert excel_path is not None
            assert "outputs/20240101_120000" in excel_path
            assert os.path.exists(excel_path)
    
    def test_full_pipeline_with_mocks(self, temp_dir, config_file, mock_excel_template):
        """전체 파이프라인 Mock 테스트"""
        # 1. 설정 로딩
        config = load_config(config_file)
        
        # 2. Git 분석 Mock
        with patch('src.git_analyzer.git.Repo') as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo
            
            mock_base_commit = Mock()
            mock_base_commit.hexsha = "abc123"
            mock_head_commit = Mock()
            mock_head_commit.hexsha = "def456"
            
            mock_repo.merge_base.return_value = [mock_base_commit]
            mock_repo.commit.return_value = mock_head_commit
            
            # 가짜 커밋 생성
            mock_commit = Mock()
            mock_commit.summary = "feature: 통합 테스트 추가"
            mock_repo.iter_commits.return_value = [mock_commit]
            
            # 가짜 diff 생성
            mock_diff = Mock()
            mock_diff.a_path = "test.py"
            mock_diff.diff = b"+def test_function():\n+    return True"
            mock_base_commit.diff.return_value = [mock_diff]
            
            git_analysis = get_git_analysis_text(config["repo_path"])
            
            # 3. LLM 호출 Mock
            with patch('src.llm_handler.requests.post') as mock_post:
                mock_response = Mock()
                mock_response.json.return_value = {
                    'response': json.dumps({
                        "Scenario Description": "통합 테스트용 시나리오",
                        "Test Scenario Name": "전체 파이프라인 테스트",
                        "Test Cases": [
                            {
                                "ID": "PIPE_001",
                                "절차": "전체 파이프라인 실행",
                                "사전조건": "모든 모듈 정상 작동",
                                "데이터": {"input": "test"},
                                "예상결과": "Excel 파일 생성 성공",
                                "종류": "통합"
                            }
                        ]
                    })
                }
                mock_response.raise_for_status.return_value = None
                mock_post.return_value = mock_response
                
                llm_result = call_ollama_llm(f"분석 결과: {git_analysis}", format="json")
                result_json = json.loads(llm_result)
                
                # 4. Excel 생성
                outputs_dir = os.path.join(temp_dir, "outputs")
                os.makedirs(outputs_dir, exist_ok=True)
                
                with patch('src.excel_writer.datetime') as mock_datetime:
                    mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
                    
                    excel_path = save_results_to_excel(result_json, mock_excel_template)
                    
                    # 5. 최종 검증
                    assert excel_path is not None
                    assert os.path.exists(excel_path)
                    
                    # Excel 내용 검증
                    import openpyxl
                    workbook = openpyxl.load_workbook(excel_path)
                    sheet = workbook.active
                    
                    assert sheet['B5'].value == "통합 테스트용 시나리오"
                    assert sheet['F4'].value == "전체 파이프라인 테스트"
                    assert sheet['A11'].value == "PIPE_001"
                    assert "전체 파이프라인 실행" in sheet['B11'].value
    
    def test_error_handling_workflow(self, temp_dir, config_file):
        """오류 처리 워크플로우 테스트"""
        config = load_config(config_file)
        
        # 잘못된 Git 저장소 경로로 테스트
        invalid_repo_path = "/invalid/repo/path"
        git_analysis = get_git_analysis_text(invalid_repo_path)
        
        assert "Git 분석 중 오류 발생:" in git_analysis
        
        # LLM 호출 실패 테스트
        with patch('src.llm_handler.requests.post') as mock_post:
            from requests.exceptions import RequestException
            mock_post.side_effect = RequestException("Network error")
            
            llm_result = call_ollama_llm("test prompt")
            assert llm_result is None
        
        # 잘못된 템플릿 경로로 Excel 생성 테스트
        test_json = {
            "Scenario Description": "오류 테스트",
            "Test Scenario Name": "오류 처리 테스트",
            "Test Cases": []
        }
        
        excel_result = save_results_to_excel(test_json, "/invalid/template.xlsx")
        assert excel_result is None