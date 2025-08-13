import requests
import logging
from typing import Optional, Dict, Any

# Get a logger for this module
logger = logging.getLogger(__name__)

# Constants
DEFAULT_MODEL = "qwen3:8b"
DEFAULT_TIMEOUT = 600
OLLAMA_API_URL = "http://localhost:11434/api/generate"
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

def _send_request(payload: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    """Sends a request to the Ollama API and returns the response."""
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.exception("Ollama API request failed")
        raise OllamaAPIError(f"Error calling Ollama API: {e}")

def call_ollama_llm(
    prompt: str, 
    model: str = DEFAULT_MODEL, 
    format: str = "", 
    timeout: int = DEFAULT_TIMEOUT
) -> Optional[str]:
    """
    Calls the Ollama API with a given prompt.
    """
    logger.info(f"Calling Ollama model '{model}'...")
    
    try:
        payload = _create_payload(prompt, model, format)
        response_data = _send_request(payload, timeout)
        
        response_text = response_data.get('response', '').strip()
        if not response_text:
            logger.warning("Ollama API returned an empty response.")
            return None
            
        logger.info(f"Successfully received response from Ollama model '{model}'.")
        return response_text
    
    except OllamaAPIError as e:
        logger.error(f"Ollama API Error: {e}")
        return None
    except Exception as e:
        logger.exception("An unexpected error occurred in call_ollama_llm")
        return None
