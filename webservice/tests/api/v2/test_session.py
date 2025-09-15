"""
세션 관리 API 종합 테스트

새로운 세션 관리 시스템의 모든 엔드포인트와 기능을 테스트합니다.
- 세션 생성 및 준비
- 세션 생명주기 관리
- 세션 재사용 정책
- 세션 재시도 로직
- 세션 만료 및 자동 정리
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from pathlib import Path
import sys

# 프로젝트 경로 설정
sys.path.append(str(Path(__file__).resolve().parents[3]))

from app.main import app
from app.api.routers.v2.models import (
    PrepareSessionRequest,
    PrepareSessionResponse,
    SessionStatusResponse,
    SessionStatus
)
from app.api.routers.v2.session import (
    session_metadata_store,
    get_session_store,
    update_session_status,
    cleanup_task
)


class TestSessionAPI:
    """세션 관리 API 테스트 클래스"""

    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """각 테스트 전후 세션 저장소 초기화"""
        # 테스트 시작 전 저장소 초기화
        session_metadata_store.clear()
        yield
        # 테스트 종료 후 저장소 정리
        session_metadata_store.clear()

    @pytest.fixture
    def client(self):
        """테스트 클라이언트 fixture"""
        return TestClient(app)

    @pytest.fixture
    def sample_metadata(self):
        """테스트용 메타데이터 fixture"""
        return {
            "repository_path": "/test/repo",
            "vcs_type": "git",
            "user_name": "테스터",
            "purpose": "테스트 목적",
            "test_environment": "개발환경",
            "additional_requirements": "추가 요구사항"
        }

    @pytest.fixture
    def sample_prepare_request(self, sample_metadata):
        """테스트용 세션 준비 요청 fixture"""
        return {
            "session_id": "test_session_123",
            "metadata_json": sample_metadata,
            "html_file_path": "/test/path/test.html",
            "vcs_analysis_text": "테스트 VCS 분석 결과"
        }

    def test_prepare_session_new_creation(self, client, sample_prepare_request):
        """새 세션 생성 테스트"""
        # session_id를 제거하여 새 ID 자동 생성 트리거
        request_data = sample_prepare_request.copy()
        request_data["session_id"] = ""

        response = client.post("/api/webservice/v2/prepare-session", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # 응답 구조 검증
        assert "session_id" in data
        assert "status" in data
        assert "message" in data

        # 새 세션 생성 확인
        assert data["status"] == "created"
        assert "새 세션이 생성되었습니다" in data["message"]
        assert data["session_id"].startswith("session_")

        # 세션 저장소에 데이터 저장 확인
        session_store = get_session_store()
        assert data["session_id"] in session_store
        stored_session = session_store[data["session_id"]]
        assert stored_session["status"] == SessionStatus.PREPARED
        assert stored_session["metadata"] == sample_prepare_request["metadata_json"]

    def test_prepare_session_with_existing_id(self, client, sample_prepare_request):
        """기존 session_id로 새 세션 생성 테스트"""
        response = client.post("/api/webservice/v2/prepare-session", json=sample_prepare_request)

        assert response.status_code == 200
        data = response.json()

        # 지정된 session_id 사용 확인
        assert data["session_id"] == sample_prepare_request["session_id"]
        assert data["status"] == "created"

        # 세션 저장소 확인
        session_store = get_session_store()
        assert sample_prepare_request["session_id"] in session_store

    def test_prepare_session_reuse_completed(self, client, sample_prepare_request):
        """완료된 세션 재사용 테스트"""
        session_id = sample_prepare_request["session_id"]

        # 먼저 세션 생성
        response1 = client.post("/api/webservice/v2/prepare-session", json=sample_prepare_request)
        assert response1.status_code == 200

        # 세션 상태를 COMPLETED로 변경 (재사용 가능하도록)
        session_store = get_session_store()
        session_store[session_id]["status"] = SessionStatus.COMPLETED
        session_store[session_id]["reusable"] = True

        # 동일한 session_id로 다시 요청
        response2 = client.post("/api/webservice/v2/prepare-session", json=sample_prepare_request)

        assert response2.status_code == 200
        data = response2.json()

        # 재사용 확인
        assert data["session_id"] == session_id
        assert data["status"] == "reused"
        assert "완료된 세션을 재사용했습니다" in data["message"]

        # 세션 상태가 PREPARED로 변경되었는지 확인
        assert session_store[session_id]["status"] == SessionStatus.PREPARED
        assert session_store[session_id]["usage_count"] == 1

    def test_prepare_session_retry_failed(self, client, sample_prepare_request):
        """실패한 세션 재시도 테스트"""
        session_id = sample_prepare_request["session_id"]

        # 먼저 세션 생성 후 실패 상태로 변경
        response1 = client.post("/api/webservice/v2/prepare-session", json=sample_prepare_request)
        assert response1.status_code == 200

        session_store = get_session_store()
        session_store[session_id]["status"] = SessionStatus.FAILED
        session_store[session_id]["retry_count"] = 1
        session_store[session_id]["last_error"] = {"message": "테스트 에러", "timestamp": datetime.now().isoformat()}

        # 재시도 요청
        response2 = client.post("/api/webservice/v2/prepare-session", json=sample_prepare_request)

        assert response2.status_code == 200
        data = response2.json()

        # 재시도 확인
        assert data["session_id"] == session_id
        assert data["status"] == "retry"
        assert data["retry_attempt"] == 2
        assert data["max_retries"] == 3
        assert "실패한 세션을 재시도합니다" in data["message"]

        # 세션 상태 확인
        assert session_store[session_id]["status"] == SessionStatus.PREPARED

    def test_prepare_session_retry_limit_exceeded(self, client, sample_prepare_request):
        """재시도 한계 초과 시 새 세션 생성 테스트"""
        session_id = sample_prepare_request["session_id"]

        # 세션 생성 후 최대 재시도 횟수 도달 상태로 설정
        response1 = client.post("/api/webservice/v2/prepare-session", json=sample_prepare_request)
        assert response1.status_code == 200

        session_store = get_session_store()
        session_store[session_id]["status"] = SessionStatus.FAILED
        session_store[session_id]["retry_count"] = 3  # 최대 재시도 횟수 도달

        # 재시도 요청
        response2 = client.post("/api/webservice/v2/prepare-session", json=sample_prepare_request)

        assert response2.status_code == 200
        data = response2.json()

        # 새 세션 ID 생성 확인
        assert data["session_id"] != session_id
        assert data["session_id"].startswith(f"{session_id}_new_")
        assert data["status"] == "created"

    def test_prepare_session_conflict_in_progress(self, client, sample_prepare_request):
        """진행 중인 세션 충돌 테스트"""
        session_id = sample_prepare_request["session_id"]

        # 세션 생성 후 진행 중 상태로 변경
        response1 = client.post("/api/webservice/v2/prepare-session", json=sample_prepare_request)
        assert response1.status_code == 200

        session_store = get_session_store()
        session_store[session_id]["status"] = SessionStatus.IN_PROGRESS

        # 동일한 session_id로 다시 요청 (충돌 발생)
        response2 = client.post("/api/webservice/v2/prepare-session", json=sample_prepare_request)

        assert response2.status_code == 409
        error_data = response2.json()
        assert "아직 진행 중입니다" in error_data["detail"]

    def test_prepare_session_recycle_expired(self, client, sample_prepare_request):
        """만료된 세션 재활용 테스트"""
        session_id = sample_prepare_request["session_id"]

        # 세션 생성 후 만료 상태로 변경
        response1 = client.post("/api/webservice/v2/prepare-session", json=sample_prepare_request)
        assert response1.status_code == 200

        session_store = get_session_store()
        session_store[session_id]["status"] = SessionStatus.EXPIRED

        # 만료된 세션 재활용 요청
        response2 = client.post("/api/webservice/v2/prepare-session", json=sample_prepare_request)

        assert response2.status_code == 200
        data = response2.json()

        # 재활용 확인
        assert data["session_id"] == session_id
        assert data["status"] == "recycled"
        assert "만료된 세션을 재활용했습니다" in data["message"]

        # 세션 상태 초기화 확인
        assert session_store[session_id]["status"] == SessionStatus.PREPARED
        assert session_store[session_id]["usage_count"] == 0
        assert session_store[session_id]["retry_count"] == 0

    def test_get_session_metadata_success(self, client, sample_prepare_request):
        """세션 메타데이터 조회 성공 테스트"""
        session_id = sample_prepare_request["session_id"]

        # 세션 생성
        response1 = client.post("/api/webservice/v2/prepare-session", json=sample_prepare_request)
        assert response1.status_code == 200

        # 메타데이터 조회
        response2 = client.get(f"/api/webservice/v2/session/{session_id}/metadata")

        assert response2.status_code == 200
        metadata = response2.json()

        # 저장된 메타데이터와 일치 확인
        assert metadata == sample_prepare_request["metadata_json"]

    def test_get_session_metadata_not_found(self, client):
        """존재하지 않는 세션 메타데이터 조회 테스트"""
        response = client.get("/api/webservice/v2/session/nonexistent_session/metadata")

        assert response.status_code == 404
        error_data = response.json()
        assert "세션 nonexistent_session를 찾을 수 없습니다" in error_data["detail"]

    def test_get_session_metadata_expired(self, client, sample_prepare_request):
        """만료된 세션 메타데이터 조회 테스트"""
        session_id = sample_prepare_request["session_id"]

        # 세션 생성
        response1 = client.post("/api/webservice/v2/prepare-session", json=sample_prepare_request)
        assert response1.status_code == 200

        # 세션을 과거 시간으로 생성하여 만료시킴
        session_store = get_session_store()
        old_time = datetime.now() - timedelta(hours=2)  # TTL(1시간)보다 오래된 시간
        session_store[session_id]["created_at"] = old_time

        # 만료된 세션 메타데이터 조회
        response2 = client.get(f"/api/webservice/v2/session/{session_id}/metadata")

        assert response2.status_code == 410
        error_data = response2.json()
        assert "만료되었습니다" in error_data["detail"]

    def test_get_session_status_success(self, client, sample_prepare_request):
        """세션 상태 조회 성공 테스트"""
        session_id = sample_prepare_request["session_id"]

        # 세션 생성
        response1 = client.post("/api/webservice/v2/prepare-session", json=sample_prepare_request)
        assert response1.status_code == 200

        # 상태 조회
        response2 = client.get(f"/api/webservice/v2/session/{session_id}/status")

        assert response2.status_code == 200
        status_data = response2.json()

        # 상태 정보 검증
        assert status_data["session_id"] == session_id
        assert status_data["status"] == SessionStatus.PREPARED
        assert status_data["created_at"] is not None
        assert status_data["retry_count"] == 0
        assert status_data["usage_count"] == 0
        assert status_data["last_error"] is None
        assert status_data["previous_errors"] == []

    def test_get_session_status_not_found(self, client):
        """존재하지 않는 세션 상태 조회 테스트"""
        response = client.get("/api/webservice/v2/session/nonexistent_session/status")

        assert response.status_code == 404
        error_data = response.json()
        assert "세션 nonexistent_session를 찾을 수 없습니다" in error_data["detail"]

    def test_delete_session_success(self, client, sample_prepare_request):
        """세션 삭제 성공 테스트"""
        session_id = sample_prepare_request["session_id"]

        # 세션 생성
        response1 = client.post("/api/webservice/v2/prepare-session", json=sample_prepare_request)
        assert response1.status_code == 200

        # 세션 삭제
        response2 = client.delete(f"/api/webservice/v2/session/{session_id}")

        assert response2.status_code == 200
        data = response2.json()
        assert f"세션 {session_id}가 삭제되었습니다" in data["message"]

        # 세션 저장소에서 제거 확인
        session_store = get_session_store()
        assert session_id not in session_store

    def test_delete_session_not_found(self, client):
        """존재하지 않는 세션 삭제 테스트"""
        response = client.delete("/api/webservice/v2/session/nonexistent_session")

        assert response.status_code == 404
        error_data = response.json()
        assert "세션 nonexistent_session를 찾을 수 없습니다" in error_data["detail"]

    def test_sessions_stats(self, client, sample_prepare_request):
        """세션 통계 조회 테스트"""
        # 여러 세션 생성
        sessions = []
        for i in range(3):
            request_data = sample_prepare_request.copy()
            request_data["session_id"] = f"test_session_{i}"
            response = client.post("/api/webservice/v2/prepare-session", json=request_data)
            assert response.status_code == 200
            sessions.append(request_data["session_id"])

        # 세션 상태 다양화
        session_store = get_session_store()
        session_store[sessions[1]]["status"] = SessionStatus.IN_PROGRESS
        session_store[sessions[2]]["status"] = SessionStatus.COMPLETED

        # 통계 조회
        response = client.get("/api/webservice/v2/sessions/stats")

        assert response.status_code == 200
        stats = response.json()

        # 통계 검증
        assert stats["total_sessions"] == 3
        assert stats["status_counts"][SessionStatus.PREPARED] == 1
        assert stats["status_counts"][SessionStatus.IN_PROGRESS] == 1
        assert stats["status_counts"][SessionStatus.COMPLETED] == 1
        assert "cleanup_task_running" in stats

    def test_session_ttl_expiration(self, client, sample_prepare_request):
        """세션 TTL 만료 테스트"""
        session_id = sample_prepare_request["session_id"]

        # 세션 생성
        response = client.post("/api/webservice/v2/prepare-session", json=sample_prepare_request)
        assert response.status_code == 200

        # 세션을 과거 시간으로 생성하여 TTL 만료시킴
        session_store = get_session_store()
        old_time = datetime.now() - timedelta(hours=2)  # TTL(1시간)보다 오래된 시간
        session_store[session_id]["created_at"] = old_time

        # 만료된 세션 접근 시 상태 변경 확인
        response2 = client.get(f"/api/webservice/v2/session/{session_id}/metadata")
        assert response2.status_code == 410  # Gone

        # 세션 상태가 EXPIRED로 변경되었는지 확인
        assert session_store[session_id]["status"] == SessionStatus.EXPIRED


class TestSessionUtilityFunctions:
    """세션 유틸리티 함수 테스트 클래스"""

    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """각 테스트 전후 세션 저장소 초기화"""
        session_metadata_store.clear()
        yield
        session_metadata_store.clear()

    def test_get_session_store(self):
        """세션 저장소 접근 함수 테스트"""
        store = get_session_store()
        assert store is session_metadata_store

        # 저장소에 데이터 추가
        test_session_id = "test_session_123"
        store[test_session_id] = {"test": "data"}

        # 동일한 저장소 참조 확인
        store2 = get_session_store()
        assert test_session_id in store2
        assert store2[test_session_id]["test"] == "data"

    def test_update_session_status_completed(self):
        """세션 상태 업데이트 - 완료 테스트"""
        session_id = "test_session_123"

        # 세션 초기 데이터 생성
        session_store = get_session_store()
        session_store[session_id] = {
            "status": SessionStatus.IN_PROGRESS,
            "created_at": datetime.now(),
            "completed_at": None
        }

        # 완료 상태로 업데이트
        update_session_status(session_id, SessionStatus.COMPLETED)

        # 상태 변경 확인
        updated_session = session_store[session_id]
        assert updated_session["status"] == SessionStatus.COMPLETED
        assert updated_session["completed_at"] is not None

    def test_update_session_status_failed_with_error(self):
        """세션 상태 업데이트 - 실패 및 에러 메시지 테스트"""
        session_id = "test_session_123"

        # 세션 초기 데이터 생성
        session_store = get_session_store()
        session_store[session_id] = {
            "status": SessionStatus.IN_PROGRESS,
            "created_at": datetime.now(),
            "failed_at": None,
            "last_error": None
        }

        # 실패 상태로 업데이트 (에러 메시지 포함)
        error_message = "테스트 에러 발생"
        update_session_status(session_id, SessionStatus.FAILED, error_message=error_message)

        # 상태 및 에러 정보 확인
        updated_session = session_store[session_id]
        assert updated_session["status"] == SessionStatus.FAILED
        assert updated_session["failed_at"] is not None
        assert updated_session["last_error"]["message"] == error_message
        assert updated_session["last_error"]["timestamp"] is not None

    def test_update_session_status_with_additional_data(self):
        """세션 상태 업데이트 - 추가 데이터 포함 테스트"""
        session_id = "test_session_123"

        # 세션 초기 데이터 생성
        session_store = get_session_store()
        session_store[session_id] = {
            "status": SessionStatus.PREPARED,
            "custom_field": None
        }

        # 추가 데이터와 함께 상태 업데이트
        update_session_status(
            session_id,
            SessionStatus.IN_PROGRESS,
            custom_field="custom_value",
            progress=50
        )

        # 추가 데이터 확인
        updated_session = session_store[session_id]
        assert updated_session["status"] == SessionStatus.IN_PROGRESS
        assert updated_session["custom_field"] == "custom_value"
        assert updated_session["progress"] == 50

    def test_update_session_status_nonexistent_session(self):
        """존재하지 않는 세션 상태 업데이트 테스트"""
        # 존재하지 않는 세션 상태 업데이트 시도
        # 함수는 오류를 발생시키지 않고 조용히 무시해야 함
        update_session_status("nonexistent_session", SessionStatus.COMPLETED)

        # 세션 저장소가 비어있는지 확인
        session_store = get_session_store()
        assert "nonexistent_session" not in session_store


class TestSessionModels:
    """세션 데이터 모델 테스트 클래스"""

    def test_prepare_session_request_validation(self):
        """PrepareSessionRequest 모델 유효성 검증 테스트"""
        # 정상적인 요청
        valid_data = {
            "session_id": "test_session_123",
            "metadata_json": {"test": "data"},
            "html_file_path": "/test/path/test.html",
            "vcs_analysis_text": "테스트 VCS 분석"
        }

        request = PrepareSessionRequest(**valid_data)
        assert request.session_id == "test_session_123"
        assert request.metadata_json == {"test": "data"}
        assert request.html_file_path == "/test/path/test.html"
        assert request.vcs_analysis_text == "테스트 VCS 분석"

    def test_prepare_session_request_optional_fields(self):
        """PrepareSessionRequest 선택적 필드 테스트"""
        # session_id가 빈 문자열인 경우 (자동 생성 트리거)
        data_with_empty_session_id = {
            "session_id": "",
            "metadata_json": {"test": "data"},
            "html_file_path": "/test/path/test.html",
            "vcs_analysis_text": "테스트 VCS 분석"
        }

        request = PrepareSessionRequest(**data_with_empty_session_id)
        assert request.session_id == ""

    def test_prepare_session_response_structure(self):
        """PrepareSessionResponse 모델 구조 테스트"""
        response_data = {
            "session_id": "test_session_123",
            "status": "created",
            "message": "새 세션이 생성되었습니다"
        }

        response = PrepareSessionResponse(**response_data)
        assert response.session_id == "test_session_123"
        assert response.status == "created"
        assert response.message == "새 세션이 생성되었습니다"

    def test_session_status_response_complete(self):
        """SessionStatusResponse 전체 필드 테스트"""
        status_data = {
            "session_id": "test_session_123",
            "status": SessionStatus.COMPLETED,
            "created_at": datetime.now(),
            "completed_at": datetime.now(),
            "failed_at": None,
            "retry_count": 1,
            "usage_count": 2,
            "last_error": {"message": "이전 에러", "timestamp": "2023-01-01T12:00:00"},
            "previous_errors": ["에러1", "에러2"]
        }

        response = SessionStatusResponse(**status_data)
        assert response.session_id == "test_session_123"
        assert response.status == SessionStatus.COMPLETED
        assert response.retry_count == 1
        assert response.usage_count == 2
        assert response.last_error["message"] == "이전 에러"
        assert len(response.previous_errors) == 2

    def test_session_status_enum_values(self):
        """SessionStatus 열거형 값 테스트"""
        # 모든 세션 상태 값 확인
        assert SessionStatus.PREPARED == "prepared"
        assert SessionStatus.IN_PROGRESS == "in_progress"
        assert SessionStatus.COMPLETED == "completed"
        assert SessionStatus.FAILED == "failed"
        assert SessionStatus.EXPIRED == "expired"


class TestSessionIntegrationScenarios:
    """세션 통합 시나리오 테스트 클래스"""

    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """각 테스트 전후 세션 저장소 초기화"""
        session_metadata_store.clear()
        yield
        session_metadata_store.clear()

    @pytest.fixture
    def client(self):
        """테스트 클라이언트 fixture"""
        return TestClient(app)

    def test_complete_session_lifecycle(self, client):
        """완전한 세션 생명주기 테스트"""
        session_data = {
            "session_id": "lifecycle_test_session",
            "metadata_json": {"purpose": "생명주기 테스트"},
            "html_file_path": "/test/lifecycle.html",
            "vcs_analysis_text": "생명주기 테스트 VCS 분석"
        }

        # 1. 세션 생성
        response1 = client.post("/api/webservice/v2/prepare-session", json=session_data)
        assert response1.status_code == 200
        session_id = response1.json()["session_id"]

        # 2. 세션 상태 조회 (PREPARED)
        response2 = client.get(f"/api/webservice/v2/session/{session_id}/status")
        assert response2.status_code == 200
        assert response2.json()["status"] == SessionStatus.PREPARED

        # 3. 세션 상태를 IN_PROGRESS로 변경
        update_session_status(session_id, SessionStatus.IN_PROGRESS)

        # 4. 진행 중 상태 확인
        response3 = client.get(f"/api/webservice/v2/session/{session_id}/status")
        assert response3.status_code == 200
        assert response3.json()["status"] == SessionStatus.IN_PROGRESS

        # 5. 세션 완료
        update_session_status(session_id, SessionStatus.COMPLETED)

        # 6. 완료 상태 확인
        response4 = client.get(f"/api/webservice/v2/session/{session_id}/status")
        assert response4.status_code == 200
        status_data = response4.json()
        assert status_data["status"] == SessionStatus.COMPLETED
        assert status_data["completed_at"] is not None

        # 7. 완료된 세션 재사용
        response5 = client.post("/api/webservice/v2/prepare-session", json=session_data)
        assert response5.status_code == 200
        assert response5.json()["status"] == "reused"

        # 8. 세션 삭제
        response6 = client.delete(f"/api/webservice/v2/session/{session_id}")
        assert response6.status_code == 200

    def test_session_failure_and_retry_workflow(self, client):
        """세션 실패 및 재시도 워크플로우 테스트"""
        session_data = {
            "session_id": "retry_test_session",
            "metadata_json": {"purpose": "재시도 테스트"},
            "html_file_path": "/test/retry.html",
            "vcs_analysis_text": "재시도 테스트 VCS 분석"
        }

        # 1. 세션 생성 및 실패 시뮬레이션
        response1 = client.post("/api/webservice/v2/prepare-session", json=session_data)
        assert response1.status_code == 200
        session_id = response1.json()["session_id"]

        # 2. 세션 실패 처리 (retry_count는 0부터 시작)
        update_session_status(session_id, SessionStatus.FAILED, error_message="첫 번째 실패")

        # 3. 첫 번째 재시도 (retry_count=0, retry_attempt=1)
        response2 = client.post("/api/webservice/v2/prepare-session", json=session_data)
        assert response2.status_code == 200
        retry_data = response2.json()
        assert retry_data["status"] == "retry"
        assert retry_data["retry_attempt"] == 1

        # 4. 두 번째 실패 및 재시도 (retry_count=0에서 1로 증가하지 않음)
        update_session_status(session_id, SessionStatus.FAILED, error_message="두 번째 실패")
        # retry_count를 1로 수동 설정
        session_store = get_session_store()
        session_store[session_id]["retry_count"] = 1

        response3 = client.post("/api/webservice/v2/prepare-session", json=session_data)
        assert response3.status_code == 200
        assert response3.json()["retry_attempt"] == 2

        # 5. 세 번째 실패 및 재시도
        update_session_status(session_id, SessionStatus.FAILED, error_message="세 번째 실패")
        session_store[session_id]["retry_count"] = 2

        response4 = client.post("/api/webservice/v2/prepare-session", json=session_data)
        assert response4.status_code == 200
        assert response4.json()["retry_attempt"] == 3

        # 6. 네 번째 실패 시 새 세션 생성 (retry_count=3 도달)
        update_session_status(session_id, SessionStatus.FAILED, error_message="네 번째 실패")
        session_store[session_id]["retry_count"] = 3

        response5 = client.post("/api/webservice/v2/prepare-session", json=session_data)
        assert response5.status_code == 200
        new_session_data = response5.json()
        assert new_session_data["status"] == "created"
        assert new_session_data["session_id"] != session_id
        assert new_session_data["session_id"].startswith(f"{session_id}_new_")

    def test_concurrent_session_access_simulation(self, client):
        """동시 세션 접근 시뮬레이션 테스트"""
        session_data = {
            "session_id": "concurrent_test_session",
            "metadata_json": {"purpose": "동시성 테스트"},
            "html_file_path": "/test/concurrent.html",
            "vcs_analysis_text": "동시성 테스트 VCS 분석"
        }

        # 1. 첫 번째 클라이언트가 세션 생성 및 진행 시작
        response1 = client.post("/api/webservice/v2/prepare-session", json=session_data)
        assert response1.status_code == 200
        session_id = response1.json()["session_id"]

        # 세션을 진행 중 상태로 변경
        update_session_status(session_id, SessionStatus.IN_PROGRESS)

        # 2. 두 번째 클라이언트가 동일한 세션으로 요청 시 충돌
        response2 = client.post("/api/webservice/v2/prepare-session", json=session_data)
        assert response2.status_code == 409
        assert "아직 진행 중입니다" in response2.json()["detail"]

        # 3. 첫 번째 세션 완료 후 두 번째 클라이언트 요청 성공
        update_session_status(session_id, SessionStatus.COMPLETED)
        response3 = client.post("/api/webservice/v2/prepare-session", json=session_data)
        assert response3.status_code == 200
        assert response3.json()["status"] == "reused"

    @patch('app.api.routers.v2.session.cleanup_expired_sessions')
    def test_cleanup_task_integration(self, mock_cleanup, client):
        """자동 정리 태스크 통합 테스트"""
        session_data = {
            "session_id": "cleanup_test_session",
            "metadata_json": {"purpose": "정리 테스트"},
            "html_file_path": "/test/cleanup.html",
            "vcs_analysis_text": "정리 테스트 VCS 분석"
        }

        # 세션 생성 (cleanup task 시작 트리거)
        response = client.post("/api/webservice/v2/prepare-session", json=session_data)
        assert response.status_code == 200

        # cleanup task가 시작되었는지 확인 (mock 호출은 안 되지만 task가 생성됨)
        # 실제 환경에서는 백그라운드에서 실행되므로 통계에서 확인
        stats_response = client.get("/api/webservice/v2/sessions/stats")
        assert stats_response.status_code == 200
        stats = stats_response.json()
        # cleanup_task_running 필드 존재 확인
        assert "cleanup_task_running" in stats