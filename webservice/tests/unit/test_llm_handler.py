"""
llm_handler.py 모듈 테스트
"""
import pytest
import requests
from unittest.mock import Mock, patch
from app.core.llm_handler import call_ollama_llm


class TestLLMHandler:
    """LLM 핸들러 테스트"""
    
    @patch('src.llm_handler.requests.post')
    def test_successful_llm_call(self, mock_post, mock_ollama_response):
        """성공적인 LLM 호출 테스트"""
        mock_response = Mock()
        mock_response.json.return_value = mock_ollama_response
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = call_ollama_llm("test prompt", "qwen3:8b")
        
        assert result is not None
        assert "Test Cases" in result
        mock_post.assert_called_once()
        
        # 호출 인자 검증
        call_args = mock_post.call_args
        assert call_args[1]['json']['model'] == "qwen3:8b"
        assert call_args[1]['json']['prompt'] == "test prompt"
        assert call_args[1]['json']['stream'] == False
    
    @patch('src.llm_handler.requests.post')
    def test_llm_call_with_json_format(self, mock_post, mock_ollama_response):
        """JSON 형식 LLM 호출 테스트"""
        mock_response = Mock()
        mock_response.json.return_value = mock_ollama_response
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = call_ollama_llm("test prompt", "qwen3:8b", format="json")
        
        assert result is not None
        
        # JSON 형식 옵션이 포함되었는지 확인
        call_args = mock_post.call_args
        assert call_args[1]['json']['format'] == 'json'
    
    @patch('src.llm_handler.requests.post')
    def test_llm_call_with_custom_timeout(self, mock_post, mock_ollama_response):
        """커스텀 타임아웃 LLM 호출 테스트"""
        mock_response = Mock()
        mock_response.json.return_value = mock_ollama_response
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = call_ollama_llm("test prompt", timeout=300)
        
        assert result is not None
        
        # 타임아웃 설정 확인
        call_args = mock_post.call_args
        assert call_args[1]['timeout'] == 300
    
    @patch('src.llm_handler.requests.post')
    def test_llm_call_network_error(self, mock_post, capsys):
        """네트워크 오류 테스트"""
        mock_post.side_effect = requests.exceptions.RequestException("Network error")
        
        result = call_ollama_llm("test prompt")
        
        assert result is None
        captured = capsys.readouterr()
        assert "Ollama API 호출 중 오류 발생" in captured.out
    
    @patch('src.llm_handler.requests.post')
    def test_llm_call_timeout_error(self, mock_post, capsys):
        """타임아웃 오류 테스트"""
        mock_post.side_effect = requests.exceptions.Timeout("Timeout error")
        
        result = call_ollama_llm("test prompt", timeout=1)
        
        assert result is None
        captured = capsys.readouterr()
        assert "Ollama API 호출 중 오류 발생" in captured.out
    
    @patch('src.llm_handler.requests.post')
    def test_llm_call_http_error(self, mock_post, capsys):
        """HTTP 오류 테스트"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_post.return_value = mock_response
        
        result = call_ollama_llm("test prompt")
        
        assert result is None
        captured = capsys.readouterr()
        assert "Ollama API 호출 중 오류 발생" in captured.out
    
    @patch('src.llm_handler.requests.post')
    def test_llm_call_empty_response(self, mock_post):
        """빈 응답 테스트"""
        mock_response = Mock()
        mock_response.json.return_value = {"response": ""}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = call_ollama_llm("test prompt")
        
        assert result == ""
    
    @patch('src.llm_handler.requests.post')
    def test_llm_call_missing_response_field(self, mock_post):
        """응답 필드 누락 테스트"""
        mock_response = Mock()
        mock_response.json.return_value = {"other_field": "value"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = call_ollama_llm("test prompt")
        
        assert result == ""