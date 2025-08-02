"""
시나리오 생성 API 테스트
"""

import pytest
import json
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
    """시나리오 생성 성공 테스트"""
    
    # Mock LLM 응답 설정
    mock_dependencies['llm_handler'].return_value = """
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
    """
    
    request_data = {
        "repo_path": "/test/repo",
        "use_performance_mode": True
    }
    
    response = client.post("/api/scenario/generate", json=request_data)
    
    assert response.status_code == 200
    data = response.json()
    assert "scenario_description" in data
    assert "test_scenario_name" in data
    assert "test_cases" in data
    assert "metadata" in data

def test_generate_scenario_invalid_repo(client, mock_dependencies):
    """잘못된 저장소 경로로 시나리오 생성 테스트"""
    
    # isdir Mock을 False로 설정
    mock_dependencies['isdir'].return_value = False
    
    request_data = {
        "repo_path": "/invalid/repo",
        "use_performance_mode": True
    }
    
    response = client.post("/api/scenario/generate", json=request_data)
    
    assert response.status_code == 400
    assert "유효한 Git 저장소 경로" in response.json()["detail"]

def test_generate_scenario_config_error(client, mock_dependencies):
    """설정 로드 오류 테스트"""
    
    # config 로드 실패 Mock
    mock_dependencies['load_config'].return_value = None
    
    request_data = {
        "repo_path": "/test/repo",
        "use_performance_mode": True
    }
    
    response = client.post("/api/scenario/generate", json=request_data)
    
    assert response.status_code == 500
    assert "설정 파일을 로드할 수 없습니다" in response.json()["detail"]

def test_generate_scenario_llm_error(client, mock_dependencies):
    """LLM 호출 실패 테스트"""
    
    # LLM 호출 실패 Mock
    mock_dependencies['llm_handler'].return_value = None
    
    request_data = {
        "repo_path": "/test/repo",
        "use_performance_mode": True
    }
    
    response = client.post("/api/scenario/generate", json=request_data)
    
    assert response.status_code == 500
    assert "LLM으로부터 응답을 받지 못했습니다" in response.json()["detail"]

def test_generate_scenario_json_parse_error(client, mock_dependencies):
    """JSON 파싱 오류 테스트"""
    
    # 잘못된 JSON 응답 Mock
    mock_dependencies['llm_handler'].return_value = "Invalid JSON response"
    
    request_data = {
        "repo_path": "/test/repo",
        "use_performance_mode": True
    }
    
    response = client.post("/api/scenario/generate", json=request_data)
    
    assert response.status_code == 500
    assert "JSON 블록을 찾을 수 없습니다" in response.json()["detail"]

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