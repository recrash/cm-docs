import httpx
import json
import logging
from typing import Optional, Dict, Any

# Get a logger for this module
logger = logging.getLogger(__name__)

# Constants
DEFAULT_MODEL = "qwen3:8b"
DEFAULT_TIMEOUT = 300  # 5분으로 증가 (기존 600초에서 300초로 조정)
OLLAMA_BASE_URL = "http://localhost:11434"
JSON_FORMAT = "json"

class OllamaAPIError(Exception):
    """Custom exception for Ollama API errors."""
    pass

def _create_payload(prompt: str, model: str, format_type: str) -> Dict[str, Any]:
    """Creates the payload for the Ollama API request."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    if format_type == JSON_FORMAT:
        payload['format'] = JSON_FORMAT
    return payload

# 하위 호환성을 위한 동기 함수 유지 (레거시 코드용)
async def _send_request_async(client: httpx.AsyncClient, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Sends an async request to the Ollama API and returns the response."""
    try:
        response = await client.post("/api/generate", json=payload)
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        logger.exception("Ollama API request failed")
        raise OllamaAPIError(f"Error calling Ollama API: {e}")
    except httpx.HTTPStatusError as e:
        logger.exception("Ollama API HTTP error")
        raise OllamaAPIError(f"Ollama API HTTP error {e.response.status_code}: {e.response.text}")

def call_ollama_llm(
    prompt: str, 
    model: str = DEFAULT_MODEL, 
    format: str = "", 
    timeout: int = DEFAULT_TIMEOUT
) -> Optional[str]:
    """
    Calls the Ollama API with a given prompt (동기 버전 - 하위 호환성용)
    
    ⚠️ 주의: 이 함수는 동기 방식이므로 FastAPI에서는 사용하지 마세요.
    비동기 환경에서는 LLMHandler.generate_scenarios_async()를 사용하세요.
    """
    import requests
    
    logger.info(f"Calling Ollama model '{model}' (sync)...")
    
    try:
        payload = _create_payload(prompt, model, format)
        response = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=timeout)
        response.raise_for_status()
        response_data = response.json()
        
        response_text = response_data.get('response', '').strip()
        if not response_text:
            logger.warning("Ollama API returned an empty response.")
            return None
            
        logger.info(f"Successfully received response from Ollama model '{model}'.")
        return response_text
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Ollama API Error: {e}")
        return None
    except Exception as e:
        logger.exception("An unexpected error occurred in call_ollama_llm")
        return None


class LLMHandler:
    """Phase 2: LLM 핸들러 클래스 (완전 비동기 버전)"""
    
    def __init__(self, model: str = DEFAULT_MODEL, timeout: int = DEFAULT_TIMEOUT):
        """
        Args:
            model: 사용할 LLM 모델명
            timeout: 요청 타임아웃 시간 (초)
        """
        self.model = model
        self.timeout = timeout
        # 비동기 클라이언트를 클래스 속성으로 관리
        # 더 세밀한 timeout 설정 (연결, 읽기, 쓰기, 풀링 각각 설정)
        timeout_config = httpx.Timeout(
            connect=60.0,    # 연결 타임아웃 1분
            read=self.timeout,    # 읽기 타임아웃 (응답 대기시간)
            write=30.0,      # 쓰기 타임아웃 30초
            pool=10.0        # 풀링 타임아웃 10초
        )
        self.client = httpx.AsyncClient(
            base_url=OLLAMA_BASE_URL,
            timeout=timeout_config
        )
        
    async def generate_scenarios_async(self, prompt: str) -> Dict[str, Any]:
        """
        비동기 시나리오 생성 (완전 비동기)

        Args:
            prompt: 시나리오 생성 프롬프트

        Returns:
            생성된 시나리오 정보
        """
        logger.info("Generating scenarios using LLM (async)...")

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
            # format 필드 제거: scenario_v2.py와 동일한 자유 형식으로 변경
            # options 제거: 기본 설정 사용으로 scenario_v2.py와 통일
        }

        # DEBUG: 요청 페이로드 전체 로깅
        logger.info(f"[LLM DEBUG] Request payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        logger.info(f"[LLM DEBUG] Prompt length: {len(prompt)} characters")
        logger.info(f"[LLM DEBUG] Full prompt:\n{prompt[-300:]}")

        try:
            # httpx.AsyncClient를 사용한 비동기 POST 요청
            response_data = await _send_request_async(self.client, payload)

            # DEBUG: 원시 응답 데이터 전체 로깅
            # logger.info(f"[LLM DEBUG] Raw response data: {json.dumps(response_data, ensure_ascii=False, indent=2)}")

            # Ollama는 'response' 필드에 JSON 문자열을 담아주므로 한 번 더 파싱
            response_text = response_data.get('response', '{}').strip()

            # DEBUG: 응답 텍스트 상세 로깅
            logger.info(f"[LLM DEBUG] Response text length: {len(response_text)} characters")
            logger.info(f"[LLM DEBUG] Response text preview (first 1000 chars): {response_text[:1000]}...")
            if len(response_text) > 1000:
                logger.info(f"[LLM DEBUG] Response text end (last 500 chars): ...{response_text[-500:]}")

            if not response_text:
                logger.warning("Ollama API returned an empty response.")
                return {
                    "test_cases": [],
                    "description": "LLM 응답을 받을 수 없어 시나리오를 생성하지 못했습니다."
                }

            # scenario_v2.py와 동일한 JSON 블록 추출 로직 적용
            import re

            # <json> 태그 또는 ```json 코드 블록 모두 지원
            json_match = re.search(r'<json>(.*?)</json>', response_text, re.DOTALL)
            if not json_match:
                # markdown 스타일 ```json 블록도 시도
                json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)

            if not json_match:
                logger.error(f"[LLM DEBUG] JSON 블록을 찾을 수 없음. Full LLM Response: {response_text}")
                logger.error("[LLM DEBUG] JSON 블록을 찾을 수 없어 기본 시나리오를 반환합니다.")
                return {
                    "test_cases": [],
                    "description": "JSON 파싱 오류로 인한 기본 시나리오"
                }

            # JSON 파싱 및 복구 로직 (scenario_v2.py와 동일)
            try:
                json_str = json_match.group(1).strip()
                # 후행 콤마 제거
                json_str = json_str.rstrip(',')

                # 중괄호 불일치 보정
                if not json_str.endswith('}') and json_str.count('{') > json_str.count('}'):
                    json_str += '}'

                # 불완전한 배열 보정
                if '"Test Cases": [' in json_str and not json_str.count('[') == json_str.count(']'):
                    json_str += ']'

                result_json = json.loads(json_str)
                logger.info(f"[LLM DEBUG] JSON 파싱 성공: {len(result_json.get('Test Cases', []))}개 테스트 케이스")

                # scenario_v2.py 형식에서 generate_scenarios_async 형식으로 변환
                return {
                    "test_cases": result_json.get("Test Cases", []),
                    "description": result_json.get("Scenario Description", "LLM에서 생성된 시나리오입니다.")
                }

            except json.JSONDecodeError as recovery_error:
                logger.error(f"[LLM DEBUG] JSON 파싱 복구 실패: {str(recovery_error)}")
                logger.error(f"[LLM DEBUG] 파싱 시도된 JSON: {json_str[:200]}...")
                return {
                    "test_cases": [],
                    "description": "JSON 파싱 오류로 인한 기본 시나리오"
                }

        except OllamaAPIError as e:
            logger.error(f"Ollama API Error: {e}")
            return {
                "test_cases": [],
                "description": f"LLM API 호출 실패: {e}"
            }
        except Exception as e:
            logger.exception("An unexpected error occurred in generate_scenarios_async")
            return {
                "test_cases": [],
                "description": f"예기치 않은 오류 발생: {e}"
            }
    
    # 서버 종료 시 클라이언트 세션을 gracefully 닫기 위한 메서드
    async def close(self):
        """비동기 클라이언트 연결 종료"""
        if self.client:
            await self.client.aclose()
            logger.info("LLMHandler async client closed")
