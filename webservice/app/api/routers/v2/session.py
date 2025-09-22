"""
세션 기반 메타데이터 관리 API
URL 길이 제한 문제 해결을 위한 임시 저장소
"""

import secrets
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
import logging

from .models import (
    SessionStatus, 
    PrepareSessionRequest, 
    PrepareSessionResponse, 
    SessionStatusResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()

# 메모리 기반 세션 저장소 (추후 Redis 전환 가능)
session_metadata_store: Dict[str, Dict[str, Any]] = {}

# 자동 정리를 위한 백그라운드 태스크 관리
cleanup_task: Optional[asyncio.Task] = None

def get_session_store():
    """세션 저장소 접근 (다른 모듈에서 사용)"""
    return session_metadata_store

async def cleanup_expired_sessions():
    """만료된 세션 자동 정리 (1시간마다 실행)"""
    while True:
        try:
            current_time = datetime.now()
            expired_sessions = []
            
            for session_id, data in session_metadata_store.items():
                created_at = data.get("created_at")
                ttl = data.get("ttl", 3600)
                
                if created_at and (current_time - created_at).total_seconds() > ttl:
                    if data.get("status") != SessionStatus.IN_PROGRESS:
                        expired_sessions.append(session_id)
                        data["status"] = SessionStatus.EXPIRED
            
            # 만료된 세션 삭제
            for session_id in expired_sessions:
                logger.info(f"만료된 세션 삭제: {session_id}")
                del session_metadata_store[session_id]
                
            if expired_sessions:
                logger.info(f"정리된 만료 세션 수: {len(expired_sessions)}")
                
        except Exception as e:
            logger.error(f"세션 정리 중 오류: {str(e)}")
            
        # 1시간 대기
        await asyncio.sleep(3600)

def start_cleanup_task():
    """세션 정리 백그라운드 태스크 시작"""
    global cleanup_task
    if cleanup_task is None or cleanup_task.done():
        cleanup_task = asyncio.create_task(cleanup_expired_sessions())
        logger.info("세션 자동 정리 태스크 시작됨")


@router.post("/prepare-session", response_model=PrepareSessionResponse)
async def prepare_session(
    request: PrepareSessionRequest,
    background_tasks: BackgroundTasks
):
    """
    세션 준비 - 메타데이터를 임시 저장소에 저장
    
    Args:
        request: 세션 준비 요청
        background_tasks: 백그라운드 작업 관리자
        
    Returns:
        세션 ID와 준비 상태
    """
    try:
        # 백그라운드 정리 태스크 시작 (최초 1회)
        start_cleanup_task()
        
        session_id = request.session_id
        
        # 기존 세션 확인
        if session_id and session_id in session_metadata_store:
            existing = session_metadata_store[session_id]
            current_status = existing.get("status")
            
            logger.info(f"기존 세션 발견: {session_id}, 상태: {current_status}")
            
            # 완료된 세션 재사용 정책
            if current_status == SessionStatus.COMPLETED:
                if existing.get("reusable", True):
                    logger.info(f"완료된 세션 재사용: {session_id}")
                    existing.update({
                        "metadata": request.metadata_json,
                        "html_file_path": request.html_file_path,
                        "vcs_analysis_text": request.vcs_analysis_text,
                        "status": SessionStatus.PREPARED,
                        "created_at": datetime.now(),
                        "usage_count": existing.get("usage_count", 0) + 1
                    })
                    return PrepareSessionResponse(
                        session_id=session_id,
                        status="reused",
                        message="완료된 세션을 재사용했습니다"
                    )
                else:
                    # 재사용 불가능하면 새 세션 생성
                    session_id = f"{session_id}_retry_{datetime.now().strftime('%H%M%S')}"
                    logger.info(f"새 세션 생성 (기존 완료): {session_id}")
                    
            elif current_status == SessionStatus.IN_PROGRESS:
                # 진행 중인 세션은 충돌
                raise HTTPException(
                    status_code=409,
                    detail=f"세션 {session_id}가 아직 진행 중입니다. 잠시 후 다시 시도해주세요."
                )
                
            elif current_status == SessionStatus.FAILED:
                # 실패한 세션 재시도 정책
                retry_count = existing.get("retry_count", 0)
                max_retries = 3
                
                if retry_count < max_retries:
                    logger.info(f"실패한 세션 재시도 {retry_count+1}/{max_retries}: {session_id}")
                    existing.update({
                        "metadata": request.metadata_json,
                        "html_file_path": request.html_file_path,
                        "vcs_analysis_text": request.vcs_analysis_text,
                        "status": SessionStatus.PREPARED,
                        "retry_count": retry_count,
                        "previous_errors": existing.get("previous_errors", []) + [existing.get("last_error")]
                    })
                    return PrepareSessionResponse(
                        session_id=session_id,
                        status="retry",
                        retry_attempt=retry_count + 1,
                        max_retries=max_retries,
                        message=f"실패한 세션을 재시도합니다 ({retry_count+1}/{max_retries})"
                    )
                else:
                    # 재시도 한계 초과 - 새 세션 생성
                    new_session_id = f"{session_id}_new_{datetime.now().strftime('%H%M%S')}"
                    logger.warning(f"재시도 한계 초과, 새 세션 생성: {new_session_id}")
                    session_id = new_session_id
                    
            elif current_status == SessionStatus.EXPIRED:
                # 만료된 세션은 재활용
                logger.info(f"만료된 세션 재활용: {session_id}")
                existing.update({
                    "metadata": request.metadata_json,
                    "html_file_path": request.html_file_path,
                    "vcs_analysis_text": request.vcs_analysis_text,
                    "status": SessionStatus.PREPARED,
                    "created_at": datetime.now(),
                    "usage_count": 0,
                    "retry_count": 0
                })
                return PrepareSessionResponse(
                    session_id=session_id,
                    status="recycled",
                    message="만료된 세션을 재활용했습니다"
                )
        
        # 새 세션 생성
        if not session_id:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(4)}"
            
        logger.info(f"새 세션 생성: {session_id}")
        
        # 세션 데이터 저장
        session_metadata_store[session_id] = {
            "metadata": request.metadata_json,
            "html_file_path": request.html_file_path,
            "vcs_analysis_text": request.vcs_analysis_text,
            "status": SessionStatus.PREPARED,
            "created_at": datetime.now(),
            "completed_at": None,
            "failed_at": None,
            "ttl": 3600,  # 1시간
            "reusable": True,
            "usage_count": 0,
            "retry_count": 0,
            "last_error": None,
            "previous_errors": []
        }
        
        return PrepareSessionResponse(
            session_id=session_id,
            status="created",
            message="새 세션이 생성되었습니다"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("세션 준비 중 예상치 못한 오류")
        raise HTTPException(
            status_code=500,
            detail=f"세션 준비 중 오류가 발생했습니다: {str(e)}"
        )

@router.get("/session/{session_id}/metadata")
async def get_session_metadata(session_id: str):
    """
    세션 메타데이터 조회
    
    Args:
        session_id: 세션 ID
        
    Returns:
        저장된 메타데이터
    """
    try:
        if session_id not in session_metadata_store:
            logger.warning(f"세션을 찾을 수 없음: {session_id}")
            raise HTTPException(
                status_code=404,
                detail=f"세션 {session_id}를 찾을 수 없습니다"
            )
        
        session_data = session_metadata_store[session_id]
        
        # 만료 확인
        created_at = session_data.get("created_at")
        ttl = session_data.get("ttl", 3600)
        if created_at and (datetime.now() - created_at).total_seconds() > ttl:
            logger.warning(f"만료된 세션 접근: {session_id}")
            session_data["status"] = SessionStatus.EXPIRED
            raise HTTPException(
                status_code=410,
                detail=f"세션 {session_id}가 만료되었습니다"
            )
        
        logger.info(f"세션 메타데이터 조회 성공: {session_id}")
        return session_data.get("metadata", {})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("세션 메타데이터 조회 중 오류")
        raise HTTPException(
            status_code=500,
            detail=f"세션 메타데이터 조회 중 오류: {str(e)}"
        )

@router.get("/session/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(session_id: str):
    """
    세션 상태 및 에러 정보 조회 (디버깅용)
    
    Args:
        session_id: 세션 ID
        
    Returns:
        세션 상태 정보
    """
    try:
        if session_id not in session_metadata_store:
            raise HTTPException(
                status_code=404,
                detail=f"세션 {session_id}를 찾을 수 없습니다"
            )
        
        session = session_metadata_store[session_id]
        
        return SessionStatusResponse(
            session_id=session_id,
            status=session.get("status", SessionStatus.PREPARED),
            created_at=session.get("created_at"),
            completed_at=session.get("completed_at"),
            failed_at=session.get("failed_at"),
            retry_count=session.get("retry_count", 0),
            usage_count=session.get("usage_count", 0),
            last_error=session.get("last_error"),
            previous_errors=session.get("previous_errors", [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("세션 상태 조회 중 오류")
        raise HTTPException(
            status_code=500,
            detail=f"세션 상태 조회 중 오류: {str(e)}"
        )

@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    세션 삭제
    
    Args:
        session_id: 세션 ID
        
    Returns:
        삭제 성공 메시지
    """
    try:
        if session_id not in session_metadata_store:
            raise HTTPException(
                status_code=404,
                detail=f"세션 {session_id}를 찾을 수 없습니다"
            )
        
        del session_metadata_store[session_id]
        logger.info(f"세션 삭제됨: {session_id}")
        
        return {"message": f"세션 {session_id}가 삭제되었습니다"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("세션 삭제 중 오류")
        raise HTTPException(
            status_code=500,
            detail=f"세션 삭제 중 오류: {str(e)}"
        )

@router.get("/sessions/stats")
async def get_sessions_stats():
    """
    세션 통계 조회 (모니터링용)
    
    Returns:
        세션 통계 정보
    """
    try:
        total_sessions = len(session_metadata_store)
        status_counts = {}
        
        for session_data in session_metadata_store.values():
            status = session_data.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total_sessions": total_sessions,
            "status_counts": status_counts,
            "cleanup_task_running": cleanup_task is not None and not cleanup_task.done()
        }
        
    except Exception as e:
        logger.exception("세션 통계 조회 중 오류")
        raise HTTPException(
            status_code=500,
            detail=f"세션 통계 조회 중 오류: {str(e)}"
        )

def update_session_status(session_id: str, status: SessionStatus, **kwargs):
    """
    세션 상태 업데이트 (다른 모듈에서 사용)
    
    Args:
        session_id: 세션 ID
        status: 새로운 상태
        **kwargs: 추가 업데이트 정보
    """
    if session_id in session_metadata_store:
        session_metadata_store[session_id]["status"] = status
        
        if status == SessionStatus.COMPLETED:
            session_metadata_store[session_id]["completed_at"] = datetime.now()
        elif status == SessionStatus.FAILED:
            session_metadata_store[session_id]["failed_at"] = datetime.now()
            if "error_message" in kwargs:
                session_metadata_store[session_id]["last_error"] = {
                    "message": kwargs["error_message"],
                    "timestamp": datetime.now().isoformat()
                }
        
        # 추가 정보 업데이트
        for key, value in kwargs.items():
            if key != "error_message":  # 이미 처리됨
                session_metadata_store[session_id][key] = value
                
        logger.info(f"세션 상태 업데이트: {session_id} -> {status}")