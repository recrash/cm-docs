"""
v2 WebSocket 진행 상황 시스템 테스트
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import WebSocket
from pathlib import Path
import sys

# 프로젝트 경로 설정
sys.path.append(str(Path(__file__).resolve().parents[3]))

from app.main import app
from app.api.routers.v2.progress_websocket import (
    V2ConnectionManager, 
    v2_connection_manager,
    handle_v2_websocket
)
from app.api.routers.v2.models import V2ProgressMessage, V2GenerationStatus


class TestV2ConnectionManager:
    """V2ConnectionManager 테스트 클래스"""
    
    @pytest.fixture
    def manager(self):
        """테스트용 연결 매니저 fixture"""
        return V2ConnectionManager()
    
    @pytest.fixture
    def mock_websocket(self):
        """모킹된 WebSocket fixture"""
        mock_ws = Mock(spec=WebSocket)
        mock_ws.accept = AsyncMock()
        mock_ws.send_text = AsyncMock()
        mock_ws.close = AsyncMock()
        return mock_ws
    
    @pytest.mark.asyncio
    async def test_connect_new_client(self, manager, mock_websocket):
        """새로운 클라이언트 연결 테스트"""
        client_id = "test_client_connect"
        
        await manager.connect(client_id, mock_websocket)
        
        # WebSocket accept 호출 확인
        mock_websocket.accept.assert_called_once()
        
        # 연결이 등록되었는지 확인
        assert client_id in manager.connections
        assert manager.connections[client_id] == mock_websocket
        
        # 연결 상태 확인
        assert manager.is_connected(client_id) is True
        
        # 환영 메시지가 전송되었는지 확인
        mock_websocket.send_text.assert_called()
        sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_data["client_id"] == client_id
        assert sent_data["status"] == "received"
    
    @pytest.mark.asyncio
    async def test_connect_replace_existing_client(self, manager, mock_websocket):
        """기존 클라이언트 연결 교체 테스트"""
        client_id = "test_client_replace"
        
        # 기존 연결 설정
        old_websocket = Mock(spec=WebSocket)
        old_websocket.accept = AsyncMock()
        old_websocket.close = AsyncMock()
        old_websocket.send_text = AsyncMock()
        
        await manager.connect(client_id, old_websocket)
        
        # 새로운 연결로 교체
        await manager.connect(client_id, mock_websocket)
        
        # 기존 연결이 닫혔는지 확인
        old_websocket.close.assert_called()
        
        # 새 연결이 등록되었는지 확인
        assert manager.connections[client_id] == mock_websocket
    
    @pytest.mark.asyncio
    async def test_disconnect(self, manager, mock_websocket):
        """연결 해제 테스트"""
        client_id = "test_client_disconnect"
        
        # 연결 설정
        await manager.connect(client_id, mock_websocket)
        assert manager.is_connected(client_id) is True
        
        # 연결 해제
        await manager.disconnect(client_id)
        
        # 연결이 정리되었는지 확인
        assert client_id not in manager.connections
        assert manager.is_connected(client_id) is False
        mock_websocket.close.assert_called()
    
    @pytest.mark.asyncio
    async def test_send_progress_success(self, manager, mock_websocket):
        """진행 상황 전송 성공 테스트"""
        client_id = "test_client_progress"
        
        # 연결 설정
        await manager.connect(client_id, mock_websocket)
        
        # 진행 상황 메시지 생성
        progress_msg = V2ProgressMessage(
            client_id=client_id,
            status=V2GenerationStatus.ANALYZING_GIT,
            message="Git 분석 중...",
            progress=25.0
        )
        
        # 메시지 전송
        result = await manager.send_progress(client_id, progress_msg)
        
        # 전송 성공 확인
        assert result is True
        mock_websocket.send_text.assert_called()
        
        # 전송된 데이터 확인
        sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_data["client_id"] == client_id
        assert sent_data["status"] == "analyzing_git"
        assert sent_data["progress"] == 25.0
    
    @pytest.mark.asyncio
    async def test_send_progress_to_disconnected_client(self, manager):
        """연결되지 않은 클라이언트에게 메시지 전송 테스트"""
        client_id = "test_client_not_connected"
        
        progress_msg = V2ProgressMessage(
            client_id=client_id,
            status=V2GenerationStatus.ERROR,
            message="연결 없음",
            progress=0
        )
        
        # 연결되지 않은 클라이언트에게 전송
        result = await manager.send_progress(client_id, progress_msg)
        
        # 전송 실패 확인
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_progress_websocket_error(self, manager, mock_websocket):
        """WebSocket 전송 오류 테스트"""
        client_id = "test_client_error"
        
        # 연결 설정
        await manager.connect(client_id, mock_websocket)
        
        # WebSocket 전송 시 오류 발생하도록 설정
        from fastapi import WebSocketDisconnect
        mock_websocket.send_text.side_effect = WebSocketDisconnect()
        
        progress_msg = V2ProgressMessage(
            client_id=client_id,
            status=V2GenerationStatus.COMPLETED,
            message="완료",
            progress=100
        )
        
        # 메시지 전송 (오류 처리)
        result = await manager.send_progress(client_id, progress_msg)
        
        # 전송 실패 및 연결 정리 확인
        assert result is False
        assert client_id not in manager.connections
    
    @pytest.mark.asyncio
    async def test_send_to_all(self, manager):
        """모든 클라이언트에게 브로드캐스트 테스트"""
        # 여러 클라이언트 연결 설정
        clients = []
        for i in range(3):
            client_id = f"test_client_broadcast_{i}"
            mock_ws = Mock(spec=WebSocket)
            mock_ws.accept = AsyncMock()
            mock_ws.send_text = AsyncMock()
            mock_ws.close = AsyncMock()
            
            await manager.connect(client_id, mock_ws)
            clients.append((client_id, mock_ws))
        
        # 브로드캐스트 메시지
        broadcast_msg = V2ProgressMessage(
            client_id="broadcast",
            status=V2GenerationStatus.COMPLETED,
            message="브로드캐스트 테스트",
            progress=100
        )
        
        await manager.send_to_all(broadcast_msg)
        
        # 모든 클라이언트가 메시지를 받았는지 확인
        for client_id, mock_ws in clients:
            mock_ws.send_text.assert_called()
    
    @pytest.mark.asyncio
    async def test_cleanup_all(self, manager):
        """모든 연결 정리 테스트"""
        # 여러 클라이언트 연결 설정
        for i in range(3):
            client_id = f"test_client_cleanup_{i}"
            mock_ws = Mock(spec=WebSocket)
            mock_ws.accept = AsyncMock()
            mock_ws.send_text = AsyncMock()
            mock_ws.close = AsyncMock()
            
            await manager.connect(client_id, mock_ws)
        
        # 3개의 연결이 있는지 확인
        assert len(manager.connections) == 3
        
        # 모든 연결 정리
        await manager.cleanup_all()
        
        # 모든 연결이 정리되었는지 확인
        assert len(manager.connections) == 0
    
    def test_get_connected_clients(self, manager):
        """연결된 클라이언트 목록 조회 테스트"""
        # 초기 상태
        assert manager.get_connected_clients() == []
        
        # 직접 연결 추가 (테스트용)
        mock_ws1 = Mock()
        mock_ws2 = Mock()
        
        manager.connections["client1"] = mock_ws1
        manager.connections["client2"] = mock_ws2
        
        connected_clients = manager.get_connected_clients()
        assert len(connected_clients) == 2
        assert "client1" in connected_clients
        assert "client2" in connected_clients


class TestV2WebSocketIntegration:
    """v2 WebSocket 통합 테스트"""
    
    @pytest.fixture
    def client(self):
        """테스트 클라이언트 fixture"""
        return TestClient(app)
    
    def test_websocket_endpoint_exists(self, client):
        """WebSocket 엔드포인트 존재 확인"""
        # WebSocket 연결 테스트는 실제 연결을 만들어야 하므로 
        # 여기서는 엔드포인트가 등록되어 있는지만 확인
        
        # 라우터에 WebSocket 엔드포인트가 등록되어 있는지 확인
        from app.main import app
        websocket_routes = [route for route in app.routes if hasattr(route, 'path') and 'ws' in route.path]
        
        # v2 WebSocket 경로가 있는지 확인
        v2_ws_routes = [route for route in websocket_routes if '/api/webservice/v2/ws/progress' in route.path]
        assert len(v2_ws_routes) > 0
    
    @pytest.mark.asyncio
    async def test_handle_v2_websocket_flow(self):
        """WebSocket 핸들러 플로우 테스트"""
        mock_websocket = Mock(spec=WebSocket)
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        mock_websocket.receive_text = AsyncMock()
        mock_websocket.close = AsyncMock()
        
        # 정상 메시지 수신 후 연결 종료 시뮬레이션
        mock_websocket.receive_text.side_effect = [
            "ping",  # 첫 번째 메시지
            Exception("WebSocketDisconnect")  # 연결 종료
        ]
        
        client_id = "test_websocket_handler"
        
        # WebSocket 핸들러 실행
        try:
            await handle_v2_websocket(mock_websocket, client_id)
        except Exception:
            pass  # WebSocketDisconnect 예외 무시
        
        # WebSocket이 수락되었는지 확인
        mock_websocket.accept.assert_called_once()


class TestV2ProgressMessage:
    """V2ProgressMessage 모델 테스트"""
    
    def test_progress_message_creation(self):
        """진행 상황 메시지 생성 테스트"""
        msg = V2ProgressMessage(
            client_id="test_client",
            status=V2GenerationStatus.CALLING_LLM,
            message="LLM 호출 중...",
            progress=50.5
        )
        
        assert msg.client_id == "test_client"
        assert msg.status == V2GenerationStatus.CALLING_LLM
        assert msg.message == "LLM 호출 중..."
        assert msg.progress == 50.5
        assert msg.details is None
        assert msg.result is None
    
    def test_progress_message_with_details(self):
        """세부 정보가 있는 진행 상황 메시지 테스트"""
        details = {"llm_response_time": 2.5, "prompt_size": 1024}
        
        msg = V2ProgressMessage(
            client_id="test_client",
            status=V2GenerationStatus.COMPLETED,
            message="완료",
            progress=100.0,
            details=details
        )
        
        assert msg.details == details
        assert msg.details["llm_response_time"] == 2.5
    
    def test_progress_message_with_result(self):
        """결과가 있는 진행 상황 메시지 테스트"""
        result = {
            "filename": "test_result.xlsx",
            "description": "테스트 시나리오",
            "download_url": "/api/webservice/files/download/excel/test_result.xlsx"
        }
        
        msg = V2ProgressMessage(
            client_id="test_client",
            status=V2GenerationStatus.COMPLETED,
            message="완료",
            progress=100.0,
            result=result
        )
        
        assert msg.result == result
        assert msg.result["filename"] == "test_result.xlsx"
    
    def test_progress_message_validation(self):
        """진행 상황 메시지 유효성 검증 테스트"""
        # progress 범위 테스트
        with pytest.raises(ValueError):
            V2ProgressMessage(
                client_id="test",
                status=V2GenerationStatus.RECEIVED,
                message="테스트",
                progress=-10  # 0 미만
            )
        
        with pytest.raises(ValueError):
            V2ProgressMessage(
                client_id="test",
                status=V2GenerationStatus.RECEIVED,
                message="테스트",
                progress=150  # 100 초과
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])