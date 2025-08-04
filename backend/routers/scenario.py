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
import sys
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.git_analyzer import get_git_analysis_text
from src.llm_handler import call_ollama_llm, OllamaAPIError
from src.excel_writer import save_results_to_excel
from src.config_loader import load_config
from src.prompt_loader import create_final_prompt, add_git_analysis_to_rag
from backend.models.scenario import (
    ScenarioGenerationRequest, 
    ScenarioResponse, 
    ScenarioMetadata,
    GenerationProgress, 
    GenerationStatus
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

        if not (request.repo_path and Path(request.repo_path).is_dir()):
            await _handle_generation_error(websocket, "유효한 Git 저장소 경로를 입력해주세요.")
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

        project_root = Path(__file__).resolve().parents[2]
        template_path = project_root / "templates" / "template.xlsx"
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
