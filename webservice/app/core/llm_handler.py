import httpx
import json
import logging
from typing import Optional, Dict, Any

# Get a logger for this module
logger = logging.getLogger(__name__)

# Constants
DEFAULT_MODEL = "qwen3:8b"
DEFAULT_TIMEOUT = 600
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
        self.client = httpx.AsyncClient(
            base_url=OLLAMA_BASE_URL, 
            timeout=float(self.timeout)
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
            "stream": False,
            "format": "json"  # JSON 포맷 요청
        }

        try:
            # httpx.AsyncClient를 사용한 비동기 POST 요청
            response_data = await _send_request_async(self.client, payload)
            
            # Ollama는 'response' 필드에 JSON 문자열을 담아주므로 한 번 더 파싱
            response_text = response_data.get('response', '{}').strip()
            
            if not response_text:
                logger.warning("Ollama API returned an empty response.")
                return {
                    "test_cases": [],
                    "description": "LLM 응답을 받을 수 없어 시나리오를 생성하지 못했습니다."
                }
            
            # JSON 파싱 시도
            try:
                result = json.loads(response_text)
                
                # 기본 구조 확인 및 생성
                if not isinstance(result, dict):
                    result = {"test_cases": [], "description": response_text}
                
                if "test_cases" not in result:
                    result["test_cases"] = []
                
                if "description" not in result:
                    result["description"] = "LLM에서 생성된 시나리오입니다."
                
                logger.info(f"Successfully generated {len(result.get('test_cases', []))} test scenarios")
                return result
                
            except json.JSONDecodeError:
                logger.warning("Failed to parse LLM JSON response, using raw text")
                return {
                    "test_cases": [{"case": response_text}],
                    "description": f"LLM 응답 파싱 실패: {response_text}"
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
