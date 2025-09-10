"""
Phase 2: 전체 문서 생성 API

CLI에서 sessionId와 metadata를 포함한 요청을 받아서
모든 문서를 생성하고 병합하는 오케스트레이션 API
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from .models import (
    FullGenerationRequest, 
    FullGenerationResponse, 
    FullGenerationStatus, 
    FullGenerationResultData
)
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
        
        # 세션 초기화
        generation_sessions[request.session_id] = {
            "status": FullGenerationStatus.RECEIVED,
            "started_at": datetime.now(),
            "steps_completed": 0,
            "total_steps": 6,  # 총 6단계
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
        
        return FullGenerationResponse(
            session_id=request.session_id,
            status="accepted",
            message="전체 문서 생성 작업이 시작되었습니다."
        )
        
    except Exception as e:
        logger.error(f"전체 문서 생성 시작 실패: {e}")
        raise HTTPException(status_code=500, detail=f"전체 문서 생성 시작 실패: {e}")


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
    
    Args:
        session_id: 세션 ID
        vcs_analysis_text: VCS 분석 텍스트
        metadata_json: 메타데이터
    """
    session = generation_sessions[session_id]
    
    try:
        logger.info(f"전체 문서 생성 실행 시작: {session_id}")
        
        # Step 1: VCS 분석 처리
        await update_session_status(session_id, FullGenerationStatus.ANALYZING_VCS, "VCS 분석 중", 1)
        await asyncio.sleep(1)  # 시뮬레이션
        
        # Step 2: 시나리오 생성
        await update_session_status(session_id, FullGenerationStatus.GENERATING_SCENARIOS, "시나리오 생성 중", 2)
        scenario_result = await generate_scenario_excel(vcs_analysis_text, metadata_json)
        session["results"]["scenario_filename"] = scenario_result.get("filename")
        
        # Step 3, 4, 5: autodoc_service 문서 3종 동시 생성 (성능 최적화)
        await update_session_status(session_id, FullGenerationStatus.GENERATING_WORD_DOC, "Word, Excel 목록, 기본 시나리오 동시 생성 중", 3)
        
        # asyncio.gather를 사용해 3개의 작업을 동시에 실행 (성능 3배 향상)
        try:
            results = await asyncio.gather(
                generate_word_document(metadata_json),
                generate_excel_list([metadata_json]),
                generate_base_scenario(metadata_json),
                return_exceptions=True  # 작업 중 하나가 실패해도 나머지는 계속하도록
            )
            
            # 결과 처리
            word_result, excel_list_result, base_scenario_result = results
            
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
            
            # 기본 시나리오 결과 처리
            if isinstance(base_scenario_result, Exception):
                logger.error(f"기본 시나리오 생성 실패: {base_scenario_result}")
                session["errors"].append(f"기본 시나리오 생성 실패: {base_scenario_result}")
                base_scenario_result = {}
            else:
                session["results"]["base_scenario_filename"] = base_scenario_result.get("filename")
                
        except Exception as e:
            logger.error(f"병렬 문서 생성 중 예외 발생: {e}")
            # 실패한 경우 개별 시도
            word_result = await generate_word_document(metadata_json)
            excel_list_result = await generate_excel_list([metadata_json])
            base_scenario_result = await generate_base_scenario(metadata_json)
            
            session["results"]["word_filename"] = word_result.get("filename")
            session["results"]["excel_list_filename"] = excel_list_result.get("filename")
            session["results"]["base_scenario_filename"] = base_scenario_result.get("filename")
        
        # Step 6: Excel 시나리오 강화 (기본 템플릿에 LLM 테스트 케이스 추가)
        await update_session_status(session_id, FullGenerationStatus.MERGING_EXCEL, "시나리오 강화 중 (LLM 테스트 케이스 추가)", 6)
        if scenario_result.get("test_cases") and base_scenario_result.get("filename"):
            enhanced_result = await enhance_base_scenario(
                base_scenario_result["filename"],
                scenario_result["test_cases"],
                session_id,
                metadata_json.get("change_id", "UNKNOWN")
            )
            session["results"]["merged_excel_filename"] = enhanced_result.get("merged_filename")
        
        # 완료
        session["status"] = FullGenerationStatus.COMPLETED
        session["current_step"] = "생성 완료"
        session["completed_at"] = datetime.now()
        
        logger.info(f"전체 문서 생성 완료: {session_id}")
        
    except Exception as e:
        logger.error(f"전체 문서 생성 실패: {session_id}, {e}")
        session["status"] = FullGenerationStatus.ERROR
        session["current_step"] = "생성 실패"
        session["errors"].append(str(e))


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
    기본 시나리오 생성 (autodoc_service 호출)
    
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


async def enhance_base_scenario(base_scenario_filename: str, llm_test_cases: List[Dict[str, Any]], session_id: str, change_id: str) -> Dict[str, Any]:
    """
    기본 시나리오에 LLM 테스트 케이스 추가 (새로운 최적화된 방식)
    
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