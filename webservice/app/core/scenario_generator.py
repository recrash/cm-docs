"""
공통 시나리오 생성 모듈

scenario_v2.py의 검증된 로직을 추출하여 재사용 가능하게 모듈화
Phase 2 오케스트레이션과 기존 v2 API에서 공통으로 사용
"""

import asyncio
import json
import logging
import re
import time
import concurrent.futures
from typing import Dict, Any, Optional
from pathlib import Path

from .config_loader import load_config
from .prompt_loader import create_final_prompt, add_git_analysis_to_rag
from .llm_handler import call_ollama_llm, LLMHandler
from .excel_writer import save_results_to_excel
from .paths import get_templates_dir

logger = logging.getLogger(__name__)


async def generate_scenarios_with_llm(
    vcs_analysis_text: str,
    repo_path: str,
    performance_mode: bool = False,
    additional_context: Optional[str] = None,
    use_async_llm: bool = True
) -> Dict[str, Any]:
    """
    VCS 분석 데이터를 기반으로 LLM을 사용해 시나리오를 생성합니다.
    
    scenario_v2.py의 검증된 로직을 재사용하여 일관된 품질을 보장합니다.
    
    Args:
        vcs_analysis_text: VCS 분석 결과 텍스트 (Git/SVN 공통)
        repo_path: 저장소 경로 
        performance_mode: 성능 최적화 모드 (프롬프트 길이 제한)
        additional_context: 추가 컨텍스트 (HTML 파싱 데이터 등)
        use_async_llm: True면 비동기 LLM 사용, False면 기존 동기 방식
        
    Returns:
        생성된 시나리오 데이터 딕셔너리
        
    Raises:
        ValueError: 입력 데이터 검증 실패 또는 LLM 응답 파싱 실패 시
        Exception: LLM 호출 실패 또는 기타 처리 오류 시
    """
    try:
        # 1. 입력 데이터 검증
        if not vcs_analysis_text or vcs_analysis_text.startswith("오류:"):
            raise ValueError(f"VCS 분석 결과가 유효하지 않습니다: {vcs_analysis_text}")
        
        # 2. 설정 로드
        config = load_config()
        if not config:
            raise ValueError("설정 파일을 로드할 수 없습니다.")
        
        model_name = config.get("model_name", "qwen3:8b")
        timeout = config.get("timeout", 600)
        
        # 3. RAG 저장
        logger.info("분석 결과를 RAG 시스템에 저장 중...")
        added_chunks = add_git_analysis_to_rag(vcs_analysis_text, repo_path)
        
        # 4. 프롬프트 생성 (기존 검증된 로직 사용)
        base_prompt = create_final_prompt(
            vcs_analysis_text,
            use_rag=True,
            use_feedback_enhancement=True,
            performance_mode=performance_mode
        )
        
        if not base_prompt:
            raise ValueError("프롬프트 생성에 실패했습니다.")
        
        # 추가 컨텍스트가 있으면 프롬프트에 통합
        final_prompt = base_prompt
        if additional_context:
            final_prompt = f"{base_prompt}\n\n추가 컨텍스트:\n{additional_context}"
        
        # 5. LLM 호출 (비동기 또는 동기)
        logger.info(f"LLM 호출 시작 (모델: {model_name}, 비동기: {use_async_llm})")
        start_time = time.time()
        
        if use_async_llm:
            # 비동기 LLM 사용 (Phase 2에서 사용)
            llm_handler = LLMHandler()
            try:
                # LLMHandler는 이미 비동기이므로 직접 호출
                raw_response = await llm_handler.generate_scenarios_async(final_prompt)
                # LLMHandler는 이미 파싱된 결과를 반환하므로 그대로 사용
                result_json = raw_response
            finally:
                await llm_handler.close()
        else:
            # 기존 동기 방식 (기존 v2 API와 호환)
            def call_llm_sync():
                return call_ollama_llm(final_prompt, model=model_name, timeout=timeout)
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(call_llm_sync)
                while not future.done():
                    await asyncio.sleep(1)
                raw_response = future.result()
                
            if not raw_response:
                raise ValueError("LLM으로부터 응답을 받지 못했습니다.")
            
            # 6. 응답 파싱 (기존 검증된 로직 사용)
            result_json = _parse_llm_response(raw_response)
        
        end_time = time.time()
        llm_response_time = end_time - start_time
        
        # 7. 결과 데이터 구성
        result = {
            "test_cases": result_json.get("Test Cases", result_json.get("test_cases", [])),
            "description": result_json.get("Scenario Description", result_json.get("description", "")),
            "test_scenario_name": result_json.get("Test Scenario Name", result_json.get("test_scenario_name", "")),
            "llm_response_time": llm_response_time,
            "prompt_size": len(final_prompt),
            "added_chunks": added_chunks
        }
        
        logger.info(f"시나리오 생성 완료 (응답시간: {llm_response_time:.2f}초, 테스트케이스: {len(result['test_cases'])}개)")
        return result
        
    except Exception as e:
        logger.error(f"시나리오 생성 중 오류 발생: {e}")
        raise


def _parse_llm_response(raw_response: str) -> Dict[str, Any]:
    """
    LLM 원시 응답을 파싱합니다.
    
    scenario_v2.py의 검증된 파싱 로직을 재사용합니다.
    <json> 태그와 ```json 마크다운 블록을 모두 지원합니다.
    
    Args:
        raw_response: LLM 원시 응답 텍스트
        
    Returns:
        파싱된 JSON 딕셔너리
        
    Raises:
        ValueError: JSON 블록을 찾을 수 없거나 파싱에 실패한 경우
    """
    logger.debug(f"LLM 응답 파싱 중... (길이: {len(raw_response)})")
    
    # <json> 태그 또는 ```json 코드 블록 모두 지원 (기존 검증된 로직)
    json_match = re.search(r'<json>(.*?)</json>', raw_response, re.DOTALL)
    if not json_match:
        # markdown 스타일 ```json 블록도 시도
        json_match = re.search(r'```json\s*(.*?)\s*```', raw_response, re.DOTALL)
    
    if not json_match:
        # 디버깅을 위한 상세 로깅
        logger.error(f"JSON 블록을 찾을 수 없습니다. 응답 샘플: {raw_response[:500]}...")
        raise ValueError("LLM 응답에서 JSON 블록을 찾을 수 없습니다.")

    try:
        result_json = json.loads(json_match.group(1).strip())
        logger.debug(f"JSON 파싱 성공 (키: {list(result_json.keys())})")
        return result_json
    except json.JSONDecodeError as e:
        logger.error(f"JSON 파싱 실패: {e}")
        logger.error(f"파싱 대상 텍스트: {json_match.group(1)[:200]}...")
        raise ValueError(f"LLM 응답 JSON 파싱 실패: {e}")


async def create_scenario_excel_file(
    scenario_data: Dict[str, Any],
    title: str = "테스트 시나리오"
) -> str:
    """
    시나리오 데이터로 Excel 파일을 생성합니다.
    
    Args:
        scenario_data: generate_scenarios_with_llm()의 결과 데이터
        title: Excel 파일 제목
        
    Returns:
        생성된 Excel 파일의 경로 (파일명)
        
    Raises:
        ValueError: Excel 파일 생성 실패 시
    """
    try:
        template_path = get_templates_dir() / "template.xlsx"
        
        # scenario_v2.py와 동일한 방식으로 결과 구성
        excel_data = {
            "Test Cases": scenario_data.get("test_cases", []),
            "Scenario Description": scenario_data.get("description", ""),
            "Test Scenario Name": scenario_data.get("test_scenario_name", title)
        }
        
        final_filename = save_results_to_excel(excel_data, str(template_path))
        
        if not final_filename:
            raise ValueError("Excel 파일 생성에 실패했습니다.")
        
        return Path(final_filename).name
        
    except Exception as e:
        logger.error(f"Excel 파일 생성 실패: {e}")
        raise