"""
v2 WebSocket 진행 상황 관리 시스템
클라이언트별 WebSocket 연결 및 메시지 브로드캐스트 관리
"""

import logging
import json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Optional
from pathlib import Path
from websockets.exceptions import ConnectionClosedError

# 프로젝트 경로 설정
import sys
sys.path.append(str(Path(__file__).resolve().parents[3]))

from .models import V2ProgressMessage

# 로거 설정
logger = logging.getLogger(__name__)


class V2ConnectionManager:
    """v2 WebSocket 연결 관리자"""
    
    def __init__(self):
        # 클라이언트별 WebSocket 연결 저장
        self.connections: Dict[str, WebSocket] = {}
        # 연결 정리를 위한 락
        self._lock = asyncio.Lock()
    
    async def connect(self, client_id: str, websocket: WebSocket):
        """새로운 WebSocket 연결 등록"""
        try:
            await websocket.accept()
            
            async with self._lock:
                # 기존 연결이 있다면 정리
                if client_id in self.connections:
                    old_ws = self.connections[client_id]
                    try:
                        await old_ws.close()
                        logger.info(f"기존 연결을 정리했습니다: {client_id}")
                    except:
                        pass
                
                # 새 연결 등록
                self.connections[client_id] = websocket
                logger.info(f"WebSocket 연결 등록: {client_id}")
                
                # 연결 확인 메시지 전송
                welcome_msg = V2ProgressMessage(
                    client_id=client_id,
                    status="received",
                    message="WebSocket 연결이 설정되었습니다.",
                    progress=0
                )
                await self.send_progress(client_id, welcome_msg)
                
        except Exception as e:
            logger.error(f"WebSocket 연결 설정 실패 {client_id}: {e}")
            raise

    async def disconnect(self, client_id: str):
        """WebSocket 연결 정리"""
        async with self._lock:
            if client_id in self.connections:
                try:
                    websocket = self.connections[client_id]
                    await websocket.close()
                except:
                    pass
                finally:
                    del self.connections[client_id]
                    logger.info(f"WebSocket 연결 정리: {client_id}")

    def is_connected(self, client_id: str) -> bool:
        """특정 클라이언트의 연결 상태 확인"""
        return client_id in self.connections

    async def send_progress(self, client_id: str, progress: V2ProgressMessage):
        """특정 클라이언트에게 진행 상황 메시지 전송"""
        if client_id not in self.connections:
            logger.warning(f"연결되지 않은 클라이언트에게 메시지 전송 시도: {client_id}")
            return False

        websocket = self.connections[client_id]
        
        try:
            # Pydantic 모델을 JSON으로 직렬화
            message_dict = progress.model_dump()
            message_json = json.dumps(message_dict, ensure_ascii=False)
            
            await websocket.send_text(message_json)
            logger.debug(f"진행 상황 전송 완료 {client_id}: {progress.status} ({progress.progress}%)")
            return True
            
        except WebSocketDisconnect:
            logger.info(f"클라이언트 연결 끊김 감지: {client_id}")
            await self.disconnect(client_id)
            return False
            
        except Exception as e:
            logger.error(f"진행 상황 전송 실패 {client_id}: {e}")
            await self.disconnect(client_id)
            return False

    async def send_to_all(self, progress: V2ProgressMessage):
        """모든 연결된 클라이언트에게 메시지 브로드캐스트"""
        if not self.connections:
            logger.debug("브로드캐스트할 연결이 없습니다.")
            return

        # 연결된 모든 클라이언트에게 전송
        disconnected_clients = []
        
        for client_id, websocket in list(self.connections.items()):
            try:
                message_dict = progress.model_dump()
                message_json = json.dumps(message_dict, ensure_ascii=False)
                await websocket.send_text(message_json)
                
            except (WebSocketDisconnect, ConnectionClosedError):
                disconnected_clients.append(client_id)
                logger.info(f"브로드캐스트 중 연결 끊김 감지: {client_id}")
                
            except Exception as e:
                disconnected_clients.append(client_id)
                logger.error(f"브로드캐스트 전송 실패 {client_id}: {e}")
        
        # 끊어진 연결 정리
        for client_id in disconnected_clients:
            await self.disconnect(client_id)

    def get_connected_clients(self) -> list:
        """현재 연결된 모든 클라이언트 ID 반환"""
        return list(self.connections.keys())

    async def cleanup_all(self):
        """모든 연결 정리 (서버 종료 시 사용)"""
        logger.info("모든 WebSocket 연결을 정리합니다.")
        
        for client_id in list(self.connections.keys()):
            await self.disconnect(client_id)
        
        logger.info("WebSocket 연결 정리 완료")


# 전역 연결 관리자 인스턴스
v2_connection_manager = V2ConnectionManager()


async def handle_v2_websocket(websocket: WebSocket, client_id: str):
    """
    v2 WebSocket 연결 핸들러
    
    Args:
        websocket: WebSocket 연결 객체
        client_id: 클라이언트 식별자
    """
    logger.info(f"v2 WebSocket 연결 시도: {client_id}")
    
    try:
        # 연결 설정
        await v2_connection_manager.connect(client_id, websocket)
        
        # 연결 유지 루프
        while True:
            try:
                # 클라이언트로부터 메시지 수신 (연결 상태 확인용)
                data = await websocket.receive_text()
                logger.debug(f"클라이언트 메시지 수신 {client_id}: {data}")
                
                # 핑/퐁이나 상태 확인 메시지 처리
                if data.strip().lower() in ['ping', 'status']:
                    pong_msg = V2ProgressMessage(
                        client_id=client_id,
                        status="received",
                        message="연결 상태 정상",
                        progress=0
                    )
                    await v2_connection_manager.send_progress(client_id, pong_msg)
                    
            except WebSocketDisconnect:
                logger.info(f"클라이언트가 연결을 종료했습니다: {client_id}")
                break
                
            except Exception as e:
                logger.error(f"WebSocket 메시지 처리 중 오류 {client_id}: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket 연결 처리 중 오류 {client_id}: {e}")
        
    finally:
        # 연결 정리
        await v2_connection_manager.disconnect(client_id)
        logger.info(f"WebSocket 연결 종료: {client_id}")