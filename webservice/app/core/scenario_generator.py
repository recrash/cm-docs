"""
공통 시나리오 생성 모듈

scenario_v2.py의 검증된 로직을 추출하여 재사용 가능하게 모듈화
Phase 2 오케스트레이션과 기존 v2 API에서 공통으로 사용
"""

import asyncio
import json
import logging
import os
import re
import sys
import time
import concurrent.futures
from typing import Dict, Any, Optional, Union
from pathlib import Path

# Windows 인코딩 문제 해결 - Full Generation 에러 수정
if sys.platform.startswith('win'):
    os.environ['PYTHONIOENCODING'] = 'utf-8'

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
        
        # [FULL-GEN DEBUG] LLM 호출 전 디버깅 로그 추가 (scenario_v2.py 패턴 적용)
        logger.error(f"[FULL-GEN DEBUG] VCS Analysis (first 500 chars): {vcs_analysis_text[:500]}")
        logger.error(f"[FULL-GEN DEBUG] Final prompt (last 300 chars): {final_prompt[-300:]}")
        
        start_time = time.time()
        
        if use_async_llm:
            # 비동기 LLM 사용 (Phase 2에서 사용)
            llm_handler = LLMHandler()
            try:
                # LLMHandler는 이미 비동기이므로 직접 호출
                raw_response = await llm_handler.generate_scenarios_async(final_prompt)
                
                # [FULL-GEN DEBUG] 비동기 LLM 응답 후 디버깅 로그
                raw_response_str = str(raw_response) if raw_response else "None"
                logger.error(f"[FULL-GEN DEBUG] Async LLM Response (first 500 chars): {raw_response_str[:500]}")
                
                # _parse_llm_response는 이제 dictionary와 string 모두 처리 가능
                result_json = _parse_llm_response(raw_response)
                
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
            
            # [FULL-GEN DEBUG] 동기 LLM 응답 후 디버깅 로그 (scenario_v2.py 패턴 적용)
            raw_response_str = str(raw_response) if raw_response else "None"
            logger.error(f"[FULL-GEN DEBUG] Sync LLM Raw Response (first 500 chars): {raw_response_str[:500]}")
            
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
        
        # [FULL-GEN DEBUG] 파싱 결과 디버깅 로그
        logger.error(f"[FULL-GEN DEBUG] Parsed scenarios count: {len(result['test_cases'])}")
        
        logger.info(f"시나리오 생성 완료 (응답시간: {llm_response_time:.2f}초, 테스트케이스: {len(result['test_cases'])}개)")
        return result
        
    except Exception as e:
        logger.error(f"시나리오 생성 중 오류 발생: {e}")
        raise


def _parse_llm_response(raw_response: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    LLM 원시 응답을 파싱합니다.
    
    scenario_v2.py의 검증된 파싱 로직을 재사용합니다.
    <json> 태그와 ```json 마크다운 블록을 모두 지원합니다.
    
    Args:
        raw_response: LLM 원시 응답 텍스트 또는 이미 파싱된 dictionary
        
    Returns:
        파싱된 JSON 딕셔너리
        
    Raises:
        ValueError: JSON 블록을 찾을 수 없거나 파싱에 실패한 경우
    """
    # 이미 딕셔너리인 경우 (비동기 LLM handler에서 반환된 경우)
    if isinstance(raw_response, dict):
        logger.debug(f"이미 파싱된 딕셔너리 반환 (키: {list(raw_response.keys())})")
        return raw_response
    
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
        logger.error(f"문제가 된 JSON 부분: {json_match.group(1)[max(0, e.pos-50):e.pos+50] if hasattr(e, 'pos') else 'N/A'}")
        
        # JSON 복구 시도 (불완전한 JSON 처리) - Full Generation 에러 방어
        try:
            json_str = json_match.group(1).strip()
            
            # 1차 복구: 마지막 콤마 제거
            json_str = json_str.rstrip(',')
            
            # 2차 복구: 불완전한 중괄호 처리
            if not json_str.endswith('}') and json_str.count('{') > json_str.count('}'):
                json_str += '}'
            
            # 3차 복구: 불완전한 배열 처리
            if '"test_cases"' in json_str and not json_str.rstrip('}').endswith(']'):
                # 배열이 닫히지 않은 경우 닫기
                last_bracket = json_str.rfind('[')
                if last_bracket != -1:
                    before_bracket = json_str[:last_bracket+1]
                    json_str = before_bracket + ']'
                    if not json_str.endswith('}'):
                        json_str += '}'
            
            # 복구된 JSON으로 재시도
            result_json = json.loads(json_str)
            logger.warning(f"JSON 복구 성공: {json_str[:100]}...")
            return result_json
            
        except json.JSONDecodeError as recovery_error:
            logger.error(f"JSON 복구도 실패: {recovery_error}")
            
            # 최종 안전망: 기본 구조 반환
            logger.warning("안전한 기본 구조로 대체합니다.")
            return {
                "Test Cases": [],
                "Scenario Description": "JSON 파싱 오류로 인한 기본 시나리오",
                "Test Scenario Name": "파싱 실패 시나리오"
            }


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
        
        # Excel 파일 생성 (Windows 인코딩 안전 처리)
        try:
            final_filename = save_results_to_excel(excel_data, str(template_path))
        except (UnicodeEncodeError, UnicodeDecodeError) as enc_err:
            logger.error(f"Excel 파일 생성 중 인코딩 에러: {enc_err}")
            # 파일명에서 한글 제거하여 재시도
            safe_title = title.encode('ascii', errors='replace').decode('ascii')
            excel_data["Test Scenario Name"] = safe_title
            final_filename = save_results_to_excel(excel_data, str(template_path))
            logger.warning(f"안전한 파일명으로 Excel 생성: {safe_title}")
        
        if not final_filename:
            raise ValueError("Excel 파일 생성에 실패했습니다.")
        
        return Path(final_filename).name
        
    except Exception as e:
        logger.error(f"Excel 파일 생성 실패: {e}")
        raise