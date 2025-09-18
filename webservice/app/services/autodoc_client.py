"""
AutoDoc Service 클라이언트

Phase 2: Webservice에서 autodoc_service로 문서 생성 요청을 보내는 클라이언트
"""

import asyncio
import httpx
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class AutoDocServiceError(Exception):
    """AutoDoc Service 호출 관련 오류"""
    pass


def transform_metadata_to_enhanced_request(metadata_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    webservice 메타데이터를 autodoc_service enhanced 요청 형식으로 변환
    
    Args:
        metadata_json: webservice에서 전달받은 메타데이터
        
    Returns:
        autodoc_service에서 기대하는 enhanced 요청 형식
    """
    raw_data = metadata_json.get("raw_data", {})
    
    # 디버그 로깅: 입력 데이터 확인
    logger.info(f"변환 입력 데이터 - metadata_json keys: {list(metadata_json.keys())}")
    logger.info(f"변환 입력 데이터 - raw_data keys: {list(raw_data.keys()) if raw_data else 'None'}")
    
    # raw_data가 API 응답 구조 {'success': true, 'data': {...}}인 경우 실제 데이터 추출
    if raw_data and 'data' in raw_data and 'success' in raw_data:
        logger.info("API 응답 구조 감지: raw_data['data']에서 실제 데이터 추출")
        actual_data = raw_data.get('data', {})
        logger.info(f"실제 데이터 keys: {list(actual_data.keys()) if actual_data else 'None'}")
    else:
        actual_data = raw_data
        logger.info("직접 데이터 구조 사용")
    
    if actual_data:
        logger.info(f"actual_data 샘플: 처리자_약칭={actual_data.get('처리자_약칭')}, 요청자={actual_data.get('요청자')}, 변경관리번호={actual_data.get('변경관리번호')}")
    
    # actual_data에서 실제 값을 추출하여 change_request 생성
    change_request = {
        "change_id": actual_data.get("변경관리번호") or metadata_json.get("change_id", "UNKNOWN"),
        "title": actual_data.get("제목") or metadata_json.get("title", "제목 없음"),
        "system": actual_data.get("요청시스템") or metadata_json.get("system", "시스템 없음"),
        "requester": actual_data.get("요청자") or metadata_json.get("requester", "요청자 없음"),
        "writer_short": actual_data.get("처리자_약칭") or actual_data.get("요청자") or metadata_json.get("requester", "요청자"),
        "request_dept": actual_data.get("요청부서"),
        "doc_no": actual_data.get("문서번호"),
        "work_datetime": actual_data.get("작업일시"),
        "deploy_datetime": actual_data.get("배포일시"),
        "customer": actual_data.get("고객사"),
        "worker_deployer": actual_data.get("배포자"),
        "created_date": actual_data.get("작성일")
    }
    
    # None 값 제거 (autodoc_service에서 Optional 필드들)
    change_request = {k: v for k, v in change_request.items() if v is not None}
    
    # enhanced 요청 형식으로 변환
    enhanced_request = {
        "raw_data": actual_data,  # API 응답에서 추출한 실제 데이터 사용
        "change_request": change_request
    }
    
    logger.info(f"메타데이터 변환 완료: change_id={change_request.get('change_id')}, writer_short={change_request.get('writer_short')}")
    
    return enhanced_request


class AutoDocClient:
    """AutoDoc Service HTTP 클라이언트"""
    
    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0):
        """
        Args:
            base_url: autodoc_service 서버 URL (None이면 환경변수에서 자동 설정)
            timeout: HTTP 요청 타임아웃 (초)
        """
        # 환경변수에서 AutoDoc Service URL 동적 해결
        if base_url is None:
            base_url = os.getenv('AUTODOC_SERVICE_URL', 'http://localhost:8001')
            logger.info(f"AutoDoc Service URL 환경변수에서 설정: {base_url}")
        
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        self.client = httpx.AsyncClient(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self.client:
            await self.client.aclose()
            self.client = None
    
    async def health_check(self) -> Dict[str, Any]:
        """
        AutoDoc Service 헬스 체크
        
        Returns:
            헬스 체크 결과
        """
        if not self.client:
            raise AutoDocServiceError("클라이언트가 초기화되지 않았습니다")
        
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            raise AutoDocServiceError(f"AutoDoc Service 연결 실패: {e}")
        except httpx.HTTPStatusError as e:
            raise AutoDocServiceError(f"AutoDoc Service 헬스 체크 실패: {e.response.status_code}")
    
    async def build_cm_word(self, metadata_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Word 문서 생성 요청 (enhanced API 사용)
        
        Args:
            metadata_json: webservice 메타데이터 (raw_data 포함)
            
        Returns:
            생성 결과 (파일명 포함)
        """
        if not self.client:
            raise AutoDocServiceError("클라이언트가 초기화되지 않았습니다")
        
        try:
            # 메타데이터를 enhanced 요청 형식으로 변환
            enhanced_request = transform_metadata_to_enhanced_request(metadata_json)
            
            logger.info(f"Word 문서 생성 요청: {enhanced_request['change_request'].get('change_id', 'N/A')}")
            
            response = await self.client.post(
                f"{self.base_url}/api/autodoc/create-cm-word-enhanced",
                json=enhanced_request
            )
            response.raise_for_status()
            result = response.json()
            
            if not result.get("ok", False):
                raise AutoDocServiceError(f"Word 문서 생성 실패: {result.get('error', '알 수 없는 오류')}")
            
            logger.info(f"Word 문서 생성 완료: {result.get('filename')}")
            return result
            
        except httpx.RequestError as e:
            raise AutoDocServiceError(f"Word 문서 생성 요청 실패: {e}")
        except httpx.HTTPStatusError as e:
            raise AutoDocServiceError(f"Word 문서 생성 HTTP 오류: {e.response.status_code}")
    
    async def build_cm_list(self, change_requests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Excel 목록 생성 요청
        
        Args:
            change_requests: 변경 요청 데이터 목록 (webservice 메타데이터 형식)
            
        Returns:
            생성 결과 (파일명 포함)
        """
        if not self.client:
            raise AutoDocServiceError("클라이언트가 초기화되지 않았습니다")
        
        try:
            # 각 메타데이터를 ChangeRequest 형식으로 변환
            transformed_requests = []
            for metadata in change_requests:
                enhanced_request = transform_metadata_to_enhanced_request(metadata)
                transformed_requests.append(enhanced_request['change_request'])
            
            logger.info(f"Excel 목록 생성 요청: {len(transformed_requests)}개 항목")
            
            response = await self.client.post(
                f"{self.base_url}/api/autodoc/build-cm-list",
                json=transformed_requests
            )
            response.raise_for_status()
            result = response.json()
            
            if not result.get("ok", False):
                raise AutoDocServiceError(f"Excel 목록 생성 실패: {result.get('error', '알 수 없는 오류')}")
            
            logger.info(f"Excel 목록 생성 완료: {result.get('filename')}")
            return result
            
        except httpx.RequestError as e:
            raise AutoDocServiceError(f"Excel 목록 생성 요청 실패: {e}")
        except httpx.HTTPStatusError as e:
            raise AutoDocServiceError(f"Excel 목록 생성 HTTP 오류: {e.response.status_code}")
    
    async def build_base_scenario(self, metadata_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        기본 시나리오 Excel 생성 요청
        
        Args:
            metadata_json: webservice 메타데이터 (raw_data 포함)
            
        Returns:
            생성 결과 (파일명 포함)
        """
        if not self.client:
            raise AutoDocServiceError("클라이언트가 초기화되지 않았습니다")
        
        try:
            # 메타데이터를 ChangeRequest 형식으로 변환
            enhanced_request = transform_metadata_to_enhanced_request(metadata_json)
            change_request = enhanced_request['change_request']
            
            logger.info(f"기본 시나리오 생성 요청: {change_request.get('change_id', 'N/A')}")
            
            response = await self.client.post(
                f"{self.base_url}/api/autodoc/build-base-scenario",
                json=change_request
            )
            response.raise_for_status()
            result = response.json()
            
            if not result.get("ok", False):
                raise AutoDocServiceError(f"기본 시나리오 생성 실패: {result.get('error', '알 수 없는 오류')}")
            
            logger.info(f"기본 시나리오 생성 완료: {result.get('filename')}")
            return result
            
        except httpx.RequestError as e:
            raise AutoDocServiceError(f"기본 시나리오 생성 요청 실패: {e}")
        except httpx.HTTPStatusError as e:
            raise AutoDocServiceError(f"기본 시나리오 생성 HTTP 오류: {e.response.status_code}")
    
    async def build_test_scenario(self, metadata_json: Dict[str, Any], test_cases: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        테스트 시나리오 Excel 생성 요청 (기본 시나리오 + LLM 테스트 케이스 통합)
        
        Args:
            metadata_json: webservice 메타데이터 (raw_data 포함)
            test_cases: LLM이 생성한 추가 테스트 케이스 목록
            
        Returns:
            생성 결과 (파일명 포함)
        """
        if not self.client:
            raise AutoDocServiceError("클라이언트가 초기화되지 않았습니다")
        
        try:
            # 메타데이터를 ChangeRequest 형식으로 변환
            enhanced_request = transform_metadata_to_enhanced_request(metadata_json)
            change_request = enhanced_request['change_request']
            
            logger.info(f"테스트 시나리오 생성 요청: {change_request.get('change_id', 'N/A')}, {len(test_cases) if test_cases else 0}개 테스트 케이스")
            
            request_data = {
                "change_request": change_request,
                "test_cases": test_cases or []
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/autodoc/build-test-scenario",
                json=request_data
            )
            response.raise_for_status()
            result = response.json()
            
            if not result.get("ok", False):
                raise AutoDocServiceError(f"테스트 시나리오 생성 실패: {result.get('error', '알 수 없는 오류')}")
            
            logger.info(f"테스트 시나리오 생성 완료: {result.get('filename')}")
            return result
            
        except httpx.RequestError as e:
            raise AutoDocServiceError(f"테스트 시나리오 생성 요청 실패: {e}")
        except httpx.HTTPStatusError as e:
            raise AutoDocServiceError(f"테스트 시나리오 생성 HTTP 오류: {e.response.status_code}")
    
    async def list_documents(self) -> Dict[str, Any]:
        """
        문서 목록 조회
        
        Returns:
            문서 목록
        """
        if not self.client:
            raise AutoDocServiceError("클라이언트가 초기화되지 않았습니다")
        
        try:
            response = await self.client.get(f"{self.base_url}/api/autodoc/documents")
            response.raise_for_status()
            return response.json()
            
        except httpx.RequestError as e:
            raise AutoDocServiceError(f"문서 목록 조회 실패: {e}")
        except httpx.HTTPStatusError as e:
            raise AutoDocServiceError(f"문서 목록 조회 HTTP 오류: {e.response.status_code}")
    
    async def get_download_url(self, filename: str) -> str:
        """
        파일 다운로드 URL 생성
        
        Args:
            filename: 다운로드할 파일명
            
        Returns:
            다운로드 URL
        """
        return f"{self.base_url}/api/autodoc/download/{filename}"


async def test_autodoc_client():
    """AutoDoc 클라이언트 테스트 함수"""
    async with AutoDocClient() as client:
        try:
            # 헬스 체크
            health = await client.health_check()
            print(f"Health check: {health}")
            
            # 문서 목록 조회
            docs = await client.list_documents()
            print(f"Documents: {len(docs.get('documents', []))} files")
            
        except AutoDocServiceError as e:
            print(f"AutoDoc 클라이언트 테스트 실패: {e}")


if __name__ == "__main__":
    # 테스트 실행
    asyncio.run(test_autodoc_client())