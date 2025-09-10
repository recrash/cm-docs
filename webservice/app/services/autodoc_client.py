"""
AutoDoc Service 클라이언트

Phase 2: Webservice에서 autodoc_service로 문서 생성 요청을 보내는 클라이언트
"""

import asyncio
import httpx
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class AutoDocServiceError(Exception):
    """AutoDoc Service 호출 관련 오류"""
    pass


class AutoDocClient:
    """AutoDoc Service HTTP 클라이언트"""
    
    def __init__(self, base_url: str = "http://localhost:8001", timeout: float = 30.0):
        """
        Args:
            base_url: autodoc_service 서버 URL
            timeout: HTTP 요청 타임아웃 (초)
        """
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
    
    async def build_cm_word(self, change_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Word 문서 생성 요청
        
        Args:
            change_request: 변경 요청 데이터
            
        Returns:
            생성 결과 (파일명 포함)
        """
        if not self.client:
            raise AutoDocServiceError("클라이언트가 초기화되지 않았습니다")
        
        try:
            logger.info(f"Word 문서 생성 요청: {change_request.get('change_id', 'N/A')}")
            
            response = await self.client.post(
                f"{self.base_url}/api/autodoc/build-cm-word",
                json=change_request
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
            change_requests: 변경 요청 데이터 목록
            
        Returns:
            생성 결과 (파일명 포함)
        """
        if not self.client:
            raise AutoDocServiceError("클라이언트가 초기화되지 않았습니다")
        
        try:
            logger.info(f"Excel 목록 생성 요청: {len(change_requests)}개 항목")
            
            response = await self.client.post(
                f"{self.base_url}/api/autodoc/build-cm-list",
                json=change_requests
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
    
    async def build_base_scenario(self, change_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        기본 시나리오 Excel 생성 요청
        
        Args:
            change_request: 변경 요청 데이터
            
        Returns:
            생성 결과 (파일명 포함)
        """
        if not self.client:
            raise AutoDocServiceError("클라이언트가 초기화되지 않았습니다")
        
        try:
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