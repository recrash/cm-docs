"""
v2 시나리오 생성 API 라우터
CLI 연동을 위한 비동기 시나리오 생성 처리
"""

import logging
import asyncio
import uuid
import json
import re
import time
import concurrent.futures
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pathlib import Path
from typing import Dict, Optional

# 프로젝트 경로 설정
from .models import (
    V2GenerationRequest, 
    V2GenerationResponse, 
    V2ProgressMessage,
    V2GenerationStatus,
    V2ResultData
)
from .progress_websocket import v2_connection_manager
from ....core.git_analyzer import get_git_analysis_text
from ....core.llm_handler import call_ollama_llm, OllamaAPIError
from ....core.excel_writer import save_results_to_excel
from ....core.config_loader import load_config
from ....core.prompt_loader import create_final_prompt, add_git_analysis_to_rag
from ....core.paths import get_templates_dir

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter()

# 활성 생성 작업 추적
active_generations: Dict[str, asyncio.Task] = {}


async def _handle_v2_generation(client_id: str, request: V2GenerationRequest):
    """백그라운드에서 실행되는 실제 생성 로직"""
    try:
        # 진행 상황 전송 헬퍼 함수
        async def send_progress(status: V2GenerationStatus, message: str, progress: float, details: Optional[dict] = None, result: Optional[dict] = None):
            progress_msg = V2ProgressMessage(
                client_id=client_id,
                status=status,
                message=message,
                progress=progress,
                details=details,
                result=result
            )
            await v2_connection_manager.send_progress(client_id, progress_msg)

        # 1. 요청 수신 확인
        await send_progress(V2GenerationStatus.RECEIVED, "요청을 수신했습니다.", 5)
        await asyncio.sleep(0.5)

        # 2. Git 저장소 유효성 검증 (CLI에서 전달받은 결과 사용)
        if not request.is_valid_git_repo:
            raise ValueError(f"CLI에서 검증한 결과, 유효하지 않은 Git 저장소입니다: {request.repo_path}")
        
        # 3. 설정 로드
        config = load_config()
        if not config:
            raise ValueError("설정 파일을 로드할 수 없습니다.")

        # 4. Git 분석
        await send_progress(V2GenerationStatus.ANALYZING_GIT, "Git 변경 내역을 분석 중입니다...", 15)
        await asyncio.sleep(1)
        git_analysis = get_git_analysis_text(request.repo_path)
        
        if not git_analysis:
            raise ValueError("Git 분석 결과를 얻을 수 없습니다.")

        # 5. RAG 저장
        await send_progress(V2GenerationStatus.STORING_RAG, "분석 결과를 RAG 시스템에 저장 중입니다...", 25)
        await asyncio.sleep(1)
        added_chunks = add_git_analysis_to_rag(git_analysis, request.repo_path)

        # 6. LLM 호출
        await send_progress(V2GenerationStatus.CALLING_LLM, "LLM을 호출하여 시나리오를 생성 중입니다...", 40, {
            "added_chunks": added_chunks
        })
        await asyncio.sleep(1)

        model_name = config.get("model_name", "qwen3:8b")
        timeout = config.get("timeout", 600)

        final_prompt = create_final_prompt(
            git_analysis,
            use_rag=True,
            use_feedback_enhancement=True,
            performance_mode=request.use_performance_mode
        )

        if not final_prompt:
            raise ValueError("프롬프트 생성에 실패했습니다.")

        # LLM 호출 시뮬레이션 (실제로는 시간이 많이 걸림)
        await send_progress(V2GenerationStatus.CALLING_LLM, "LLM 응답을 기다리는 중...", 60, {
            "added_chunks": added_chunks,
            "prompt_size": len(final_prompt)
        })
        
        # LLM 응답 시간 측정 + 웹소켓 연결 유지를 위한 주기적 업데이트
        start_time = time.time()
        
        async def heartbeat_during_llm():
            """LLM 처리 중 웹소켓 연결 유지를 위한 heartbeat"""
            heartbeat_count = 0
            while True:
                await asyncio.sleep(30)  # 30초마다
                heartbeat_count += 1
                elapsed = time.time() - start_time
                await send_progress(V2GenerationStatus.CALLING_LLM, 
                                  f"LLM 응답 대기 중... ({elapsed:.0f}초 경과)", 
                                  60 + (heartbeat_count % 10),  # 60-70% 사이 진동
                                  {
                                      "added_chunks": added_chunks,
                                      "prompt_size": len(final_prompt),
                                      "elapsed_time": elapsed,
                                      "heartbeat": heartbeat_count
                                  })
        
        # Heartbeat 태스크 시작
        heartbeat_task = asyncio.create_task(heartbeat_during_llm())
        
        try:
            # 별도 스레드에서 LLM 호출 (논블로킹)
            
            def call_llm_sync():
                return call_ollama_llm(final_prompt, model=model_name, timeout=timeout)
            
            # 스레드풀에서 LLM 호출
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(call_llm_sync)
                
                # LLM 완료까지 대기 (heartbeat과 함께)
                while not future.done():
                    await asyncio.sleep(1)
                
                raw_response = future.result()
                
        finally:
            # Heartbeat 태스크 종료
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
        
        end_time = time.time()
        llm_response_time = end_time - start_time
        
        if not raw_response:
            raise ValueError("LLM으로부터 응답을 받지 못했습니다.")

        # 7. 응답 파싱
        await send_progress(V2GenerationStatus.PARSING_RESPONSE, "LLM 응답을 파싱 중입니다...", 80, {
            "added_chunks": added_chunks,
            "prompt_size": len(final_prompt),
            "llm_response_time": llm_response_time
        })
        await asyncio.sleep(0.5)
        
        json_match = re.search(r'<json>(.*?)</json>', raw_response, re.DOTALL)
        if not json_match:
            raise ValueError("LLM 응답에서 JSON 블록을 찾을 수 없습니다.")

        result_json = json.loads(json_match.group(1).strip())

        # 8. Excel 파일 생성
        await send_progress(V2GenerationStatus.GENERATING_EXCEL, "Excel 파일을 생성 중입니다...", 90)
        await asyncio.sleep(1)

        template_path = get_templates_dir() / "template.xlsx"
        final_filename = save_results_to_excel(result_json, str(template_path))

        if not final_filename:
            raise ValueError("Excel 파일 생성에 실패했습니다.")

        # 9. 완료 처리
        filename = Path(final_filename).name
        download_url = f"/api/files/download/excel/{filename}"
        scenario_description = result_json.get("Scenario Description", "")
        test_cases = result_json.get("Test Cases", [])
        test_scenario_name = result_json.get("Test Scenario Name", "")

        result_data = V2ResultData(
            filename=filename,
            description=scenario_description,
            download_url=download_url,
            llm_response_time=llm_response_time,
            prompt_size=len(final_prompt),
            added_chunks=added_chunks,
            test_cases=test_cases,
            test_scenario_name=test_scenario_name
        )

        # 완료 메시지 전송
        await send_progress(
            V2GenerationStatus.COMPLETED,
            "시나리오 생성이 완료되었습니다!",
            100,
            result=result_data.model_dump()
        )

        logger.info(f"클라이언트 {client_id}의 시나리오 생성 완료: {filename}")

    except Exception as e:
        logger.exception(f"클라이언트 {client_id}의 시나리오 생성 중 오류 발생")
        
        error_msg = V2ProgressMessage(
            client_id=client_id,
            status=V2GenerationStatus.ERROR,
            message=f"시나리오 생성 중 오류가 발생했습니다: {str(e)}",
            progress=0
        )
        await v2_connection_manager.send_progress(client_id, error_msg)
    
    finally:
        # 완료된 작업을 추적에서 제거
        if client_id in active_generations:
            del active_generations[client_id]


@router.post("/generate", response_model=V2GenerationResponse)
async def generate_scenario_v2(request: V2GenerationRequest, background_tasks: BackgroundTasks):
    """
    CLI에서 호출하는 v2 시나리오 생성 API
    
    Args:
        request: 클라이언트 ID와 저장소 경로를 포함한 생성 요청
        background_tasks: FastAPI 백그라운드 작업 관리자
    
    Returns:
        즉시 응답과 WebSocket URL 제공
    """
    try:
        logger.info(f"v2 시나리오 생성 요청 수신: client_id={request.client_id}, repo_path={request.repo_path}, git_valid={request.is_valid_git_repo}")
        
        # 이미 진행 중인 작업인지 확인
        if request.client_id in active_generations:
            logger.warning(f"이미 진행 중인 작업: {request.client_id}")
            raise HTTPException(
                status_code=409,
                detail=f"클라이언트 {request.client_id}의 작업이 이미 진행 중입니다."
            )

        # 백그라운드에서 생성 작업 시작
        task = asyncio.create_task(_handle_v2_generation(request.client_id, request))
        active_generations[request.client_id] = task

        # WebSocket URL 생성 (config.json의 base_url 사용)
        config = load_config()
        if not config:
            raise HTTPException(
                status_code=500,
                detail="서버 설정을 로드할 수 없습니다. 관리자에게 문의하세요."
            )
        
        base_url = config.get("base_url")
        if not base_url:
            raise HTTPException(
                status_code=500, 
                detail="서버 설정에서 base_url을 찾을 수 없습니다. 관리자에게 문의하세요."
            )
        
        logger.info(f"설정에서 base_url 로드됨: {base_url}")
        
        # 프로토콜 결정: http면 ws, https면 wss 사용
        if base_url.startswith("https://"):
            protocol = "wss"
            host = base_url.replace("https://", "")
        elif base_url.startswith("http://"):
            protocol = "ws"
            host = base_url.replace("http://", "")
        else:
            # 프로토콜이 없으면 기본값 사용 (폐쇄망의 경우 http 가능성 높음)
            protocol = "ws"
            host = base_url
            
        websocket_url = f"{protocol}://{host}/api/v2/ws/progress/{request.client_id}"

        response = V2GenerationResponse(
            client_id=request.client_id,
            websocket_url=websocket_url
        )

        logger.info(f"v2 생성 작업 시작됨: {request.client_id}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("v2 시나리오 생성 요청 처리 중 예기치 않은 오류")
        raise HTTPException(
            status_code=500,
            detail=f"서버 오류: {str(e)}"
        )


@router.get("/status/{client_id}")
async def get_generation_status(client_id: str):
    """
    특정 클라이언트의 생성 상태 조회
    
    Args:
        client_id: 조회할 클라이언트 ID
    
    Returns:
        현재 생성 상태 정보
    """
    is_active = client_id in active_generations
    is_connected = v2_connection_manager.is_connected(client_id)
    
    return {
        "client_id": client_id,
        "is_generating": is_active,
        "is_websocket_connected": is_connected,
        "status": "generating" if is_active else "idle"
    }