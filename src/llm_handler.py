# src/llm_handler.py
import requests

def call_ollama_llm(prompt, model="qwen3:14b", format="", timeout=600):
    """Ollama API를 호출하는 범용 함수."""
    print(f"...Ollama 모델({model}) 호출 중...")
    ollama_api_url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    if format == 'json':
        payload['format'] = 'json'
        
    try:
        # --- [수정] 전달받은 timeout 값을 사용 ---
        response = requests.post(ollama_api_url, json=payload, timeout=timeout)
        response.raise_for_status()
        response_data = response.json()
        return response_data.get('response', '').strip()
    except requests.exceptions.RequestException as e:
        print(f"Ollama API 호출 중 오류 발생: {e}")
        return None