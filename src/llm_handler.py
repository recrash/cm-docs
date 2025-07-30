# src/llm_handler.py
import requests
from typing import Optional, Dict, Any

# 상수 정의
DEFAULT_MODEL = "qwen3:8b"
DEFAULT_TIMEOUT = 600
OLLAMA_API_URL = "http://localhost:11434/api/generate"
JSON_FORMAT = "json"


class OllamaAPIError(Exception):
    """올라마 API 호출 오류"""
    pass


def _create_payload(prompt: str, model: str, format_type: str) -> Dict[str, Any]:
    """
    Ollama API 요청 페이로드를 생성합니다.
    
    Args:
        prompt: LLM에 전달할 프롬프트
        model: 사용할 모델명
        format_type: 응답 형식 (빈 문자열 또는 'json')
    
    Returns:
        API 요청 페이로드 딕셔너리
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    
    if format_type == JSON_FORMAT:
        payload['format'] = JSON_FORMAT
    
    return payload


def _send_request(payload: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    """
    Ollama API에 요청을 전송하고 응답을 반환합니다.
    
    Args:
        payload: API 요청 페이로드
        timeout: 타임아웃 (초)
    
    Returns:
        API 응답 데이터
    
    Raises:
        OllamaAPIError: API 호출 실패 시
    """
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise OllamaAPIError(f"Ollama API 호출 중 오류 발생: {e}")


def call_ollama_llm(prompt: str, model: str = DEFAULT_MODEL, format: str = "", timeout: int = DEFAULT_TIMEOUT) -> Optional[str]:
    """
    Ollama API를 호출하는 범용 함수.
    
    Args:
        prompt: LLM에 전달할 프롬프트
        model: 사용할 모델명 (기본값: qwen3:8b)
        format: 응답 형식 ('빈 문자열' 또는 'json')
        timeout: 타임아웃 시간 (초, 기본값: 600)
    
    Returns:
        LLM 응답 텍스트 또는 None (오류 시)
    """
    print(f"...Ollama 모델({model}) 호출 중...")
    
    try:
        payload = _create_payload(prompt, model, format)
        response_data = _send_request(payload, timeout)
        return response_data.get('response', '').strip()
    
    except OllamaAPIError as e:
        print(str(e))
        return None