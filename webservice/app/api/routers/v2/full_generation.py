"""
Phase 2: 전체 문서 생성 API

CLI에서 sessionId와 metadata를 포함한 요청을 받아서
모든 문서를 생성하고 병합하는 오케스트레이션 API
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse

from .models import (
    FullGenerationRequest, 
    FullGenerationResponse, 
    FullGenerationStatus, 
    FullGenerationResultData,
    SessionStatus
)
from .session import get_session_store, update_session_status as session_update_status
from .full_generation_websocket import full_generation_connection_manager, get_status_message, generate_download_urls
from app.services.autodoc_client import AutoDocClient, AutoDocServiceError
from app.services.excel_merger import ExcelMerger, ExcelMergerError
from app.core.llm_handler import LLMHandler
from app.core.excel_writer import create_excel_file
from app.core.paths import get_outputs_dir

# 로거 설정
logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter()

# 전체 생성 세션 저장소 (실제로는 Redis 등을 사용해야 함)
generation_sessions: Dict[str, Dict[str, Any]] = {}


@router.post("/start-full-generation", response_model=FullGenerationResponse)
async def start_full_generation(
    request: FullGenerationRequest,
    background_tasks: BackgroundTasks
):
    """
    전체 문서 생성 시작 (Phase 2)
    
    Args:
        request: 전체 문서 생성 요청
        background_tasks: 백그라운드 작업 관리자
        
    Returns:
        생성 시작 응답
    """
    try:
        logger.info(f"전체 문서 생성 시작: session_id={request.session_id}")
        
        # 세션 저장소에서 메타데이터 조회 시도
        session_store = get_session_store()
        if not request.metadata_json or request.metadata_json == {}:
            if request.session_id in session_store:
                stored_data = session_store[request.session_id]
                request.metadata_json = stored_data.get("metadata", {})
                logger.info(f"세션 저장소에서 메타데이터 복원: {request.session_id}")
                
                # 세션 상태를 진행 중으로 업데이트
                session_update_status(request.session_id, SessionStatus.IN_PROGRESS)
            else:
                logger.warning(f"세션 저장소에 메타데이터 없음: {request.session_id}")
        
        # 세션 초기화
        generation_sessions[request.session_id] = {
            "status": FullGenerationStatus.RECEIVED,
            "started_at": datetime.now(),
            "steps_completed": 0,
            "total_steps": 4,  # 총 4단계로 단순화 (VCS분석 → 시나리오생성 → 문서생성 → 완료)
            "current_step": "요청 수신",
            "vcs_analysis_text": request.vcs_analysis_text,
            "metadata_json": request.metadata_json,
            "results": {},
            "errors": [],
            "warnings": []
        }
        
        # 백그라운드에서 전체 문서 생성 실행
        background_tasks.add_task(
            execute_full_generation,
            request.session_id,
            request.vcs_analysis_text,
            request.metadata_json
        )

        # 초기 WebSocket 메시지 전송 (연결된 클라이언트가 있다면)
        if full_generation_connection_manager.is_connected(request.session_id):
            from .models import FullGenerationProgressMessage
            initial_msg = FullGenerationProgressMessage(
                session_id=request.session_id,
                status="received",
                message="전체 문서 생성 작업이 시작되었습니다.",
                progress=5,
                current_step="요청 수신",
                steps_completed=0,
                total_steps=4,
                details={},
                result=None
            )
            await full_generation_connection_manager.send_progress(request.session_id, initial_msg)
        
        return FullGenerationResponse(
            session_id=request.session_id,
            status="accepted",
            message="전체 문서 생성 작업이 시작되었습니다."
        )
        
    except Exception as e:
        logger.error(f"전체 문서 생성 시작 실패: {e}")
        raise HTTPException(status_code=500, detail=f"전체 문서 생성 시작 실패: {e}")


@router.post("/init-session/{session_id}")
async def init_full_generation_session(session_id: str, request: Request):
    """
    전체 문서 생성 세션 초기화 (WebSocket 연결 전 사전 등록)
    
    Args:
        session_id: 세션 ID
        
    Returns:
        세션 초기화 응답
    """
    try:
        logger.info(f"전체 문서 생성 세션 초기화: session_id={session_id}")
        
        # 세션이 이미 존재하면 기존 세션 반환
        if session_id in generation_sessions:
            logger.info(f"기존 세션 발견: {session_id}")

            # WebSocket URL 생성 (기존 세션도 동일하게)
            protocol = "wss" if request.url.scheme == "https" else "ws"
            host = request.headers.get("host", "localhost:8000")
            websocket_url = f"{protocol}://{host}/api/webservice/v2/ws/full-generation/{session_id}"

            return JSONResponse({
                "session_id": session_id,
                "status": "existing",
                "message": "기존 세션이 존재합니다.",
                "websocket_url": websocket_url
            })
        
        # 새 세션 초기화
        generation_sessions[session_id] = {
            "status": FullGenerationStatus.RECEIVED,
            "started_at": datetime.now(),
            "steps_completed": 0,
            "total_steps": 4,
            "current_step": "세션 대기 중",
            "vcs_analysis_text": "",
            "metadata_json": {},
            "results": {},
            "errors": [],
            "warnings": []
        }
        
        logger.info(f"새 세션 생성 완료: {session_id}")

        # WebSocket URL 생성 (scenario_v2.py 패턴 참조)
        protocol = "wss" if request.url.scheme == "https" else "ws"
        host = request.headers.get("host", "localhost:8000")
        websocket_url = f"{protocol}://{host}/api/webservice/v2/ws/full-generation/{session_id}"

        return JSONResponse({
            "session_id": session_id,
            "status": "initialized",
            "message": "새 세션이 생성되었습니다.",
            "websocket_url": websocket_url
        })
        
    except Exception as e:
        logger.error(f"세션 초기화 실패: {e}")
        raise HTTPException(status_code=500, detail=f"세션 초기화 실패: {e}")


@router.get("/full-generation-status/{session_id}")
async def get_full_generation_status(session_id: str):
    """
    전체 문서 생성 상태 조회
    
    Args:
        session_id: 세션 ID
        
    Returns:
        현재 생성 상태
    """
    if session_id not in generation_sessions:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
    
    session = generation_sessions[session_id]
    
    return {
        "session_id": session_id,
        "status": session["status"],
        "current_step": session["current_step"],
        "steps_completed": session["steps_completed"],
        "total_steps": session["total_steps"],
        "progress": (session["steps_completed"] / session["total_steps"]) * 100,
        "results": session.get("results", {}),
        "errors": session.get("errors", []),
        "warnings": session.get("warnings", [])
    }


async def execute_full_generation(session_id: str, vcs_analysis_text: str, metadata_json: Dict[str, Any]):
    """
    전체 문서 생성 실행 (백그라운드 작업)
    웹소켓을 통한 실시간 진행상황 전송 포함

    Args:
        session_id: 세션 ID
        vcs_analysis_text: VCS 분석 텍스트
        metadata_json: 메타데이터
    """
    session = generation_sessions[session_id]

    # 진행 상황 전송 헬퍼 함수 (V2 패턴 복사)
    async def send_progress(status: FullGenerationStatus, message: str, progress: float,
                          current_step: str, steps_completed: int, details: Optional[dict] = None,
                          result: Optional[dict] = None):
        """웹소켓으로 진행 상황 전송"""
        from .models import FullGenerationProgressMessage, FullGenerationResultData

        progress_msg = FullGenerationProgressMessage(
            session_id=session_id,
            status=status,
            message=message,
            progress=progress,
            current_step=current_step,
            steps_completed=steps_completed,
            total_steps=session["total_steps"],
            details=details or {},
            result=None  # 완료 시에만 설정
        )

        # 완료 시 결과 데이터 포함
        if status == FullGenerationStatus.COMPLETED and result:
            progress_msg.result = FullGenerationResultData(
                session_id=session_id,
                word_filename=result.get("word_filename"),
                excel_list_filename=result.get("excel_list_filename"),
                base_scenario_filename=result.get("base_scenario_filename"),
                merged_excel_filename=result.get("merged_excel_filename"),
                download_urls=generate_download_urls(result),
                generation_time=result.get("generation_time", 0.0),
                steps_completed=steps_completed,
                total_steps=session["total_steps"],
                errors=session.get("errors", []),
                warnings=session.get("warnings", [])
            )

        await full_generation_connection_manager.send_progress(session_id, progress_msg)

    try:
        logger.info(f"전체 문서 생성 실행 시작: {session_id}")

        # Step 1: VCS 분석 처리
        await send_progress(FullGenerationStatus.ANALYZING_VCS, "VCS 변경사항을 분석하고 있습니다...", 25, "VCS 분석 중", 1)
        await update_session_status(session_id, FullGenerationStatus.ANALYZING_VCS, "VCS 분석 중", 1)
        await asyncio.sleep(1)  # 시뮬레이션

        # Step 2: 시나리오 생성
        await send_progress(FullGenerationStatus.GENERATING_SCENARIOS, "테스트 시나리오를 생성하고 있습니다...", 50, "시나리오 생성 중", 2)
        await update_session_status(session_id, FullGenerationStatus.GENERATING_SCENARIOS, "시나리오 생성 중", 2)
        scenario_result = await generate_scenario_excel(vcs_analysis_text, metadata_json)
        session["results"]["scenario_filename"] = scenario_result.get("filename")
        
        # Step 3: autodoc_service 문서 2종 + 통합 시나리오 동시 생성 (성능 최적화)
        await send_progress(FullGenerationStatus.GENERATING_WORD_DOC, "Word, Excel 목록, 통합 시나리오를 동시 생성하고 있습니다...", 75, "문서 생성 중", 3)
        await update_session_status(session_id, FullGenerationStatus.GENERATING_WORD_DOC, "Word, Excel 목록, 통합 시나리오 동시 생성 중", 3)
        
        # asyncio.gather를 사용해 3개의 작업을 동시에 실행 (새로운 통합 API 사용)
        try:
            results = await asyncio.gather(
                generate_word_document(metadata_json),
                generate_excel_list([metadata_json]),
                generate_integrated_scenario(metadata_json, scenario_result.get("test_cases", [])),
                return_exceptions=True  # 작업 중 하나가 실패해도 나머지는 계속하도록
            )
            
            # 결과 처리
            word_result, excel_list_result, integrated_scenario_result = results
            
            # Word 결과 처리
            if isinstance(word_result, Exception):
                logger.error(f"Word 문서 생성 실패: {word_result}")
                session["errors"].append(f"Word 문서 생성 실패: {word_result}")
                word_result = {}  # 빈 결과로 대체
            else:
                session["results"]["word_filename"] = word_result.get("filename")
            
            # Excel 목록 결과 처리
            if isinstance(excel_list_result, Exception):
                logger.error(f"Excel 목록 생성 실패: {excel_list_result}")
                session["errors"].append(f"Excel 목록 생성 실패: {excel_list_result}")
                excel_list_result = {}
            else:
                session["results"]["excel_list_filename"] = excel_list_result.get("filename")
            
            # 통합 시나리오 결과 처리
            if isinstance(integrated_scenario_result, Exception):
                logger.error(f"통합 시나리오 생성 실패: {integrated_scenario_result}")
                session["errors"].append(f"통합 시나리오 생성 실패: {integrated_scenario_result}")
                integrated_scenario_result = {}
            else:
                session["results"]["integrated_scenario_filename"] = integrated_scenario_result.get("filename")
                # 하위 호환성을 위해 기존 키도 설정
                session["results"]["base_scenario_filename"] = integrated_scenario_result.get("filename")
                session["results"]["merged_excel_filename"] = integrated_scenario_result.get("filename")
                
        except Exception as e:
            logger.error(f"병렬 문서 생성 중 예외 발생: {e}")
            # 실패한 경우 개별 시도
            word_result = await generate_word_document(metadata_json)
            excel_list_result = await generate_excel_list([metadata_json])
            integrated_scenario_result = await generate_integrated_scenario(metadata_json, scenario_result.get("test_cases", []))
            
            session["results"]["word_filename"] = word_result.get("filename")
            session["results"]["excel_list_filename"] = excel_list_result.get("filename")
            session["results"]["integrated_scenario_filename"] = integrated_scenario_result.get("filename")
            # 하위 호환성을 위해 기존 키도 설정
            session["results"]["base_scenario_filename"] = integrated_scenario_result.get("filename")
            session["results"]["merged_excel_filename"] = integrated_scenario_result.get("filename")
        
        # Step 4: 완료
        session["completed_at"] = datetime.now()
        generation_time = (session["completed_at"] - session.get("started_at")).total_seconds() if session.get("started_at") else 0.0

        # 완료 결과 데이터 준비
        completion_result = {
            "word_filename": session["results"].get("word_filename"),
            "excel_list_filename": session["results"].get("excel_list_filename"),
            "base_scenario_filename": session["results"].get("base_scenario_filename"),
            "merged_excel_filename": session["results"].get("merged_excel_filename"),
            "integrated_scenario_filename": session["results"].get("integrated_scenario_filename"),
            "scenario_filename": session["results"].get("scenario_filename"),
            "generation_time": generation_time
        }

        # 완료 메시지 전송
        await send_progress(
            FullGenerationStatus.COMPLETED,
            "모든 문서 생성이 완료되었습니다!",
            100,
            "생성 완료",
            4,
            result=completion_result
        )

        await update_session_status(session_id, FullGenerationStatus.COMPLETED, "생성 완료", 4)
        logger.info(f"전체 문서 생성 완료: {session_id}")

    except Exception as e:
        logger.error(f"전체 문서 생성 실패: {session_id}, {e}")
        session["status"] = FullGenerationStatus.ERROR
        session["current_step"] = "생성 실패"
        session["errors"].append(str(e))

        # 오류 메시지 전송
        await send_progress(
            FullGenerationStatus.ERROR,
            f"문서 생성 중 오류가 발생했습니다: {str(e)}",
            50,  # 오류 발생 시 중간 진행률로 설정
            "생성 실패",
            session.get("steps_completed", 0)
        )


async def update_session_status(session_id: str, status: FullGenerationStatus, step: str, completed_steps: int):
    """
    세션 상태 업데이트
    
    Args:
        session_id: 세션 ID
        status: 새로운 상태
        step: 현재 단계
        completed_steps: 완료된 단계 수
    """
    if session_id in generation_sessions:
        session = generation_sessions[session_id]
        session["status"] = status
        session["current_step"] = step
        session["steps_completed"] = completed_steps
        
        logger.info(f"세션 상태 업데이트: {session_id} -> {status} ({step})")


async def generate_scenario_excel(vcs_analysis_text: str, metadata_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    시나리오 Excel 생성 (기존 검증된 로직 재사용)
    
    Args:
        vcs_analysis_text: VCS 분석 텍스트
        metadata_json: 메타데이터 (HTML 파싱 데이터 포함)
        
    Returns:
        생성 결과
    """
    try:
        from app.core.scenario_generator import generate_scenarios_with_llm, create_scenario_excel_file
        
        # HTML 파싱 데이터에서 추가 컨텍스트 추출
        additional_context = ""
        raw_data = metadata_json.get("raw_data", {})
        if isinstance(raw_data, dict):
            request_reason = raw_data.get("요청사유", "")
            request_content = raw_data.get("의뢰내용", "")
            
            if request_reason or request_content:
                additional_context = f"""
HTML 파싱 추가 정보:
- 요청사유: {request_reason}
- 의뢰내용: {request_content}
"""
        
        # 기존 검증된 로직 사용 (비동기 LLM)
        scenario_data = await generate_scenarios_with_llm(
            vcs_analysis_text=vcs_analysis_text,
            repo_path=metadata_json.get("change_id", "unknown"),
            performance_mode=False,
            additional_context=additional_context.strip() if additional_context.strip() else None,
            use_async_llm=True
        )
        
        # Excel 파일 생성
        title = metadata_json.get("title", "테스트 시나리오")
        filename = await create_scenario_excel_file(scenario_data, title)
        
        return {
            "filename": filename, 
            "test_cases": scenario_data.get("test_cases", []),
            "llm_response_time": scenario_data.get("llm_response_time", 0),
            "description": scenario_data.get("description", "")
        }
        
    except Exception as e:
        logger.error(f"시나리오 Excel 생성 실패: {e}")
        raise


async def generate_word_document(metadata_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Word 문서 생성 (autodoc_service 호출)
    
    Args:
        metadata_json: 메타데이터
        
    Returns:
        생성 결과
    """
    try:
        async with AutoDocClient() as client:
            result = await client.build_cm_word(metadata_json)
            return result
            
    except AutoDocServiceError as e:
        logger.error(f"Word 문서 생성 실패: {e}")
        raise


async def generate_excel_list(change_requests: list) -> Dict[str, Any]:
    """
    Excel 목록 생성 (autodoc_service 호출)
    
    Args:
        change_requests: 변경 요청 목록
        
    Returns:
        생성 결과
    """
    try:
        async with AutoDocClient() as client:
            result = await client.build_cm_list(change_requests)
            return result
            
    except AutoDocServiceError as e:
        logger.error(f"Excel 목록 생성 실패: {e}")
        raise


async def generate_base_scenario(metadata_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    기본 시나리오 생성 (autodoc_service 호출) - 하위 호환성용
    
    Args:
        metadata_json: 메타데이터
        
    Returns:
        생성 결과
    """
    try:
        async with AutoDocClient() as client:
            result = await client.build_base_scenario(metadata_json)
            return result
            
    except AutoDocServiceError as e:
        logger.error(f"기본 시나리오 생성 실패: {e}")
        raise


async def generate_integrated_scenario(metadata_json: Dict[str, Any], llm_test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    통합 시나리오 생성 (기본 시나리오 + LLM 테스트 케이스 통합)
    
    Args:
        metadata_json: 메타데이터
        llm_test_cases: LLM이 생성한 테스트 케이스 목록
        
    Returns:
        생성 결과
    """
    try:
        async with AutoDocClient() as client:
            result = await client.build_test_scenario(metadata_json, llm_test_cases)
            return result
            
    except AutoDocServiceError as e:
        logger.error(f"통합 시나리오 생성 실패: {e}")
        raise


async def enhance_base_scenario(base_scenario_filename: str, llm_test_cases: List[Dict[str, Any]], session_id: str, change_id: str) -> Dict[str, Any]:
    """
    기본 시나리오에 LLM 테스트 케이스 추가 (레거시 방식 - 하위 호환성용)
    
    Args:
        base_scenario_filename: 기본 시나리오 파일명
        llm_test_cases: LLM이 생성한 테스트 케이스 목록
        session_id: 세션 ID
        change_id: 변경 ID
        
    Returns:
        강화 결과
    """
    try:
        # webservice의 documents 디렉토리 경로
        from app.core.paths import get_documents_dir
        documents_dir = get_documents_dir()
        
        merger = ExcelMerger(documents_dir)
        result = merger.append_scenarios_to_base(
            base_scenario_filename,
            llm_test_cases,
            session_id,
            change_id
        )
        return result
        
    except ExcelMergerError as e:
        logger.error(f"시나리오 강화 실패: {e}")
        raise

async def merge_excel_files(scenario_filename: str, base_scenario_filename: str, session_id: str, change_id: str) -> Dict[str, Any]:
    """
    Excel 파일 병합 (레거시 방식 - 하위 호환성 유지)
    
    Args:
        scenario_filename: 시나리오 파일명
        base_scenario_filename: 기본 시나리오 파일명
        session_id: 세션 ID
        change_id: 변경 ID
        
    Returns:
        병합 결과
    """
    try:
        # webservice의 documents 디렉토리 경로
        from app.core.paths import get_documents_dir
        documents_dir = get_documents_dir()
        
        merger = ExcelMerger(documents_dir)
        result = merger.merge_scenario_files(
            scenario_filename,
            base_scenario_filename,
            session_id,
            change_id
        )
        return result
        
    except ExcelMergerError as e:
        logger.error(f"Excel 병합 실패: {e}")
        raise