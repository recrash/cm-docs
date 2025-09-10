"""
v2 API 메인 라우터
모든 v2 엔드포인트를 통합하는 라우터
"""

from fastapi import APIRouter, WebSocket
from . import scenario_v2, full_generation
from .progress_websocket import handle_v2_websocket
from .full_generation_websocket import handle_full_generation_websocket

# v2 메인 라우터 생성
v2_router = APIRouter(prefix="/v2", tags=["V2 API"])

# 시나리오 생성 라우터 포함
v2_router.include_router(scenario_v2.router, prefix="/scenario")

# Phase 2: 전체 문서 생성 라우터 포함
v2_router.include_router(full_generation.router, prefix="", tags=["Phase 2 Full Generation"])

# WebSocket 엔드포인트 직접 등록
@v2_router.websocket("/ws/progress/{client_id}")
async def websocket_progress_endpoint(websocket: WebSocket, client_id: str):
    """
    v2 진행 상황 WebSocket 엔드포인트
    
    Args:
        websocket: WebSocket 연결 객체
        client_id: 클라이언트 식별자
    """
    await handle_v2_websocket(websocket, client_id)


# Phase 2: 전체 문서 생성 WebSocket 엔드포인트
@v2_router.websocket("/ws/full-generation/{session_id}")
async def websocket_full_generation_endpoint(websocket: WebSocket, session_id: str):
    """
    Phase 2: 전체 문서 생성 진행 상황 WebSocket 엔드포인트
    
    Args:
        websocket: WebSocket 연결 객체
        session_id: 세션 식별자
    """
    await handle_full_generation_websocket(websocket, session_id)