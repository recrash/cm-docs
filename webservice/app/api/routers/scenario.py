import logging
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import JSONResponse
import json
import re
import os
import time
import asyncio
from typing import List
from pathlib import Path

# Set up logger for this module
logger = logging.getLogger(__name__)

# Standard library and project module imports
from ...core.git_analyzer import get_git_analysis_text
from ...core.llm_handler import call_ollama_llm, OllamaAPIError
from ...core.paths import get_templates_dir
from ...core.excel_writer import save_results_to_excel
from ...core.config_loader import load_config
from ...core.prompt_loader import create_final_prompt, add_git_analysis_to_rag
from ..models.scenario import (
    ScenarioGenerationRequest, 
    ScenarioResponse, 
    ScenarioMetadata,
    GenerationProgress, 
    GenerationStatus,
    AnalysisTextRequest,
    AnalysisTextResponse
)

router = APIRouter()

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket connection established.")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("WebSocket connection closed.")

    async def send_progress(self, websocket: WebSocket, progress: GenerationProgress):
        try:
            progress_dict = progress.model_dump()
            await websocket.send_text(json.dumps(progress_dict))
        except Exception:
            logger.warning("Failed to send progress update over WebSocket.", exc_info=True)
            self.disconnect(websocket)

manager = ConnectionManager()

async def _handle_generation_error(websocket: WebSocket, message: str, detail: str = ""):
    """Helper to log errors and send error messages via WebSocket."""
    logger.error(f"{message} - Detail: {detail}")
    await manager.send_progress(websocket, GenerationProgress(
        status=GenerationStatus.ERROR,
        message=message,
        progress=0
    ))

@router.websocket("/generate-ws")
async def generate_scenario_ws(websocket: WebSocket):
    await manager.connect(websocket)
    
    try:
        data = await websocket.receive_text()
        request = ScenarioGenerationRequest(**json.loads(data))

        if not request.repo_path or not request.repo_path.strip():
            await _handle_generation_error(websocket, "Git 저장소 경로를 입력해주세요.")
            return
        
        config = load_config()
        if not config:
            await _handle_generation_error(websocket, "설정 파일을 로드할 수 없습니다.")
            return

        async def send_progress(status: GenerationStatus, message: str, progress: float, details=None):
            await manager.send_progress(websocket, GenerationProgress(
                status=status, message=message, progress=progress, details=details
            ))

        # 1. Git Analysis
        await send_progress(GenerationStatus.ANALYZING_GIT, "Git 변경 내역을 분석 중입니다...", 10)
        await asyncio.sleep(1)
        git_analysis = get_git_analysis_text(request.repo_path)
        
        # 2. RAG Storage
        await send_progress(GenerationStatus.STORING_RAG, "분석 결과를 RAG 시스템에 저장 중입니다...", 20)
        await asyncio.sleep(1)
        added_chunks = add_git_analysis_to_rag(git_analysis, request.repo_path)
        
        # 3. LLM Call
        await send_progress(GenerationStatus.CALLING_LLM, "LLM을 호출하여 시나리오를 생성 중입니다...", 30)
        await asyncio.sleep(1)
        
        model_name = config.get("model_name", "qwen3:8b")
        timeout = config.get("timeout", 600)
        
        final_prompt = create_final_prompt(
            git_analysis, 
            use_rag=True, 
            use_feedback_enhancement=True,
            performance_mode=request.use_performance_mode
        )
        
        start_time = time.time()
        raw_response = call_ollama_llm(final_prompt, model=model_name, timeout=timeout)
        end_time = time.time()
        
        if not raw_response:
            await _handle_generation_error(websocket, "LLM으로부터 응답을 받지 못했습니다.")
            return
        
        # 4. JSON Parsing
        await send_progress(GenerationStatus.PARSING_RESPONSE, "LLM 응답을 파싱 중입니다...", 80)
        await asyncio.sleep(1)
        json_match = re.search(r'<json>(.*?)</json>', raw_response, re.DOTALL)
        if not json_match:
            await _handle_generation_error(websocket, "LLM 응답에서 JSON 블록을 찾을 수 없습니다.")
            return
        
        result_json = json.loads(json_match.group(1).strip())
        
        # 5. Excel File Generation
        await send_progress(GenerationStatus.GENERATING_EXCEL, "Excel 파일을 생성 중입니다...", 90)
        await asyncio.sleep(1)

        template_path = get_templates_dir() / "template.xlsx"
        final_filename = save_results_to_excel(result_json, str(template_path))
        
        # Completion
        metadata = ScenarioMetadata(
            llm_response_time=end_time - start_time,
            prompt_size=len(final_prompt),
            added_chunks=added_chunks,
            excel_filename=final_filename
        )
        
        response_data = {
            "scenario_description": result_json.get("Scenario Description", ""),
            "test_scenario_name": result_json.get("Test Scenario Name", ""),
            "test_cases": result_json.get("Test Cases", []),
            "metadata": metadata.model_dump()
        }
        
        await send_progress(
            GenerationStatus.COMPLETED, 
            "시나리오 생성이 완료되었습니다!", 
            100,
            {"result": response_data}
        )
        
    except WebSocketDisconnect:
        logger.info("Client disconnected.")
    except json.JSONDecodeError as e:
        await _handle_generation_error(websocket, "JSON 파싱 오류가 발생했습니다.", str(e))
    except OllamaAPIError as e:
        await _handle_generation_error(websocket, "LLM API 호출 중 오류가 발생했습니다.", str(e))
    except Exception as e:
        await _handle_generation_error(websocket, "시나리오 생성 중 예기치 않은 오류가 발생했습니다.", str(e))
    finally:
        manager.disconnect(websocket)

@router.get("/config")
async def get_scenario_config():
    """Returns the scenario generation configuration."""
    try:
        config = load_config()
        if not config:
            raise HTTPException(status_code=500, detail="설정 파일을 로드할 수 없습니다.")
        
        return {
            "model_name": config.get("model_name", "qwen3:8b"),
            "timeout": config.get("timeout", 600),
            "repo_path": config.get("repo_path", ""),
            "rag_enabled": config.get("rag", {}).get("enabled", False)
        }
    except Exception as e:
        logger.exception("Failed to load scenario configuration.")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/v1/generate-from-text", response_model=AnalysisTextResponse)
async def generate_scenario_from_text(request: AnalysisTextRequest):
    """
    분석 텍스트를 기반으로 테스트 시나리오를 생성합니다.
    
    Args:
        request: 분석 텍스트가 포함된 요청 객체
    
    Returns:
        생성된 Excel 파일의 다운로드 URL과 메타데이터
    """
    try:
        logger.info("분석 텍스트 기반 시나리오 생성 시작")
        
        # 설정 로드
        config = load_config()
        if not config:
            raise HTTPException(status_code=500, detail="설정 파일을 로드할 수 없습니다.")
        
        # LLM 호출을 위한 프롬프트 생성
        model_name = config.get("model_name", "qwen3:8b")
        timeout = config.get("timeout", 600)
        
        # 분석 텍스트를 Git 분석 결과로 사용하여 프롬프트 생성
        final_prompt = create_final_prompt(
            request.analysis_text, 
            use_rag=True, 
            use_feedback_enhancement=True,
            performance_mode=True  # CLI 요청은 성능 모드로 처리
        )
        
        if not final_prompt:
            raise HTTPException(status_code=500, detail="프롬프트 생성에 실패했습니다.")
        
        # LLM 호출
        logger.info(f"LLM 모델 '{model_name}' 호출 중...")
        start_time = time.time()
        raw_response = call_ollama_llm(final_prompt, model=model_name, timeout=timeout)
        end_time = time.time()
        
        if not raw_response:
            raise HTTPException(status_code=500, detail="LLM으로부터 응답을 받지 못했습니다.")
        
        # JSON 파싱
        logger.info("LLM 응답 파싱 중...")
        json_match = re.search(r'<json>(.*?)</json>', raw_response, re.DOTALL)
        if not json_match:
            raise HTTPException(status_code=500, detail="LLM 응답에서 JSON 블록을 찾을 수 없습니다.")
        
        result_json = json.loads(json_match.group(1).strip())
        
        # Excel 파일 생성
        logger.info("Excel 파일 생성 중...")
        template_path = get_templates_dir() / "template.xlsx"
        final_filename = save_results_to_excel(result_json, str(template_path))
        
        if not final_filename:
            raise HTTPException(status_code=500, detail="Excel 파일 생성에 실패했습니다.")
        
        # 파일명에서 다운로드 URL 생성
        filename = Path(final_filename).name
        download_url = f"/api/files/download/excel/{filename}"
        
        logger.info(f"시나리오 생성 완료: {filename}")
        
        return AnalysisTextResponse(
            download_url=download_url,
            filename=filename,
            message="시나리오가 성공적으로 생성되었습니다."
        )
        
    except HTTPException:
        # HTTPException은 그대로 재발생
        raise
    except json.JSONDecodeError as e:
        logger.error(f"JSON 파싱 오류: {e}")
        raise HTTPException(status_code=500, detail=f"JSON 파싱 오류: {str(e)}")
    except OllamaAPIError as e:
        logger.error(f"LLM API 오류: {e}")
        raise HTTPException(status_code=500, detail=f"LLM API 오류: {str(e)}")
    except Exception as e:
        logger.exception("분석 텍스트 기반 시나리오 생성 중 예기치 않은 오류 발생")
        raise HTTPException(status_code=500, detail=f"시나리오 생성 중 오류 발생: {str(e)}")
