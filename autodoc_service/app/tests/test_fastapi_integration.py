"""
FastAPI 통합 테스트

TestClient를 사용한 API 엔드포인트 테스트
"""
import json
import tempfile
from pathlib import Path
from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from ..main import app
from ..models import ChangeRequest


class TestFastAPIIntegration:
    """FastAPI 통합 테스트"""
    
    @pytest.fixture
    def client(self):
        """TestClient 인스턴스"""
        return TestClient(app)
    
    @pytest.fixture
    def sample_change_request_data(self):
        """테스트용 변경 요청 JSON 데이터"""
        return {
            "change_id": "TEST_20250814_1",
            "system": "테스트시스템",
            "title": "API 테스트용 변경사항",
            "requester": "테스트사용자",
            "writer_short": "테스터",
            "details": {
                "summary": "API 테스트를 위한 요약"
            }
        }
    
    @pytest.fixture
    def sample_html_content(self):
        """테스트용 HTML 콘텐츠"""
        return """
        <html>
        <body>
        <div class="dwp-title" data-xlang-code="comm.title.subject">제목</div>
        <div class="dwp-value">
            <div class="dwp-input expended">테스트 제목</div>
        </div>
        </body>
        </html>
        """
    
    def test_root_endpoint(self, client):
        """루트 엔드포인트 테스트"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "AutoDoc Service API"
        assert data["version"] == "1.0.0"
    
    def test_health_check_endpoint(self, client):
        """헬스 체크 엔드포인트 테스트"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "templates_available" in data
        assert "documents_dir_writable" in data
        assert isinstance(data["templates_available"], bool)
        assert isinstance(data["documents_dir_writable"], bool)
    
    def test_parse_html_endpoint_success(self, client, sample_html_content):
        """HTML 파싱 엔드포인트 성공 테스트"""
        # HTML 파일로 만들어 업로드
        html_bytes = sample_html_content.encode('utf-8')
        files = {"file": ("test.html", BytesIO(html_bytes), "text/html")}
        
        response = client.post("/parse-html", files=files)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "data" in data
        assert isinstance(data["data"], dict)
    
    def test_parse_html_endpoint_invalid_file(self, client):
        """HTML 파싱 엔드포인트 잘못된 파일 테스트"""
        # 텍스트 파일을 업로드
        text_content = "This is not HTML"
        files = {"file": ("test.txt", BytesIO(text_content.encode('utf-8')), "text/plain")}
        
        response = client.post("/parse-html", files=files)
        
        assert response.status_code == 400
        assert "HTML 파일만 업로드 가능합니다" in response.json()["detail"]
    
    def test_create_cm_word_endpoint_success(self, client, sample_change_request_data):
        """Word 문서 생성 엔드포인트 성공 테스트"""
        response = client.post("/create-cm-word", json=sample_change_request_data)
        
        # 템플릿이 있다면 성공, 없다면 404
        if response.status_code == 200:
            data = response.json()
            assert data["ok"] is True
            assert "filename" in data
            assert data["filename"].endswith(".docx")
        elif response.status_code == 404:
            # 템플릿이 없는 경우
            assert "템플릿" in response.json()["detail"]
        else:
            pytest.fail(f"예상치 못한 상태 코드: {response.status_code}")
    
    def test_create_cm_word_endpoint_missing_required_field(self, client):
        """Word 문서 생성 필수 필드 누락 테스트"""
        incomplete_data = {
            "change_id": "",  # 빈 값
            "system": "테스트시스템",
            "title": "테스트 제목"
        }
        
        response = client.post("/create-cm-word", json=incomplete_data)
        
        assert response.status_code == 400
        assert "change_id는 필수입니다" in response.json()["detail"]
    
    def test_create_test_excel_endpoint_success(self, client, sample_change_request_data):
        """Excel 테스트 시나리오 생성 엔드포인트 성공 테스트"""
        response = client.post("/create-test-excel", json=sample_change_request_data)
        
        # 템플릿이 있다면 성공, 없다면 404
        if response.status_code == 200:
            data = response.json()
            assert data["ok"] is True
            assert "filename" in data
            assert data["filename"].endswith(".xlsx")
        elif response.status_code == 404:
            # 템플릿이 없는 경우
            assert "템플릿" in response.json()["detail"]
        else:
            pytest.fail(f"예상치 못한 상태 코드: {response.status_code}")
    
    def test_create_cm_list_endpoint_success(self, client, sample_change_request_data):
        """변경관리 목록 생성 엔드포인트 성공 테스트"""
        list_data = [sample_change_request_data]
        
        response = client.post("/create-cm-list", json=list_data)
        
        # 템플릿이 있다면 성공, 없다면 404
        if response.status_code == 200:
            data = response.json()
            assert data["ok"] is True
            assert "filename" in data
            assert data["filename"].endswith(".xlsx")
        elif response.status_code == 404:
            # 템플릿이 없는 경우
            assert "템플릿" in response.json()["detail"]
        else:
            pytest.fail(f"예상치 못한 상태 코드: {response.status_code}")
    
    def test_create_cm_list_endpoint_empty_data(self, client):
        """변경관리 목록 빈 데이터 테스트"""
        response = client.post("/create-cm-list", json=[])
        
        assert response.status_code == 400
        assert "데이터가 비어있습니다" in response.json()["detail"]
    
    def test_download_file_endpoint_not_found(self, client):
        """파일 다운로드 존재하지 않는 파일 테스트"""
        response = client.get("/download/nonexistent_file.docx")
        
        assert response.status_code == 404
        assert "파일을 찾을 수 없습니다" in response.json()["detail"]
    
    def test_download_file_endpoint_path_traversal_attack(self, client):
        """파일 다운로드 경로 순회 공격 방어 테스트"""
        # 상위 디렉터리 접근 시도
        response = client.get("/download/../../../etc/passwd")
        
        assert response.status_code == 403
        assert "접근 권한이 없습니다" in response.json()["detail"]
    
    def test_list_templates_endpoint(self, client):
        """템플릿 목록 조회 엔드포인트 테스트"""
        response = client.get("/templates")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "templates" in data
        assert isinstance(data["templates"], list)
        
        # 각 템플릿 항목 구조 확인
        for template in data["templates"]:
            assert "name" in template
            assert "type" in template
            assert "exists" in template
            assert template["type"] in ["word", "excel"]
            assert isinstance(template["exists"], bool)
    
    def test_list_documents_endpoint(self, client):
        """문서 목록 조회 엔드포인트 테스트"""
        response = client.get("/documents")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "documents" in data
        assert isinstance(data["documents"], list)
        
        # 각 문서 항목 구조 확인
        for doc in data["documents"]:
            assert "name" in doc
            assert "size" in doc
            assert "modified" in doc
            assert isinstance(doc["size"], int)
            assert isinstance(doc["modified"], (int, float))
    
    def test_cors_headers(self, client):
        """CORS 헤더 테스트"""
        response = client.options("/")
        
        # CORS 헤더가 있는지 확인
        assert "access-control-allow-origin" in response.headers
    
    def test_invalid_json_handling(self, client):
        """잘못된 JSON 처리 테스트"""
        response = client.post(
            "/create-cm-word", 
            data="invalid json",
            headers={"content-type": "application/json"}
        )
        
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_pydantic_validation_error(self, client):
        """Pydantic 검증 오류 테스트"""
        invalid_data = {
            "change_id": 123,  # 문자열이어야 하는데 숫자
            "system": "테스트시스템",
            "title": "테스트 제목"
        }
        
        response = client.post("/create-cm-word", json=invalid_data)
        
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        assert isinstance(error_detail, list)
        assert any("change_id" in str(error) for error in error_detail)
    
    def test_api_documentation_available(self, client):
        """API 문서 접근 가능 테스트"""
        # OpenAPI 스키마
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert schema["info"]["title"] == "AutoDoc Service"
        
        # Swagger UI (선택사항 - FastAPI가 자동 제공)
        response = client.get("/docs")
        assert response.status_code == 200
    
    @pytest.mark.parametrize("endpoint", [
        "/create-cm-word",
        "/create-test-excel", 
        "/create-cm-list"
    ])
    def test_content_type_validation(self, client, endpoint):
        """Content-Type 검증 테스트"""
        # JSON이 아닌 데이터로 POST 요청
        response = client.post(
            endpoint,
            data="not json data",
            headers={"content-type": "text/plain"}
        )
        
        assert response.status_code == 422  # Unprocessable Entity