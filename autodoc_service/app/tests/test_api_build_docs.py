"""
문서 생성 API 통합 테스트
Task 1.2의 DoD 검증을 위한 테스트
"""
import pytest
import json
from pathlib import Path
from datetime import datetime
from fastapi.testclient import TestClient
from app.main import app
from app.services.paths import get_documents_dir
from app.models import ChangeRequest

# 테스트 클라이언트 생성
client = TestClient(app)

# fixtures 디렉토리 경로
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def get_sample_change_request_data():
    """테스트용 ChangeRequest 데이터 생성"""
    return {
        "change_id": f"CM-{datetime.now().strftime('%Y%m%d')}-TEST",
        "system": "테스트시스템",
        "title": "통합 테스트를 위한 변경관리 요청",
        "system_short": "TEST",
        "requester": "테스터",
        "request_dept": "QA팀",
        "customer": "테스트고객사",
        "writer_short": "테스터",
        "doc_no": "DOC-TEST-001",
        "work_datetime": "12/31 18:00",
        "deploy_datetime": "01/01 09:00",
        "biz_test_date": "2024-12-30",
        "created_date": datetime.now().strftime("%m/%d"),
        "details": {
            "summary": "테스트 요약",
            "risk": "낮음",
            "plan": "테스트 계획"
        },
        "impact_targets": "테스트 대상자",
        "worker_deployer": "작업자-배포자",
        "deploy_type": "정기배포",
        "program": "Appl.",
        "deployer": "배포자",
        "has_cm_doc": "O",
        "author": "작성자"
    }


def test_full_workflow_with_parse_html():
    """전체 워크플로우 테스트: HTML 파싱 → 문서 생성"""
    print("\n=== Task 1.2 통합 테스트 시작 ===")
    
    # Step 1: parse-html-only 호출하여 메타데이터 획득
    print("\n1. HTML 파싱으로 메타데이터 획득...")
    
    # fixtures에서 표준 HTML 파일 사용
    sample_html_path = FIXTURES_DIR / "sample_itsupp.html"
    assert sample_html_path.exists(), "테스트를 위해 fixtures/sample_itsupp.html 파일이 필요합니다."
    
    with open(sample_html_path, 'rb') as f:
        files = {"file": (sample_html_path.name, f, "text/html")}
        response = client.post("/api/autodoc/parse-html-only", files=files)
    
    assert response.status_code == 200
    parsed_response = response.json()
    assert parsed_response["success"] == True
    
    # 파싱된 데이터를 ChangeRequest 형식으로 변환
    parsed_data = parsed_response["data"]
    change_request_data = get_sample_change_request_data()
    
    # 파싱된 데이터로 업데이트
    if parsed_data:
        change_request_data.update({
            "change_id": parsed_data.get("변경관리번호", change_request_data["change_id"]),
            "system": parsed_data.get("시스템", change_request_data["system"]),
            "title": parsed_data.get("제목", change_request_data["title"]),
            "requester": parsed_data.get("요청자", change_request_data["requester"]),
            "request_dept": parsed_data.get("요청부서", change_request_data["request_dept"]),
            "customer": parsed_data.get("고객사", change_request_data["customer"])
        })
    
    print(f"   ✓ 메타데이터 획득 완료: {change_request_data['change_id']}")
    
    # Step 2: build-cm-word API 호출
    print("\n2. Word 문서 생성 API 호출...")
    response = client.post(
        "/api/autodoc/build-cm-word",
        json=change_request_data
    )
    
    assert response.status_code == 200
    word_response = response.json()
    assert word_response["ok"] == True
    assert word_response["filename"] is not None
    word_filename = word_response["filename"]
    print(f"   ✓ Word 문서 생성 완료: {word_filename}")
    
    # Step 3: build-cm-list API 호출
    print("\n3. 목록 Excel 생성 API 호출...")
    response = client.post(
        "/api/autodoc/build-cm-list",
        json=[change_request_data]  # 배열로 전송
    )
    
    assert response.status_code == 200
    list_response = response.json()
    assert list_response["ok"] == True
    assert list_response["filename"] is not None
    list_filename = list_response["filename"]
    print(f"   ✓ 목록 Excel 생성 완료: {list_filename}")
    
    # Step 4: build-base-scenario API 호출
    print("\n4. 기본 시나리오 Excel 생성 API 호출...")
    response = client.post(
        "/api/autodoc/build-base-scenario",
        json=change_request_data
    )
    
    assert response.status_code == 200
    scenario_response = response.json()
    assert scenario_response["ok"] == True
    assert scenario_response["filename"] is not None
    scenario_filename = scenario_response["filename"]
    print(f"   ✓ 기본 시나리오 Excel 생성 완료: {scenario_filename}")
    
    # Step 5: 실제 파일 생성 확인 (Task 1.2 DoD)
    print("\n5. documents 폴더에 파일 생성 확인 (DoD 검증)...")
    documents_dir = get_documents_dir()
    
    # Word 파일 확인
    word_path = documents_dir / word_filename
    assert word_path.exists(), f"Word 파일이 생성되지 않음: {word_path}"
    assert word_path.stat().st_size > 0, "Word 파일 크기가 0"
    print(f"   ✓ Word 파일 확인: {word_path} ({word_path.stat().st_size} bytes)")
    
    # 목록 Excel 파일 확인
    list_path = documents_dir / list_filename
    assert list_path.exists(), f"목록 Excel 파일이 생성되지 않음: {list_path}"
    assert list_path.stat().st_size > 0, "목록 Excel 파일 크기가 0"
    print(f"   ✓ 목록 Excel 확인: {list_path} ({list_path.stat().st_size} bytes)")
    
    # 시나리오 Excel 파일 확인
    scenario_path = documents_dir / scenario_filename
    assert scenario_path.exists(), f"시나리오 Excel 파일이 생성되지 않음: {scenario_path}"
    assert scenario_path.stat().st_size > 0, "시나리오 Excel 파일 크기가 0"
    print(f"   ✓ 시나리오 Excel 확인: {scenario_path} ({scenario_path.stat().st_size} bytes)")
    
    print("\n✅ Task 1.2 DoD 검증 성공: JSON POST 시 documents 폴더에 3개 파일 모두 생성됨")


def test_build_cm_word_api():
    """build-cm-word API 개별 테스트"""
    data = get_sample_change_request_data()
    
    response = client.post("/api/autodoc/build-cm-word", json=data)
    
    assert response.status_code == 200
    result = response.json()
    assert result["ok"] == True
    assert result["filename"] is not None
    assert result["filename"].endswith(".docx")
    
    # 실제 파일 확인
    documents_dir = get_documents_dir()
    file_path = documents_dir / result["filename"]
    assert file_path.exists()


def test_build_cm_list_api():
    """build-cm-list API 개별 테스트"""
    data = [get_sample_change_request_data()]  # 배열로 전송
    
    response = client.post("/api/autodoc/build-cm-list", json=data)
    
    assert response.status_code == 200
    result = response.json()
    assert result["ok"] == True
    assert result["filename"] is not None
    assert result["filename"].endswith(".xlsx")
    
    # 실제 파일 확인
    documents_dir = get_documents_dir()
    file_path = documents_dir / result["filename"]
    assert file_path.exists()


def test_build_base_scenario_api():
    """build-base-scenario API 개별 테스트"""
    data = get_sample_change_request_data()
    
    response = client.post("/api/autodoc/build-base-scenario", json=data)
    
    assert response.status_code == 200
    result = response.json()
    assert result["ok"] == True
    assert result["filename"] is not None
    assert result["filename"].endswith(".xlsx")
    
    # 실제 파일 확인
    documents_dir = get_documents_dir()
    file_path = documents_dir / result["filename"]
    assert file_path.exists()


def test_build_cm_list_empty_data():
    """build-cm-list API 빈 데이터 테스트"""
    response = client.post("/api/autodoc/build-cm-list", json=[])
    
    assert response.status_code == 400
    assert "데이터가 비어있습니다" in response.json()["detail"]


if __name__ == "__main__":
    # 개별 실행 시 테스트 실행
    test_build_cm_word_api()
    test_build_cm_list_api()
    test_build_base_scenario_api()
    test_build_cm_list_empty_data()
    test_full_workflow_with_parse_html()
    print("\n✅ 모든 문서 생성 API 통합 테스트 통과!")