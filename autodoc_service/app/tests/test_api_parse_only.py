"""
파싱 전용 API 테스트 (parse-html-only)
Task 1.1의 DoD 검증을 위한 테스트
"""
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app

# 테스트 클라이언트 생성
client = TestClient(app)

# fixtures 디렉토리 경로
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parse_html_only_success():
    """HTML 파일 POST 시 JSON 200 응답 확인 (Task 1.1 DoD)"""
    # fixtures에서 샘플 HTML 파일 사용 (필수)
    sample_html_path = FIXTURES_DIR / "sample_itsupp.html"
    
    # 파일이 없으면 테스트 실패
    assert sample_html_path.exists(), "테스트를 위해 fixtures/sample_itsupp.html 파일이 반드시 필요합니다."
    
    # 실제 파일 사용
    with open(sample_html_path, 'rb') as f:
        files = {"file": ("sample_itsupp.html", f, "text/html")}
        # API 호출 (파일이 열려있는 상태에서)
        response = client.post("/api/autodoc/parse-html-only", files=files)
    
    # DoD 검증: HTTP 200 상태 코드
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    # 응답 JSON 파싱
    data = response.json()
    
    # DoD 검증: 성공 플래그
    assert data["success"] == True, "Parsing should be successful"
    
    # DoD 검증: 파싱된 데이터 존재
    assert "data" in data, "Response should contain 'data' field"
    assert data["data"] is not None, "Parsed data should not be None"
    
    # DoD 검증: 예상되는 필드 포함
    parsed_data = data["data"]
    if parsed_data:  # 파싱된 데이터가 있으면
        # 기본 필드들이 있는지 확인 (일부는 없을 수 있음)
        expected_fields = ["제목", "변경관리번호", "시스템", "요청자", "요청부서"]
        found_fields = [field for field in expected_fields if field in parsed_data]
        assert len(found_fields) > 0, f"At least one expected field should be found. Parsed keys: {list(parsed_data.keys())}"
    
    print(f"✅ Task 1.1 DoD 검증 성공: HTML POST 시 JSON 200 응답 확인됨")
    print(f"   - HTTP Status: {response.status_code}")
    print(f"   - Success: {data['success']}")
    print(f"   - Fields parsed: {len(parsed_data) if parsed_data else 0}")


def test_parse_html_only_invalid_file():
    """HTML이 아닌 파일 업로드 시 에러 확인"""
    # 텍스트 파일 업로드 시도
    files = {"file": ("test.txt", "This is not HTML", "text/plain")}
    
    response = client.post("/api/autodoc/parse-html-only", files=files)
    
    # 400 에러 예상
    assert response.status_code == 400
    assert "HTML 파일만 업로드 가능합니다" in response.json()["detail"]


def test_parse_html_only_unicode_error():
    """잘못된 인코딩 파일 업로드 시 에러 확인"""
    # 잘못된 인코딩의 바이트 데이터
    invalid_bytes = b'\xff\xfe\x00\x00Invalid encoding'
    files = {"file": ("test.html", invalid_bytes, "text/html")}
    
    response = client.post("/api/autodoc/parse-html-only", files=files)
    
    # 400 에러 예상
    assert response.status_code == 400
    assert "인코딩 오류" in response.json()["detail"]


if __name__ == "__main__":
    # 개별 실행 시 테스트 실행
    test_parse_html_only_success()
    test_parse_html_only_invalid_file()
    test_parse_html_only_unicode_error()
    print("\n✅ 모든 parse-html-only API 테스트 통과!")