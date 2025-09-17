"""
Phase 2: 전체 문서 생성 WebSocket 핸들러

sessionId 기반의 전체 문서 생성 진행 상황을 실시간으로 전송
기존 V2ProgressWebSocket과 동일한 패턴으로 구현
"""

import asyncio
import json
import logging
import time
from typing import Dict
from websockets.exceptions import ConnectionClosedError

from fastapi import WebSocket, WebSocketDisconnect
from .models import FullGenerationProgressMessage

logger = logging.getLogger(__name__)


class FullGenerationConnectionManager:
    """Full Generation WebSocket 연결 관리자 (V2ConnectionManager 패턴 복사)"""

    def __init__(self):
        # 세션별 WebSocket 연결 저장
        self.connections: Dict[str, WebSocket] = {}
        # 연결 정리를 위한 락
        self._lock = asyncio.Lock()

    async def connect(self, session_id: str, websocket: WebSocket):
        """새로운 WebSocket 연결 등록"""
        try:
            await websocket.accept()

            async with self._lock:
                # 기존 연결이 있다면 정리
                if session_id in self.connections:
                    old_ws = self.connections[session_id]
                    try:
                        await old_ws.close()
                        logger.info(f"기존 연결을 정리했습니다: {session_id}")
                    except:
                        pass

                # 새 연결 등록
                self.connections[session_id] = websocket
                logger.info(f"Full Generation WebSocket 연결 등록: {session_id}")

                # 연결 확인 메시지 전송
                welcome_msg = FullGenerationProgressMessage(
                    session_id=session_id,
                    status="received",
                    message="WebSocket 연결이 설정되었습니다.",
                    progress=0,
                    current_step="연결 설정",
                    steps_completed=0,
                    total_steps=4,
                    details={},
                    result=None
                )
                await self.send_progress(session_id, welcome_msg)

        except Exception as e:
            logger.error(f"Full Generation WebSocket 연결 설정 실패 {session_id}: {e}")
            raise

    async def disconnect(self, session_id: str):
        """WebSocket 연결 정리"""
        async with self._lock:
            if session_id in self.connections:
                try:
                    websocket = self.connections[session_id]
                    await websocket.close()
                except:
                    pass
                finally:
                    del self.connections[session_id]
                    logger.info(f"Full Generation WebSocket 연결 정리: {session_id}")

    def is_connected(self, session_id: str) -> bool:
        """특정 세션의 연결 상태 확인"""
        return session_id in self.connections

    async def send_progress(self, session_id: str, progress: FullGenerationProgressMessage):
        """특정 세션에게 진행 상황 메시지 전송"""
        if session_id not in self.connections:
            logger.warning(f"연결되지 않은 세션에게 메시지 전송 시도: {session_id}")
            return False

        websocket = self.connections[session_id]

        try:
            # Pydantic 모델을 JSON으로 직렬화
            message_dict = progress.model_dump()
            message_json = json.dumps(message_dict, ensure_ascii=False)

            await websocket.send_text(message_json)
            logger.debug(f"Full Generation 진행 상황 전송 완료 {session_id}: {progress.status} ({progress.progress}%)")
            return True

        except WebSocketDisconnect:
            logger.info(f"Full Generation 클라이언트 연결 끊김 감지: {session_id}")
            await self.disconnect(session_id)
            return False

        except Exception as e:
            logger.error(f"Full Generation 진행 상황 전송 실패 {session_id}: {e}")
            await self.disconnect(session_id)
            return False

    def get_connected_sessions(self) -> list:
        """현재 연결된 모든 세션 ID 반환"""
        return list(self.connections.keys())

    async def cleanup_all(self):
        """모든 연결 정리 (서버 종료 시 사용)"""
        logger.info("모든 Full Generation WebSocket 연결을 정리합니다.")

        for session_id in list(self.connections.keys()):
            await self.disconnect(session_id)

        logger.info("Full Generation WebSocket 연결 정리 완료")


# 전역 연결 관리자 인스턴스
full_generation_connection_manager = FullGenerationConnectionManager()


async def handle_full_generation_websocket(websocket: WebSocket, session_id: str):
    """
    Full Generation WebSocket 연결 핸들러 (V2 패턴 복사)

    Args:
        websocket: WebSocket 연결 객체
        session_id: 세션 식별자
    """
    logger.info(f"Full Generation WebSocket 연결 시도: {session_id}")

    try:
        # 연결 설정
        await full_generation_connection_manager.connect(session_id, websocket)

        # FastAPI WebSocket 표준 패턴: 단순 루프로 연결 유지
        while True:
            try:
                # 클라이언트 메시지 대기 (타임아웃 없이)
                data = await websocket.receive_text()
                logger.debug(f"Full Generation 클라이언트 메시지 수신 {session_id}: {data}")

                # ping 메시지에 대한 JSON 응답 (프론트엔드 호환)
                if data.strip().lower() == 'ping':
                    await websocket.send_text('{"type":"pong","timestamp":' + str(time.time()) + '}')
                    logger.debug(f"Full Generation 클라이언트 ping에 JSON pong 응답: {session_id}")
                    continue

            except WebSocketDisconnect:
                logger.info(f"Full Generation 클라이언트가 연결을 종료했습니다: {session_id}")
                break

            except Exception as e:
                logger.error(f"Full Generation WebSocket 메시지 처리 중 오류 {session_id}: {e}")
                break

    except Exception as e:
        logger.error(f"Full Generation WebSocket 연결 처리 중 오류 {session_id}: {e}")

    finally:
        # 연결 정리
        await full_generation_connection_manager.disconnect(session_id)
        logger.info(f"Full Generation WebSocket 연결 종료: {session_id}")


# 기존 함수들을 연결 관리자 방식으로 대체
# 더 이상 필요하지 않은 함수들을 제거하고, 필요한 유틸리티 함수만 남김

def get_status_message(status: str) -> str:
    """
    상태에 따른 한글 메시지 반환

    Args:
        status: 생성 상태

    Returns:
        한글 상태 메시지
    """
    status_messages = {
        "received": "요청을 수신했습니다",
        "analyzing_vcs": "VCS 변경사항을 분석하고 있습니다",
        "generating_scenarios": "테스트 시나리오를 생성하고 있습니다",
        "generating_word_doc": "Word 문서를 생성하고 있습니다",
        "generating_excel_list": "Excel 목록을 생성하고 있습니다",
        "generating_base_scenarios": "기본 시나리오를 생성하고 있습니다",
        "merging_excel": "Excel 파일을 병합하고 있습니다",
        "completed": "모든 문서 생성이 완료되었습니다",
        "error": "문서 생성 중 오류가 발생했습니다"
    }
    return status_messages.get(status, "알 수 없는 상태")


def generate_download_urls(results: Dict[str, str]) -> Dict[str, str]:
    """
    생성된 파일들의 다운로드 URL 생성

    Args:
        results: 생성 결과 딕셔너리

    Returns:
        다운로드 URL 딕셔너리
    """
    download_urls = {}

    # webservice outputs 파일들
    webservice_base = "/api/webservice/download"
    if results.get("scenario_filename"):
        download_urls["scenario"] = f"{webservice_base}/{results['scenario_filename']}"

    # autodoc_service documents 파일들
    autodoc_base = "/api/autodoc/download"
    if results.get("word_filename"):
        download_urls["word"] = f"{autodoc_base}/{results['word_filename']}"
    if results.get("excel_list_filename"):
        download_urls["excel_list"] = f"{autodoc_base}/{results['excel_list_filename']}"
    if results.get("base_scenario_filename"):
        download_urls["base_scenario"] = f"{autodoc_base}/{results['base_scenario_filename']}"
    if results.get("merged_excel_filename"):
        download_urls["merged_excel"] = f"{autodoc_base}/{results['merged_excel_filename']}"
    if results.get("integrated_scenario_filename"):  # 새로운 통합 시나리오
        download_urls["integrated_scenario"] = f"{autodoc_base}/{results['integrated_scenario_filename']}"

    return download_urls