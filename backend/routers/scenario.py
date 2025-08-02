"""
시나리오 생성 관련 API 라우터
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import JSONResponse
import json
import re
import os
import time
import asyncio
from typing import List

# 기존 모듈 import
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.git_analyzer import get_git_analysis_text
from src.llm_handler import call_ollama_llm
from src.excel_writer import save_results_to_excel
from src.config_loader import load_config
from src.prompt_loader import (
    create_final_prompt, 
    add_git_analysis_to_rag, 
    get_rag_info
)

from backend.models.scenario import (
    ScenarioGenerationRequest, 
    ScenarioResponse, 
    ScenarioMetadata,
    GenerationProgress, 
    GenerationStatus
)

router = APIRouter()

# WebSocket 연결 관리
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_progress(self, websocket: WebSocket, progress: GenerationProgress):
        try:
            # Convert to dict and then to JSON string for proper serialization
            progress_dict = progress.model_dump()
            await websocket.send_text(json.dumps(progress_dict))
        except Exception as e:
            print(f"WebSocket send error: {e}")
            self.disconnect(websocket)

manager = ConnectionManager()

@router.post("/generate", response_model=ScenarioResponse)
async def generate_scenario(
    request: ScenarioGenerationRequest,
    background_tasks: BackgroundTasks
):
    """테스트 시나리오 생성 API"""
    
    if not request.repo_path or not os.path.isdir(request.repo_path):
        raise HTTPException(status_code=400, detail="유효한 Git 저장소 경로를 입력해주세요.")
    
    config = load_config()
    if not config:
        raise HTTPException(status_code=500, detail="설정 파일을 로드할 수 없습니다.")
    
    try:
        # 1. Git 분석
        git_analysis = get_git_analysis_text(request.repo_path)
        
        # 2. RAG 저장
        added_chunks = add_git_analysis_to_rag(git_analysis, request.repo_path)
        
        # 3. LLM 호출
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
            raise HTTPException(status_code=500, detail="LLM으로부터 응답을 받지 못했습니다.")
        
        # 4. JSON 파싱
        json_match = re.search(r'<json>(.*?)</json>', raw_response, re.DOTALL)
        if not json_match:
            raise HTTPException(status_code=500, detail="LLM 응답에서 JSON 블록을 찾을 수 없습니다.")
        
        json_string = json_match.group(1).strip()
        result_json = json.loads(json_string)
        
        # 5. Excel 파일 생성
        # 백엔드에서 실행될 때 절대 경로 사용
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        template_path = os.path.join(project_root, "templates", "template.xlsx")
        final_filename = save_results_to_excel(result_json, template_path)
        
        # 응답 데이터 구성
        metadata = ScenarioMetadata(
            llm_response_time=end_time - start_time,
            prompt_size=len(final_prompt),
            added_chunks=added_chunks,
            excel_filename=final_filename
        )
        
        response_data = {
            "Scenario Description": result_json.get("Scenario Description", ""),
            "Test Scenario Name": result_json.get("Test Scenario Name", ""),
            "Test Cases": result_json.get("Test Cases", []),
            "metadata": metadata
        }
        
        return ScenarioResponse(**response_data)
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"JSON 파싱 오류: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"시나리오 생성 중 오류가 발생했습니다: {str(e)}")

@router.websocket("/generate-ws")
async def generate_scenario_ws(websocket: WebSocket):
    """WebSocket을 통한 실시간 시나리오 생성"""
    await manager.connect(websocket)
    
    try:
        # 요청 데이터 수신
        data = await websocket.receive_text()
        request_data = json.loads(data)
        request = ScenarioGenerationRequest(**request_data)
        
        if not request.repo_path or not os.path.isdir(request.repo_path):
            await websocket.send_text(json.dumps({
                "status": "error",
                "message": "유효한 Git 저장소 경로를 입력해주세요."
            }))
            return
        
        config = load_config()
        if not config:
            await websocket.send_text(json.dumps({
                "status": "error", 
                "message": "설정 파일을 로드할 수 없습니다."
            }))
            return
        
        # 진행 상황 알림 함수
        async def send_progress(status: GenerationStatus, message: str, progress: float, details=None):
            progress_data = GenerationProgress(
                status=status,
                message=message,
                progress=progress,
                details=details
            )
            await manager.send_progress(websocket, progress_data)
        
        # 1. Git 분석
        await send_progress(GenerationStatus.ANALYZING_GIT, "Git 변경 내역을 분석 중입니다...", 10)
        await asyncio.sleep(1.0)  # 사용자가 볼 수 있도록 잠시 대기
        git_analysis = get_git_analysis_text(request.repo_path)
        
        # 2. RAG 저장
        await send_progress(GenerationStatus.STORING_RAG, "분석 결과를 RAG 시스템에 저장 중입니다...", 20)
        await asyncio.sleep(1.0)  # 사용자가 볼 수 있도록 잠시 대기
        added_chunks = add_git_analysis_to_rag(git_analysis, request.repo_path)
        
        # 3. LLM 호출
        await send_progress(GenerationStatus.CALLING_LLM, "LLM을 호출하여 시나리오를 생성 중입니다...", 30)
        await asyncio.sleep(1.0)  # 사용자가 볼 수 있도록 잠시 대기
        
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
            await send_progress(GenerationStatus.ERROR, "LLM으로부터 응답을 받지 못했습니다.", 0)
            return
        
        # 4. JSON 파싱
        await send_progress(GenerationStatus.PARSING_RESPONSE, "LLM 응답을 파싱 중입니다...", 80)
        await asyncio.sleep(1.0)  # 사용자가 볼 수 있도록 잠시 대기
        json_match = re.search(r'<json>(.*?)</json>', raw_response, re.DOTALL)
        if not json_match:
            await send_progress(GenerationStatus.ERROR, "LLM 응답에서 JSON 블록을 찾을 수 없습니다.", 0)
            return
        
        json_string = json_match.group(1).strip()
        result_json = json.loads(json_string)
        
        # 5. Excel 파일 생성
        await send_progress(GenerationStatus.GENERATING_EXCEL, "Excel 파일을 생성 중입니다...", 90)
        await asyncio.sleep(1.0)  # 사용자가 볼 수 있도록 잠시 대기
        # 백엔드에서 실행될 때 절대 경로 사용
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        template_path = os.path.join(project_root, "templates", "template.xlsx")
        final_filename = save_results_to_excel(result_json, template_path)
        
        # 완료 - ScenarioResponse 형식에 맞게 변환
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
            "metadata": metadata
        }
        
        await send_progress(
            GenerationStatus.COMPLETED, 
            "시나리오 생성이 완료되었습니다!", 
            100,
            {
                "result": response_data
            }
        )
        
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({
                "status": "error",
                "message": f"시나리오 생성 중 오류가 발생했습니다: {str(e)}"
            }))
        except:
            pass
        manager.disconnect(websocket)

@router.get("/config")
async def get_scenario_config():
    """시나리오 생성 설정 조회"""
    config = load_config()
    if not config:
        raise HTTPException(status_code=500, detail="설정 파일을 로드할 수 없습니다.")
    
    return {
        "model_name": config.get("model_name", "qwen3:8b"),
        "timeout": config.get("timeout", 600),
        "repo_path": config.get("repo_path", ""),
        "rag_enabled": config.get("rag", {}).get("enabled", False)
    }