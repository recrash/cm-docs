"""
Phase 2: 전체 문서 생성 WebSocket 핸들러

sessionId 기반의 전체 문서 생성 진행 상황을 실시간으로 전송
"""

import asyncio
import json
import logging
from typing import Dict, Set

from fastapi import WebSocket, WebSocketDisconnect
from .models import FullGenerationProgressMessage, FullGenerationStatus
from .full_generation import generation_sessions

logger = logging.getLogger(__name__)

# 연결된 WebSocket 클라이언트들 (session_id -> WebSocket)
connected_clients: Dict[str, Set[WebSocket]] = {}


async def handle_full_generation_websocket(websocket: WebSocket, session_id: str):
    """
    전체 문서 생성 WebSocket 연결 핸들러
    
    Args:
        websocket: WebSocket 연결 객체
        session_id: 세션 ID
    """
    await websocket.accept()
    
    # 클라이언트 연결 등록
    if session_id not in connected_clients:
        connected_clients[session_id] = set()
    connected_clients[session_id].add(websocket)
    
    logger.info(f"전체 문서 생성 WebSocket 클라이언트 연결: session_id={session_id}")
    
    try:
        # 현재 상태 즉시 전송
        if session_id in generation_sessions:
            await send_current_status(websocket, session_id)
        
        # 주기적으로 상태 업데이트 전송
        while True:
            if session_id in generation_sessions:
                session = generation_sessions[session_id]
                
                # 완료 또는 오류 상태면 최종 메시지 전송 후 종료
                if session["status"] in [FullGenerationStatus.COMPLETED, FullGenerationStatus.ERROR]:
                    await send_current_status(websocket, session_id)
                    break
                
                await send_current_status(websocket, session_id)
            
            await asyncio.sleep(2)  # 2초마다 상태 확인
    
    except WebSocketDisconnect:
        logger.info(f"전체 문서 생성 WebSocket 클라이언트 연결 해제: session_id={session_id}")
    except Exception as e:
        logger.error(f"전체 문서 생성 WebSocket 오류: {e}")
    finally:
        # 연결 정리
        if session_id in connected_clients:
            connected_clients[session_id].discard(websocket)
            if not connected_clients[session_id]:  # 빈 set이면 제거
                del connected_clients[session_id]


async def send_current_status(websocket: WebSocket, session_id: str):
    """
    현재 상태를 WebSocket으로 전송
    
    Args:
        websocket: WebSocket 연결 객체
        session_id: 세션 ID
    """
    if session_id not in generation_sessions:
        return
    
    session = generation_sessions[session_id]
    progress = (session["steps_completed"] / session["total_steps"]) * 100
    
    message = FullGenerationProgressMessage(
        session_id=session_id,
        status=session["status"],
        message=get_status_message(session["status"]),
        progress=progress,
        current_step=session["current_step"],
        steps_completed=session["steps_completed"],
        total_steps=session["total_steps"],
        details={
            "started_at": session.get("started_at", "").isoformat() if session.get("started_at") else "",
            "results": session.get("results", {}),
            "errors": session.get("errors", []),
            "warnings": session.get("warnings", [])
        },
        result=None  # 완료 시에만 설정
    )
    
    # 완료 시 결과 데이터 포함
    if session["status"] == FullGenerationStatus.COMPLETED:
        from .models import FullGenerationResultData
        message.result = FullGenerationResultData(
            session_id=session_id,
            word_filename=session["results"].get("word_filename"),
            excel_list_filename=session["results"].get("excel_list_filename"),
            base_scenario_filename=session["results"].get("base_scenario_filename"),
            merged_excel_filename=session["results"].get("merged_excel_filename"),
            download_urls=generate_download_urls(session["results"]),
            generation_time=(
                (session.get("completed_at", session.get("started_at")) - 
                 session.get("started_at")).total_seconds() 
                if session.get("completed_at") and session.get("started_at") else 0.0
            ),
            steps_completed=session["steps_completed"],
            total_steps=session["total_steps"],
            errors=session.get("errors", []),
            warnings=session.get("warnings", [])
        )
    
    try:
        await websocket.send_text(message.json())
    except Exception as e:
        logger.error(f"WebSocket 메시지 전송 실패: {e}")


def get_status_message(status: FullGenerationStatus) -> str:
    """
    상태에 따른 한글 메시지 반환
    
    Args:
        status: 생성 상태
        
    Returns:
        한글 상태 메시지
    """
    status_messages = {
        FullGenerationStatus.RECEIVED: "요청을 수신했습니다",
        FullGenerationStatus.ANALYZING_VCS: "VCS 변경사항을 분석하고 있습니다",
        FullGenerationStatus.GENERATING_SCENARIOS: "테스트 시나리오를 생성하고 있습니다",
        FullGenerationStatus.GENERATING_WORD_DOC: "Word 문서를 생성하고 있습니다",
        FullGenerationStatus.GENERATING_EXCEL_LIST: "Excel 목록을 생성하고 있습니다",
        FullGenerationStatus.GENERATING_BASE_SCENARIOS: "기본 시나리오를 생성하고 있습니다",
        FullGenerationStatus.MERGING_EXCEL: "Excel 파일을 병합하고 있습니다",
        FullGenerationStatus.COMPLETED: "모든 문서 생성이 완료되었습니다",
        FullGenerationStatus.ERROR: "문서 생성 중 오류가 발생했습니다"
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
    
    return download_urls


async def broadcast_to_session(session_id: str, message: FullGenerationProgressMessage):
    """
    특정 세션의 모든 클라이언트에게 메시지 브로드캐스트
    
    Args:
        session_id: 세션 ID
        message: 전송할 메시지
    """
    if session_id not in connected_clients:
        return
    
    # 연결이 끊어진 클라이언트들 제거
    disconnected_clients = set()
    
    for websocket in connected_clients[session_id].copy():
        try:
            await websocket.send_text(message.json())
        except Exception as e:
            logger.warning(f"WebSocket 브로드캐스트 실패: {e}")
            disconnected_clients.add(websocket)
    
    # 끊어진 연결들 정리
    for websocket in disconnected_clients:
        connected_clients[session_id].discard(websocket)
    
    if not connected_clients[session_id]:
        del connected_clients[session_id]


def get_connected_clients_count(session_id: str) -> int:
    """
    특정 세션의 연결된 클라이언트 수 반환
    
    Args:
        session_id: 세션 ID
        
    Returns:
        연결된 클라이언트 수
    """
    return len(connected_clients.get(session_id, set()))


def get_all_connected_sessions() -> Dict[str, int]:
    """
    모든 연결된 세션과 클라이언트 수 반환
    
    Returns:
        세션별 클라이언트 수 딕셔너리
    """
    return {session_id: len(clients) for session_id, clients in connected_clients.items()}