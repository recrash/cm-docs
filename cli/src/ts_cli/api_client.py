"""
API 클라이언트 모듈

TestscenarioMaker API 서버와의 HTTP 통신을 담당합니다.
"""

import json
import asyncio
import websockets
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from urllib.parse import urljoin

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from .utils.logger import get_logger
from .utils.config_loader import get_api_config


class APIError(Exception):
    """API 관련 오류를 나타내는 예외 클래스"""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        APIError 초기화

        Args:
            message: 오류 메시지
            status_code: HTTP 상태 코드
            response_data: 응답 데이터
        """
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """오류 메시지 포맷팅"""
        if self.status_code:
            return f"API 오류 ({self.status_code}): {self.message}"
        return f"API 오류: {self.message}"


class NetworkError(APIError):
    """네트워크 관련 오류"""

    pass


class AuthenticationError(APIError):
    """인증 관련 오류"""

    pass


class ValidationError(APIError):
    """데이터 검증 오류"""

    pass


class APIClient:
    """
    TestscenarioMaker API 클라이언트

    httpx를 사용한 비동기 HTTP 클라이언트입니다.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        APIClient 초기화

        Args:
            config: API 설정 (None이면 기본 설정 사용)
        """
        self.config = config or get_api_config()
        self.logger = get_logger(f"{__package__}.{self.__class__.__name__}")

        # HTTP 클라이언트 설정
        self.client = httpx.AsyncClient(
            base_url=self.config["base_url"],
            timeout=httpx.Timeout(self.config["timeout"]),
            headers={
                "User-Agent": f"TestscenarioMaker-CLI/1.0.0",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

    async def __aenter__(self) -> "APIClient":
        """비동기 컨텍스트 매니저 진입"""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """비동기 컨텍스트 매니저 종료"""
        await self.client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException, NetworkError)),
    )
    async def send_analysis_v2(
        self,
        repo_path: str,
        client_id: Optional[str] = None,
        use_performance_mode: bool = True,
        is_valid_repo: bool = True,
        vcs_type: str = "git",
        changes_text: str = "",
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> Dict[str, Any]:
        """
        v2 API로 시나리오 생성 요청을 전송

        Args:
            repo_path: 저장소 경로
            client_id: 클라이언트 ID (None이면 자동 생성)
            use_performance_mode: 성능 모드 사용 여부
            is_valid_repo: 저장소 유효성 검증 결과
            vcs_type: VCS 타입 (git 또는 svn)
            changes_text: CLI에서 분석한 변경사항 텍스트
            progress_callback: 진행 상황 콜백 함수 (message, progress)

        Returns:
            API 응답 데이터 (client_id, websocket_url 포함)

        Raises:
            APIError: API 호출 실패시
        """
        try:
            # 클라이언트 ID 생성
            if not client_id:
                import uuid
                client_id = f"ts_cli_{uuid.uuid4().hex[:8]}"

            self.logger.info(f"v2 API로 시나리오 생성 요청 시작 - client_id: {client_id}, vcs_type: {vcs_type}")

            if progress_callback:
                progress_callback("API 요청 준비 중...", 10)

            # v2 API 스펙에 맞는 요청 데이터 준비
            request_data = {
                "client_id": client_id,
                "repo_path": repo_path,
                "use_performance_mode": use_performance_mode,
                "is_valid_repo": is_valid_repo,
                "vcs_type": vcs_type,
                "changes_text": changes_text
            }

            if progress_callback:
                progress_callback("서버로 요청 전송 중...", 30)

            # v2 API 엔드포인트로 요청
            response = await self.client.post("/api/webservice/v2/scenario/generate", json=request_data)

            if progress_callback:
                progress_callback("응답 처리 중...", 70)

            # 응답 처리
            await self._handle_response(response)
            response_data: Dict[str, Any] = response.json()

            if progress_callback:
                progress_callback("v2 API 요청 완료", 100)

            self.logger.info(
                f"v2 API 요청 완료 - client_id: {client_id}, websocket_url: {response_data.get('websocket_url')}"
            )
            return response_data

        except httpx.NetworkError as e:
            error_msg = "네트워크 연결 오류가 발생했습니다. 인터넷 연결을 확인해주세요."
            self.logger.error(f"네트워크 오류: {e}")
            raise NetworkError(error_msg) from e

        except httpx.TimeoutException as e:
            error_msg = f"요청 시간이 초과되었습니다 ({self.config['timeout']}초)"
            self.logger.error(f"타임아웃: {e}")
            raise APIError(error_msg) from e

        except Exception as e:
            self.logger.error(f"v2 API 요청 중 오류: {e}")
            raise APIError(f"예상치 못한 오류가 발생했습니다: {str(e)}") from e

    async def listen_to_progress_v2(
        self,
        websocket_url: str,
        progress_callback: Optional[Callable[[str, str, int, Optional[Dict[str, Any]]], None]] = None,
        timeout: int = 600,
    ) -> Dict[str, Any]:
        """
        v2 API WebSocket으로부터 진행 상황을 수신

        Args:
            websocket_url: WebSocket URL
            progress_callback: 진행 상황 콜백 함수 (status, message, progress, result)
            timeout: 타임아웃 (초)

        Returns:
            최종 결과 데이터

        Raises:
            APIError: WebSocket 연결 실패시
        """
        try:
            self.logger.info(f"WebSocket 연결 시작: {websocket_url}")

            # timeout을 connect_timeout으로 변경 (websockets 라이브러리 호환성)
            import websockets.client
            timeout_config = websockets.client.WebSocketClientProtocol
            
            # Context7 FastAPI WebSocket RPC 패턴: 안정적인 연결 설정
            async with websockets.connect(
                websocket_url,
                open_timeout=30,     # 연결 대기 시간
                close_timeout=10,    # 종료 대기 시간
                ping_timeout=30,     # ping 대기 시간 증가
                ping_interval=15     # Context7 패턴: 15초 간격 ping
            ) as websocket:
                self.logger.info("WebSocket 연결 완료")

                while True:
                    try:
                        # Context7 FastAPI WebSocket RPC 패턴: 장기간 대기 가능하도록 timeout 증가
                        message = await asyncio.wait_for(websocket.recv(), timeout=60)
                        
                        # JSON 파싱
                        try:
                            progress_data = json.loads(message)
                        except json.JSONDecodeError:
                            self.logger.error(f"JSON 파싱 실패: {message}")
                            continue
                        
                        if not progress_data:
                            self.logger.warning("빈 진행 상황 데이터 수신")
                            continue
                        
                        # Context7 패턴: 시스템 메시지 필터링
                        details = progress_data.get("details", {})
                        is_system_message = (
                            progress_data.get("status") == "keepalive" or
                            progress_data.get("progress") == -1 or
                            (isinstance(details, dict) and details.get("type") in ["ping", "keepalive"])
                        )
                        
                        if is_system_message:
                            self.logger.debug("시스템 메시지 필터링됨")
                            continue
                            
                        status = progress_data.get("status", "")
                        message_text = progress_data.get("message", "")
                        progress_value = progress_data.get("progress", 0)
                        
                        # details가 dict인지 확인하고 result 추출
                        details = progress_data.get("details", {})
                        result = None
                        if isinstance(details, dict):
                            result = details.get("result")

                        self.logger.debug(f"진행 상황 수신: {status} - {message_text} ({progress_value}%)")

                        # 콜백 함수 호출
                        if progress_callback:
                            progress_callback(status, message_text, progress_value, result)

                        # 완료 상태 확인
                        if status == "COMPLETED":
                            self.logger.info("시나리오 생성 완료")
                            if result:
                                return result
                            # details에서 result를 찾거나 전체 details 반환
                            details = progress_data.get("details", {})
                            if isinstance(details, dict) and "result" in details:
                                return details["result"]
                            return details

                        # 오류 상태 확인
                        if status == "ERROR":
                            error_message = message_text or "시나리오 생성 중 오류가 발생했습니다."
                            raise APIError(error_message)

                    except asyncio.TimeoutError:
                        self.logger.debug("WebSocket 메시지 수신 대기 중...")
                        # 타임아웃이 발생해도 계속 대기
                        continue

                    except json.JSONDecodeError as e:
                        self.logger.error(f"WebSocket 메시지 파싱 오류: {e}")
                        continue

        except websockets.exceptions.WebSocketException as e:
            self.logger.error(f"WebSocket 연결 오류: {e}")
            raise APIError(f"WebSocket 연결 실패: {str(e)}") from e

        except Exception as e:
            self.logger.error(f"WebSocket 통신 중 오류: {e}")
            raise APIError(f"WebSocket 통신 실패: {str(e)}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException)),
    )
    async def get_analysis_status(self, analysis_id: str) -> Dict[str, Any]:
        """
        분석 상태 조회

        Args:
            analysis_id: 분석 ID

        Returns:
            분석 상태 정보

        Raises:
            APIError: API 호출 실패시
        """
        try:
            self.logger.info(f"분석 상태 조회: {analysis_id}")

            response = await self.client.get(f"/api/v1/analysis/{analysis_id}/status")
            await self._handle_response(response)

            response_data: Dict[str, Any] = response.json()
            self.logger.info(f"분석 상태: {response_data.get('status')}")

            return response_data

        except httpx.NetworkError as e:
            error_msg = "네트워크 연결 오류가 발생했습니다."
            self.logger.error(f"네트워크 오류: {e}")
            raise NetworkError(error_msg) from e

        except Exception as e:
            self.logger.error(f"분석 상태 조회 중 오류: {e}")
            raise APIError(f"분석 상태 조회 실패: {str(e)}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException)),
    )
    async def download_result(
        self,
        result_url: str,
        download_path: Optional[Path] = None,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> Optional[Path]:
        """
        결과 파일 다운로드

        Args:
            result_url: 결과 파일 URL
            download_path: 다운로드 경로 (None이면 자동 생성)
            progress_callback: 진행 상황 콜백 함수

        Returns:
            다운로드된 파일 경로 또는 None

        Raises:
            APIError: 다운로드 실패시
        """
        try:
            self.logger.info(f"결과 파일 다운로드 시작: {result_url}")

            if progress_callback:
                progress_callback(10)

            # 다운로드 경로 설정
            if download_path is None:
                download_path = (
                    Path.cwd() / f"testscenario_result_{self._get_timestamp()}.zip"
                )

            # 디렉토리 생성
            download_path.parent.mkdir(parents=True, exist_ok=True)

            if progress_callback:
                progress_callback(20)

            # 파일 다운로드
            async with self.client.stream("GET", result_url) as response:
                await self._handle_response(response)

                total_size = int(response.headers.get("content-length", 0))
                downloaded_size = 0

                with open(download_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
                        downloaded_size += len(chunk)

                        if progress_callback and total_size > 0:
                            progress = 20 + int((downloaded_size / total_size) * 70)
                            progress_callback(min(progress, 90))

            if progress_callback:
                progress_callback(100)

            self.logger.info(f"결과 파일 다운로드 완료: {download_path}")
            return download_path

        except httpx.NetworkError as e:
            error_msg = "네트워크 연결 오류가 발생했습니다."
            self.logger.error(f"네트워크 오류: {e}")
            raise NetworkError(error_msg) from e

        except Exception as e:
            self.logger.error(f"결과 파일 다운로드 중 오류: {e}")
            raise APIError(f"결과 파일 다운로드 실패: {str(e)}") from e

    async def _handle_response(self, response: httpx.Response) -> None:
        """
        HTTP 응답 처리

        Args:
            response: HTTP 응답

        Raises:
            APIError: 응답 처리 실패시
        """
        if response.is_success:
            return

        # 응답 본문 파싱 시도
        try:
            error_data = response.json()
            error_message = error_data.get(
                "message", f"HTTP {response.status_code} 오류"
            )
        except (json.JSONDecodeError, ValueError):
            error_message = f"HTTP {response.status_code} 오류"
            error_data = {}

        # 상태 코드별 예외 처리
        if response.status_code == 400:
            raise ValidationError(error_message, response.status_code, error_data)
        elif response.status_code == 401:
            raise AuthenticationError(
                "인증이 필요합니다. API 키를 확인해주세요.",
                response.status_code,
                error_data,
            )
        elif response.status_code == 403:
            raise AuthenticationError(
                "접근 권한이 없습니다.", response.status_code, error_data
            )
        elif response.status_code == 404:
            raise APIError(
                "요청한 리소스를 찾을 수 없습니다.", response.status_code, error_data
            )
        elif response.status_code >= 500:
            raise APIError(
                "서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                response.status_code,
                error_data,
            )
        else:
            raise APIError(error_message, response.status_code, error_data)

    def _get_timestamp(self) -> str:
        """현재 타임스탬프 반환 (파일명용)"""
        from datetime import datetime

        return datetime.now().strftime("%Y%m%d_%H%M%S")

    async def health_check(self) -> bool:
        """
        API 서버 상태 확인

        Returns:
            서버 상태 (True: 정상, False: 비정상)
        """
        try:
            response = await self.client.get("/api/webservice/health")  # 변경된 API 경로
            return response.is_success

        except Exception as e:
            self.logger.warning(f"서버 상태 확인 실패: {e}")
            return False

    async def start_full_generation(
        self, 
        session_id: str, 
        vcs_analysis_text: str, 
        metadata_json: dict
    ) -> dict:
        """
        전체 문서 생성 요청 (Phase 2 신규 API)
        
        Args:
            session_id: WebSocket 세션 ID
            vcs_analysis_text: Git/SVN 저장소 분석 결과 텍스트
            metadata_json: HTML에서 파싱된 메타데이터 JSON
            
        Returns:
            API 응답 JSON
            
        Raises:
            APIError: API 요청 실패 시
        """
        try:
            self.logger.info(f"전체 문서 생성 API 호출 시작: session_id={session_id}")
            
            # 요청 데이터 구성
            request_data = {
                "session_id": session_id,
                "vcs_analysis_text": vcs_analysis_text,
                "metadata_json": metadata_json
            }
            
            # v2 오케스트레이션 API 호출
            endpoint = "/api/webservice/v2/start-full-generation"
            response = await self.client.post(endpoint, json=request_data, timeout=60.0)
            
            # 응답 처리 (_handle_response 사용)
            await self._handle_response(response)
            result = response.json()
            self.logger.info(f"전체 문서 생성 API 호출 성공: session_id={session_id}")
            return result
                
        except Exception as e:
            self.logger.error(f"전체 문서 생성 API 호출 실패: session_id={session_id}, error={str(e)}")
            if isinstance(e, APIError):
                raise
            raise APIError(f"전체 문서 생성 API 요청 중 오류: {str(e)}")

    async def get_session_metadata(self, session_id: str) -> Optional[dict]:
        """
        세션 메타데이터 조회
        
        Args:
            session_id: 세션 ID
            
        Returns:
            세션 메타데이터 딕셔너리 또는 None
            
        Raises:
            APIError: API 요청 실패 시
        """
        try:
            self.logger.info(f"세션 메타데이터 조회: session_id={session_id}")
            
            # 세션 메타데이터 조회 API 호출
            endpoint = f"/api/webservice/v2/session/{session_id}/metadata"
            response = await self.client.get(endpoint, timeout=30.0)
            
            # 404는 정상적인 경우 (세션이 없음)
            if response.status_code == 404:
                self.logger.info(f"세션 메타데이터 없음: session_id={session_id}")
                return None
                
            # 기타 오류 응답 처리
            await self._handle_response(response)
            result = response.json()
            
            self.logger.info(f"세션 메타데이터 조회 성공: session_id={session_id}")
            return result
                
        except APIError as e:
            # 404 오류는 None 반환
            if e.status_code == 404:
                return None
            self.logger.error(f"세션 메타데이터 조회 실패: session_id={session_id}, error={str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"세션 메타데이터 조회 중 오류: session_id={session_id}, error={str(e)}")
            raise APIError(f"세션 메타데이터 조회 요청 중 오류: {str(e)}")

    async def init_full_generation_session(self, session_id: str) -> Dict[str, Any]:
        """
        Full Generation 세션 초기화 API 호출

        Args:
            session_id: 세션 ID

        Returns:
            API 응답 JSON (session_id, websocket_url 포함)

        Raises:
            APIError: API 요청 실패 시
        """
        try:
            self.logger.info(f"Full Generation 세션 초기화 시작: session_id={session_id}")

            # 세션 초기화 API 호출
            endpoint = f"/api/webservice/v2/full-generation/init-session/{session_id}"
            response = await self.client.post(endpoint, timeout=60.0)

            # 응답 처리
            await self._handle_response(response)
            result = response.json()

            self.logger.info(f"Full Generation 세션 초기화 성공: session_id={session_id}, websocket_url={result.get('websocket_url')}")
            return result

        except Exception as e:
            self.logger.error(f"Full Generation 세션 초기화 실패: session_id={session_id}, error={str(e)}")
            if isinstance(e, APIError):
                raise
            raise APIError(f"Full Generation 세션 초기화 중 오류: {str(e)}")

    async def listen_to_full_generation_progress(
        self,
        websocket_url: str,
        progress_callback: Optional[Callable[[str, str, int, Optional[Dict[str, Any]]], None]] = None,
        timeout: int = 1800,
    ) -> Dict[str, Any]:
        """
        Full Generation WebSocket으로부터 진행 상황을 수신

        Args:
            websocket_url: WebSocket URL
            progress_callback: 진행 상황 콜백 함수 (status, message, progress, result)
            timeout: 타임아웃 (초) - Full Generation은 더 오래 걸릴 수 있어 기본 30분

        Returns:
            최종 결과 데이터

        Raises:
            APIError: WebSocket 연결 실패시
        """
        try:
            self.logger.info(f"Full Generation WebSocket 연결 시작: {websocket_url}")

            # Context7 FastAPI WebSocket RPC 패턴: 안정적인 연결 설정
            async with websockets.connect(
                websocket_url,
                open_timeout=30,     # 연결 대기 시간
                close_timeout=10,    # 종료 대기 시간
                ping_timeout=30,     # ping 대기 시간 증가
                ping_interval=15     # Context7 패턴: 15초 간격 ping
            ) as websocket:
                self.logger.info("Full Generation WebSocket 연결 완료")

                while True:
                    try:
                        # Context7 FastAPI WebSocket RPC 패턴: 장기간 대기 가능하도록 timeout 증가
                        message = await asyncio.wait_for(websocket.recv(), timeout=120)  # Full Generation은 더 긴 대기

                        # JSON 파싱
                        try:
                            progress_data = json.loads(message)
                        except json.JSONDecodeError:
                            self.logger.error(f"JSON 파싱 실패: {message}")
                            continue

                        if not progress_data:
                            self.logger.warning("빈 진행 상황 데이터 수신")
                            continue

                        # Context7 패턴: 시스템 메시지 필터링
                        details = progress_data.get("details", {})
                        is_system_message = (
                            progress_data.get("status") == "keepalive" or
                            progress_data.get("progress") == -1 or
                            (isinstance(details, dict) and details.get("type") in ["ping", "keepalive"])
                        )

                        if is_system_message:
                            self.logger.debug("시스템 메시지 필터링됨")
                            continue

                        status = progress_data.get("status", "")
                        message_text = progress_data.get("message", "")
                        progress_value = progress_data.get("progress", 0)

                        # details가 dict인지 확인하고 result 추출
                        details = progress_data.get("details", {})
                        result = None
                        if isinstance(details, dict):
                            result = details.get("result")

                        self.logger.debug(f"Full Generation 진행 상황 수신: {status} - {message_text} ({progress_value}%)")

                        # 콜백 함수 호출
                        if progress_callback:
                            progress_callback(status, message_text, progress_value, result)

                        # 완료 상태 확인
                        if status == "COMPLETED":
                            self.logger.info("Full Generation 완료")
                            if result:
                                return result
                            # details에서 result를 찾거나 전체 details 반환
                            details = progress_data.get("details", {})
                            if isinstance(details, dict) and "result" in details:
                                return details["result"]
                            return details

                        # 오류 상태 확인
                        if status == "ERROR":
                            error_message = message_text or "Full Generation 중 오류가 발생했습니다."
                            raise APIError(error_message)

                    except asyncio.TimeoutError:
                        self.logger.debug("Full Generation WebSocket 메시지 수신 대기 중...")
                        # 타임아웃이 발생해도 계속 대기
                        continue

                    except json.JSONDecodeError as e:
                        self.logger.error(f"Full Generation WebSocket 메시지 파싱 오류: {e}")
                        continue

        except websockets.exceptions.WebSocketException as e:
            self.logger.error(f"Full Generation WebSocket 연결 오류: {e}")
            raise APIError(f"Full Generation WebSocket 연결 실패: {str(e)}") from e

        except Exception as e:
            self.logger.error(f"Full Generation WebSocket 통신 중 오류: {e}")
            raise APIError(f"Full Generation WebSocket 통신 실패: {str(e)}") from e

    async def close(self) -> None:
        """클라이언트 종료"""
        await self.client.aclose()


# 편의 함수들
async def test_api_connection(config: Optional[Dict[str, Any]] = None) -> bool:
    """
    API 연결 테스트

    Args:
        config: API 설정

    Returns:
        연결 테스트 결과
    """
    async with APIClient(config) as client:
        result: bool = await client.health_check()
        return result


def test_connection_sync(config: Optional[Dict[str, Any]] = None) -> bool:
    """
    API 연결 테스트 (동기 버전)

    Args:
        config: API 설정

    Returns:
        연결 테스트 결과
    """
    return asyncio.run(test_api_connection(config))
