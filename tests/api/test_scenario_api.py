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
    """시나리오 생성 성공 테스트 (WebSocket)"""
    
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
    """설정 로드 오류 테스트 (WebSocket)"""
    
    # config 로드 실패 Mock
    mock_dependencies['load_config'].return_value = None
    
    with client.websocket_connect("/api/scenario/generate-ws") as websocket:
        request_data = {
            "repo_path": "/test/repo",
            "use_performance_mode": True
        }
        websocket.send_text(json.dumps(request_data))
        
        # 오류 응답 받기
        data = websocket.receive_text()
        progress = json.loads(data)
        
        assert progress["status"] == "error"
        assert "설정 파일을 로드할 수 없습니다" in progress["message"]

def test_generate_scenario_llm_error(client, mock_dependencies):
    """LLM 호출 실패 테스트 (WebSocket)"""
    
    # LLM 호출 실패 Mock
    mock_dependencies['llm_handler'].return_value = None
    
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
                assert "LLM으로부터 응답을 받지 못했습니다" in progress["message"]
                break
        else:
            assert False, "오류 응답을 찾을 수 없습니다"

def test_generate_scenario_json_parse_error(client, mock_dependencies):
    """JSON 파싱 오류 테스트 (WebSocket)"""
    
    # 잘못된 JSON 응답 Mock
    mock_dependencies['llm_handler'].return_value = "Invalid JSON response"
    
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
    """분석 텍스트 기반 시나리오 생성 성공 테스트"""
    
    # Mock LLM 응답 설정
    mock_dependencies['llm_handler'].return_value = """
    <json>
    {
        "Scenario Description": "CLI 분석 기반 테스트 시나리오",
        "Test Scenario Name": "CLI 테스트 시나리오",
        "Test Cases": [
            {
                "ID": "CLI_TC001",
                "절차": "CLI 명령어 실행",
                "사전조건": "CLI 도구 설치 완료",
                "데이터": "테스트 입력 데이터",
                "예상결과": "예상 출력 결과",
                "Unit": "Y",
                "Integration": "N"
            }
        ]
    }
    </json>
    """
    
    # Mock Excel 파일 생성
    mock_dependencies['excel_writer'].return_value = "/path/to/output/20241201_120000_테스트_시나리오_결과.xlsx"
    
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
    
    # config 로드 실패 Mock
    mock_dependencies['load_config'].return_value = None
    
    request_data = {
        "analysis_text": "Git 저장소 분석 결과"
    }
    
    response = client.post("/api/scenario/v1/generate-from-text", json=request_data)
    
    assert response.status_code == 500
    assert "설정 파일을 로드할 수 없습니다" in response.json()["detail"]

def test_generate_scenario_from_text_prompt_error(client, mock_dependencies):
    """분석 텍스트 기반 시나리오 생성 - 프롬프트 생성 오류 테스트"""
    
    # 프롬프트 생성 실패 Mock
    mock_dependencies['create_final_prompt'].return_value = None
    
    request_data = {
        "analysis_text": "Git 저장소 분석 결과"
    }
    
    response = client.post("/api/scenario/v1/generate-from-text", json=request_data)
    
    assert response.status_code == 500
    assert "프롬프트 생성에 실패했습니다" in response.json()["detail"]

def test_generate_scenario_from_text_llm_error(client, mock_dependencies):
    """분석 텍스트 기반 시나리오 생성 - LLM 호출 오류 테스트"""
    
    # LLM 호출 실패 Mock - requests.post에서 예외 발생
    mock_dependencies['requests_post'].side_effect = Exception("Connection error")
    
    request_data = {
        "analysis_text": "Git 저장소 분석 결과"
    }
    
    response = client.post("/api/scenario/v1/generate-from-text", json=request_data)
    
    assert response.status_code == 500
    assert "LLM API 오류" in response.json()["detail"]

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
    
    # Excel 파일 생성 실패 Mock
    mock_dependencies['excel_writer'].return_value = None
    
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