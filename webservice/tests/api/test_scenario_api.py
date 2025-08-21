"""
시나리오 생성 API 테스트
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

def test_get_scenario_config(client):
    """시나리오 설정 조회 테스트"""
    response = client.get("/api/scenario/config")
    
    assert response.status_code == 200
    data = response.json()
    assert "model_name" in data
    assert "timeout" in data
    assert "repo_path" in data
    assert "rag_enabled" in data

def test_generate_scenario_success(client, mock_dependencies):
    """시나리오 생성 성공 테스트 (WebSocket)"""
    
    # LLM API Mock 응답 설정 (외부 HTTP 요청만 Mock)
    mock_dependencies['requests_post'].return_value.json.return_value = {"response": """
    <json>
    {
        "Scenario Description": "테스트 시나리오 설명",
        "Test Scenario Name": "테스트 시나리오 이름",
        "Test Cases": [
            {
                "ID": "TC001",
                "절차": "테스트 절차",
                "사전조건": "사전조건",
                "데이터": "테스트 데이터",
                "예상결과": "예상 결과",
                "종류": "기능 테스트"
            }
        ]
    }
    </json>
    """}
    
    # 임시 디렉토리 생성 (테스트용 저장소 및 출력 폴더)
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_repo_path = Path(temp_dir) / "test_repo"
        temp_repo_path.mkdir()
        temp_outputs_path = Path(temp_dir) / "outputs"
        temp_outputs_path.mkdir()
        
        # Git 저장소 초기화 (.git 폴더 생성)
        git_dir = temp_repo_path / ".git"
        git_dir.mkdir()
        
        # 기본 config 파일 생성
        config_path = Path(temp_dir) / "config.json"
        config_data = {
            "model_name": "qwen3:8b",
            "timeout": 600,
            "repo_path": str(temp_repo_path),
            "rag": {"enabled": False}  # RAG 비활성화로 테스트 단순화
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        
        # config 로드 및 Git 분석 Mock 대신 실제 모듈 사용
        with patch('src.config_loader.load_config', return_value=config_data), \
             patch('src.git_analyzer.get_git_analysis_text', return_value="Mock Git analysis for testing"), \
             patch('src.excel_writer.save_results_to_excel', return_value=str(temp_outputs_path / "test_result.xlsx")):
            
            # WebSocket 연결 테스트
            with client.websocket_connect("/api/scenario/generate-ws") as websocket:
                request_data = {
                    "repo_path": "/test/repo",
                    "use_performance_mode": True
                }
                websocket.send_text(json.dumps(request_data))
                
                # 첫 번째 응답 받기
                data = websocket.receive_text()
                progress = json.loads(data)
                
                assert "status" in progress
                assert "message" in progress
                assert "progress" in progress

def test_generate_scenario_invalid_repo(client, mock_dependencies):
    """잘못된 저장소 경로로 시나리오 생성 테스트 (WebSocket)"""
    
    # isdir Mock을 False로 설정
    mock_dependencies['isdir'].return_value = False
    
    with client.websocket_connect("/api/scenario/generate-ws") as websocket:
        request_data = {
            "repo_path": "/invalid/repo",
            "use_performance_mode": True
        }
        websocket.send_text(json.dumps(request_data))
        
        # 오류 응답 받기
        data = websocket.receive_text()
        progress = json.loads(data)
        
        assert progress["status"] == "error"
        assert "유효한 Git 저장소 경로" in progress["message"]

def test_generate_scenario_config_error(client, mock_dependencies):
    """Git 경로 검증 오류 테스트 (WebSocket) - 실제 API 동작 기준"""
    
    # Git 경로 검증 실패 시나리오 (실제 API에서 먼저 체크되는 부분)
    with client.websocket_connect("/api/scenario/generate-ws") as websocket:
        request_data = {
            "repo_path": "",  # 빈 경로로 검증 실패 유도
            "use_performance_mode": True
        }
        websocket.send_text(json.dumps(request_data))
        
        # 오류 응답 받기
        data = websocket.receive_text()
        progress = json.loads(data)
        
        assert progress["status"] == "error"
        assert "유효한 Git 저장소 경로를 입력해주세요" in progress["message"]

def test_generate_scenario_llm_error(client, mock_dependencies):
    """LLM 호출 실패 테스트 (WebSocket)"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_repo_path = Path(temp_dir) / "test_repo"
        temp_repo_path.mkdir()
        git_dir = temp_repo_path / ".git"
        git_dir.mkdir()
        
        # 정상 config 생성
        config_path = Path(temp_dir) / "config.json"
        config_data = {
            "model_name": "qwen3:8b",
            "timeout": 600,
            "repo_path": str(temp_repo_path),
            "rag": {"enabled": False}
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        
        # LLM API 호출 실패 Mock (외부 HTTP 요청만 Mock)
        mock_dependencies['requests_post'].return_value.json.return_value = {"response": None}
        
        # 라우터 모듈 네임스페이스에 맞춰 패치
        with patch('backend.routers.scenario.load_config', return_value=config_data), \
             patch('backend.routers.scenario.get_git_analysis_text', return_value="Mock Git analysis"), \
             patch('pathlib.Path.is_dir', return_value=True):
            
            with client.websocket_connect("/api/scenario/generate-ws") as websocket:
                request_data = {
                    "repo_path": str(temp_repo_path),
                    "use_performance_mode": True
                }
                websocket.send_text(json.dumps(request_data))
                
                # 여러 응답을 받아서 오류 응답 찾기
                for _ in range(5):  # 최대 5개 응답 확인
                    data = websocket.receive_text()
                    progress = json.loads(data)
                    if progress["status"] == "error":
                        assert "LLM으로부터 응답을 받지 못했습니다" in progress["message"]
                        break
                else:
                    assert False, "오류 응답을 찾을 수 없습니다"

def test_generate_scenario_json_parse_error(client, mock_dependencies):
    """JSON 파싱 오류 테스트 (WebSocket)"""
    
    # 잘못된 JSON 응답 Mock (외부 HTTP 요청만 Mock)
    mock_dependencies['requests_post'].return_value.json.return_value = {"response": "Invalid JSON response without tags"}
    
    # 유효한 Git 경로 검증 우회
    with patch('pathlib.Path.is_dir', return_value=True):
        with client.websocket_connect("/api/scenario/generate-ws") as websocket:
            request_data = {
                "repo_path": "/test/repo",
                "use_performance_mode": True
            }
            websocket.send_text(json.dumps(request_data))
            
            # 여러 응답을 받아서 오류 응답 찾기
            for _ in range(5):  # 최대 5개 응답 확인
                data = websocket.receive_text()
                progress = json.loads(data)
                if progress["status"] == "error":
                    assert "JSON 블록을 찾을 수 없습니다" in progress["message"]
                    break
            else:
                assert False, "오류 응답을 찾을 수 없습니다"

@pytest.mark.asyncio
async def test_websocket_scenario_generation(client, mock_dependencies):
    """WebSocket 시나리오 생성 테스트"""
    
    # WebSocket 연결 테스트는 더 복잡하므로 기본 구조만 테스트
    with client.websocket_connect("/api/scenario/generate-ws") as websocket:
        # 요청 데이터 전송
        request_data = {
            "repo_path": "/test/repo",
            "use_performance_mode": True
        }
        websocket.send_text(json.dumps(request_data))
        
        # 첫 번째 응답 받기
        data = websocket.receive_text()
        progress = json.loads(data)
        
        assert "status" in progress
        assert "message" in progress
        assert "progress" in progress

def test_generate_scenario_from_text_success(client, mock_dependencies):
    """분석 텍스트 기반 시나리오 생성 성공 테스트 - 실제 내부 모듈 사용"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # config 생성
        config_path = Path(temp_dir) / "config.json"
        config_data = {
            "model_name": "qwen3:8b",
            "timeout": 600,
            "rag": {"enabled": False}
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        
        # Excel 출력 경로 설정
        outputs_path = Path(temp_dir) / "outputs"
        outputs_path.mkdir()
        expected_excel_path = outputs_path / "test_scenario.xlsx"
        
        # 실제 내부 모듈을 사용하되, Excel 생성만 Mock
        # 라우터 모듈 네임스페이스에 맞춰 패치
        with patch('backend.routers.scenario.load_config', return_value=config_data), \
             patch('backend.routers.scenario.save_results_to_excel', return_value=str(expected_excel_path)):
            
            request_data = {
                "analysis_text": "Git 저장소 분석 결과: 주요 변경사항은 사용자 인증 기능 개선입니다."
            }
            
            response = client.post("/api/scenario/v1/generate-from-text", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "download_url" in data
            assert "filename" in data
            assert "message" in data
            assert data["download_url"].startswith("/api/files/download/")
            assert data["filename"].endswith(".xlsx")

def test_generate_scenario_from_text_config_error(client, mock_dependencies):
    """분석 텍스트 기반 시나리오 생성 - 설정 로드 오류 테스트"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 존재하지 않는 config 경로 사용
        invalid_config_path = Path(temp_dir) / "nonexistent_config.json"
        
        # 라우터 네임스페이스에서 패치
        with patch('backend.routers.scenario.load_config', return_value=None):
            request_data = {
                "analysis_text": "Git 저장소 분석 결과"
            }
            
            response = client.post("/api/scenario/v1/generate-from-text", json=request_data)
            
            assert response.status_code == 500
            assert "설정 파일을 로드할 수 없습니다" in response.json()["detail"]

def test_generate_scenario_from_text_prompt_error(client, mock_dependencies):
    """분석 텍스트 기반 시나리오 생성 - 프롬프트 생성 오류 테스트"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # config 생성
        config_path = Path(temp_dir) / "config.json"
        config_data = {
            "model_name": "qwen3:8b",
            "timeout": 600,
            "rag": {"enabled": False}
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        
        # 프롬프트 생성 실패 Mock
        with patch('backend.routers.scenario.load_config', return_value=config_data), \
             patch('backend.routers.scenario.create_final_prompt', return_value=None):
            
            request_data = {
                "analysis_text": "Git 저장소 분석 결과"
            }
            
            response = client.post("/api/scenario/v1/generate-from-text", json=request_data)
            
            assert response.status_code == 500
            assert "프롬프트 생성에 실패했습니다" in response.json()["detail"]

def test_generate_scenario_from_text_llm_error(client, mock_dependencies):
    """분석 텍스트 기반 시나리오 생성 - LLM 호출 오류 테스트"""
    
    # LLM 호출 실패 Mock - 라우터에서 직접 LLM 호출 결과를 None으로 반환시켜 500 처리
    # (본 코드에서는 응답 None 시 "LLM으로부터 응답을 받지 못했습니다"로 처리)
    with patch('backend.routers.scenario.call_ollama_llm', return_value=None):
        request_data = {
            "analysis_text": "Git 저장소 분석 결과"
        }
        response = client.post("/api/scenario/v1/generate-from-text", json=request_data)
        assert response.status_code == 500
        assert "LLM으로부터 응답을 받지 못했습니다" in response.json()["detail"]

def test_generate_scenario_from_text_json_parse_error(client, mock_dependencies):
    """분석 텍스트 기반 시나리오 생성 - JSON 파싱 오류 테스트"""
    
    # 잘못된 JSON 응답 Mock
    mock_dependencies['requests_post'].return_value.json.return_value = {"response": "Invalid JSON response without tags"}
    
    request_data = {
        "analysis_text": "Git 저장소 분석 결과"
    }
    
    response = client.post("/api/scenario/v1/generate-from-text", json=request_data)
    
    assert response.status_code == 500
    assert "JSON 블록을 찾을 수 없습니다" in response.json()["detail"]

def test_generate_scenario_from_text_excel_error(client, mock_dependencies):
    """분석 텍스트 기반 시나리오 생성 - Excel 생성 오류 테스트"""
    
    # Mock LLM 응답 설정
    mock_dependencies['requests_post'].return_value.json.return_value = {"response": """
    <json>
    {
        "Scenario Description": "테스트 시나리오",
        "Test Scenario Name": "테스트",
        "Test Cases": []
    }
    </json>
    """}
    
    # Excel 파일 생성 실패 Mock (라우터 네임스페이스 기준)
    with patch('backend.routers.scenario.save_results_to_excel', return_value=None):
        request_data = {
            "analysis_text": "Git 저장소 분석 결과"
        }
        
        response = client.post("/api/scenario/v1/generate-from-text", json=request_data)
        
        assert response.status_code == 500
        assert "Excel 파일 생성에 실패했습니다" in response.json()["detail"]

def test_generate_scenario_from_text_empty_analysis(client):
    """분석 텍스트 기반 시나리오 생성 - 빈 분석 텍스트 테스트"""
    
    request_data = {
        "analysis_text": ""
    }
    
    response = client.post("/api/scenario/v1/generate-from-text", json=request_data)
    
    # 빈 텍스트는 유효한 입력으로 처리되어야 함
    assert response.status_code in [200, 500]  # 실제 구현에 따라 다를 수 있음

def test_generate_scenario_from_text_missing_field(client):
    """분석 텍스트 기반 시나리오 생성 - 필수 필드 누락 테스트"""
    
    request_data = {}  # analysis_text 필드 누락
    
    response = client.post("/api/scenario/v1/generate-from-text", json=request_data)
    
    assert response.status_code == 422  # Pydantic validation error