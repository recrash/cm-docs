"""
Phase 2 확장된 URL 파라미터 파싱 테스트

sessionId와 metadata 파라미터를 포함한 새로운 URL 형식 테스트
"""

import pytest
import tempfile
import shutil
import urllib.parse
import base64
import json
from pathlib import Path
from unittest.mock import Mock, patch
import sys

from ts_cli.main import handle_url_protocol, parse_url_parameters


class TestPhase2URLParsing:
    """Phase 2 확장된 URL 파라미터 파싱 테스트"""
    
    @pytest.fixture
    def temp_directory(self):
        """임시 디렉토리 생성"""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            yield temp_dir
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_parse_url_parameters_legacy_format(self, temp_directory):
        """기존 URL 형식 파싱 테스트 (clientId만)"""
        test_url = f"testscenariomaker://{temp_directory}?clientId=test123"
        
        repo_path, client_id, session_id, metadata = parse_url_parameters(test_url)
        
        assert repo_path == temp_directory
        assert client_id == "test123"
        assert session_id is None
        assert metadata is None
    
    def test_parse_url_parameters_full_format(self, temp_directory):
        """확장된 URL 형식 파싱 테스트 (모든 파라미터)"""
        # 메타데이터 준비
        metadata_dict = {
            "change_id": "CM-20240101-001",
            "system": "테스트시스템",
            "title": "테스트 변경사항"
        }
        metadata_json = json.dumps(metadata_dict, ensure_ascii=False)
        metadata_b64 = base64.b64encode(metadata_json.encode('utf-8')).decode('ascii')
        
        test_url = f"testscenariomaker://{temp_directory}?clientId=test123&sessionId=session456&metadata={metadata_b64}"
        
        repo_path, client_id, session_id, metadata = parse_url_parameters(test_url)
        
        assert repo_path == temp_directory
        assert client_id == "test123"
        assert session_id == "session456"
        assert metadata == metadata_dict
        assert metadata["change_id"] == "CM-20240101-001"
        assert metadata["system"] == "테스트시스템"
    
    def test_parse_url_parameters_minimal_full_generation(self, temp_directory):
        """전체 문서 생성 최소 파라미터 테스트 (sessionId + metadata만)"""
        # 최소 메타데이터
        metadata_dict = {"change_id": "CM-TEST"}
        metadata_json = json.dumps(metadata_dict)
        metadata_b64 = base64.b64encode(metadata_json.encode('utf-8')).decode('ascii')
        
        test_url = f"testscenariomaker://{temp_directory}?sessionId=session789&metadata={metadata_b64}"
        
        repo_path, client_id, session_id, metadata = parse_url_parameters(test_url)
        
        assert repo_path == temp_directory
        assert client_id is None
        assert session_id == "session789"
        assert metadata == metadata_dict
    
    def test_parse_url_parameters_invalid_metadata_base64(self, temp_directory):
        """잘못된 Base64 메타데이터 처리 테스트"""
        test_url = f"testscenariomaker://{temp_directory}?sessionId=session123&metadata=invalid_base64!!!"
        
        with pytest.raises(ValueError, match="metadata 파라미터 디코딩 실패"):
            parse_url_parameters(test_url)
    
    def test_parse_url_parameters_invalid_metadata_json(self, temp_directory):
        """잘못된 JSON 메타데이터 처리 테스트"""
        # 올바른 Base64이지만 잘못된 JSON
        invalid_json = base64.b64encode(b"invalid json content").decode('ascii')
        test_url = f"testscenariomaker://{temp_directory}?sessionId=session123&metadata={invalid_json}"
        
        with pytest.raises(ValueError, match="metadata 파라미터 디코딩 실패"):
            parse_url_parameters(test_url)
    
    def test_parse_url_parameters_korean_metadata(self, temp_directory):
        """한글이 포함된 메타데이터 파싱 테스트"""
        metadata_dict = {
            "change_id": "CM-20240101-한글테스트",
            "system": "한글시스템명",
            "title": "한글 제목입니다",
            "requester": "김개발"
        }
        metadata_json = json.dumps(metadata_dict, ensure_ascii=False)
        metadata_b64 = base64.b64encode(metadata_json.encode('utf-8')).decode('ascii')
        
        test_url = f"testscenariomaker://{temp_directory}?sessionId=한글세션&metadata={metadata_b64}"
        
        repo_path, client_id, session_id, metadata = parse_url_parameters(test_url)
        
        assert session_id == "한글세션"
        assert metadata["system"] == "한글시스템명"
        assert metadata["title"] == "한글 제목입니다"
        assert metadata["requester"] == "김개발"
    
    @patch('ts_cli.main.make_api_request')
    @patch('asyncio.run')
    @patch('ts_cli.main.load_server_config')
    @patch('ts_cli.main.validate_repository_path')
    @patch('ts_cli.main.collect_debug_info')
    @patch('ts_cli.main.log_debug_info')
    def test_handle_url_protocol_legacy_mode(
        self, mock_log_debug, mock_collect_debug, mock_validate_path,
        mock_load_server, mock_asyncio_run, mock_make_api_request, temp_directory
    ):
        """레거시 모드 워크플로우 테스트 (clientId만 있는 경우)"""
        mock_load_server.return_value = "http://localhost:8000"
        mock_make_api_request.return_value = True
        mock_collect_debug.return_value = {'debug_file': '/tmp/debug.log'}
        
        test_url = f"testscenariomaker://{temp_directory}?clientId=test123"
        
        with patch('sys.argv', ['ts-cli', test_url]), \
             patch('ts_cli.main.console') as mock_console, \
             patch('sys.exit') as mock_exit:
            
            handle_url_protocol()
            
            # 레거시 모드 메시지 확인
            mock_console.print.assert_any_call("[bold cyan]Legacy Scenario Generation Mode[/bold cyan]")
            
            # make_api_request 호출 확인
            mock_make_api_request.assert_called_once()
            
            # asyncio.run은 호출되지 않아야 함
            mock_asyncio_run.assert_not_called()
            
            # 성공 메시지 확인
            mock_console.print.assert_any_call("[bold green]Repository analysis completed successfully.[/bold green]")
            mock_exit.assert_called_with(0)
    
    @patch('ts_cli.main.handle_full_generation')
    @patch('asyncio.run')
    @patch('ts_cli.main.load_server_config')
    @patch('ts_cli.main.validate_repository_path')
    @patch('ts_cli.main.collect_debug_info')
    @patch('ts_cli.main.log_debug_info')
    def test_handle_url_protocol_full_generation_mode(
        self, mock_log_debug, mock_collect_debug, mock_validate_path,
        mock_load_server, mock_asyncio_run, mock_handle_full_generation, temp_directory
    ):
        """전체 문서 생성 모드 워크플로우 테스트 (sessionId + metadata 있는 경우)"""
        mock_load_server.return_value = "http://localhost:8000"
        mock_handle_full_generation.return_value = True
        mock_asyncio_run.return_value = True
        mock_collect_debug.return_value = {'debug_file': '/tmp/debug.log'}
        
        # 메타데이터 준비
        metadata_dict = {"change_id": "CM-TEST", "system": "테스트"}
        metadata_json = json.dumps(metadata_dict, ensure_ascii=False)
        metadata_b64 = base64.b64encode(metadata_json.encode('utf-8')).decode('ascii')
        
        test_url = f"testscenariomaker://{temp_directory}?sessionId=session123&metadata={metadata_b64}"
        
        with patch('sys.argv', ['ts-cli', test_url]), \
             patch('ts_cli.main.console') as mock_console, \
             patch('sys.exit') as mock_exit:
            
            handle_url_protocol()
            
            # 전체 문서 생성 모드 메시지 확인
            mock_console.print.assert_any_call("[bold magenta]Full Document Generation Mode[/bold magenta]")
            
            # asyncio.run 호출 확인
            mock_asyncio_run.assert_called_once()
            
            # 성공 메시지 확인
            mock_console.print.assert_any_call("[bold green]Repository analysis completed successfully.[/bold green]")
            mock_exit.assert_called_with(0)
    
    def test_parse_url_parameters_url_encoded_korean_path(self):
        """URL 인코딩된 한글 경로 파싱 테스트"""
        # 한글이 포함된 경로
        korean_path = Path("/Users/개발자/프로젝트/테스트저장소")
        encoded_path = urllib.parse.quote(str(korean_path))
        
        metadata_dict = {"change_id": "CM-KOREAN"}
        metadata_json = json.dumps(metadata_dict)
        metadata_b64 = base64.b64encode(metadata_json.encode('utf-8')).decode('ascii')
        
        test_url = f"testscenariomaker://{encoded_path}?sessionId=한글세션&metadata={metadata_b64}"
        
        repo_path, client_id, session_id, metadata = parse_url_parameters(test_url)
        
        assert repo_path == korean_path
        assert session_id == "한글세션"
        assert metadata["change_id"] == "CM-KOREAN"
    
    def test_parse_url_parameters_complex_metadata(self, temp_directory):
        """복잡한 메타데이터 구조 파싱 테스트"""
        complex_metadata = {
            "change_id": "CM-20240101-COMPLEX",
            "system": "복잡한시스템",
            "title": "복잡한 변경사항",
            "requester": "김개발자",
            "details": {
                "summary": "상세 요약",
                "risk": "중간",
                "impact": ["시스템A", "시스템B"]
            },
            "dates": {
                "created": "2024-01-01",
                "scheduled": "2024-01-15"
            },
            "flags": {
                "urgent": True,
                "tested": False,
                "approved": None
            }
        }
        
        metadata_json = json.dumps(complex_metadata, ensure_ascii=False)
        metadata_b64 = base64.b64encode(metadata_json.encode('utf-8')).decode('ascii')
        
        test_url = f"testscenariomaker://{temp_directory}?sessionId=complex_session&metadata={metadata_b64}"
        
        repo_path, client_id, session_id, metadata = parse_url_parameters(test_url)
        
        assert metadata["change_id"] == "CM-20240101-COMPLEX"
        assert metadata["details"]["risk"] == "중간"
        assert metadata["details"]["impact"] == ["시스템A", "시스템B"]
        assert metadata["flags"]["urgent"] is True
        assert metadata["flags"]["tested"] is False
        assert metadata["flags"]["approved"] is None