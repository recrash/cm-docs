import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

router = APIRouter()
logger = logging.getLogger("frontend") # Use the 'frontend' logger
backend_logger = logging.getLogger(__name__) # Backend logger for this module

class FrontendLog(BaseModel):
    level: str
    message: str
    meta: Optional[Dict[str, Any]] = None

@router.post("/log")
async def receive_frontend_log(entry: FrontendLog):
    """
    Receives log entries from the frontend and records them.
    """
    backend_logger.info(f"프론트엔드 로그 수신: level={entry.level}, message_length={len(entry.message)}")
    
    try:
        log_level = getattr(logging, entry.level.upper(), logging.INFO)
        
        # Format the message to include metadata
        log_message = entry.message
        if entry.meta:
            log_message += f" | meta: {entry.meta}"
            
        logger.log(log_level, log_message)
        
        backend_logger.debug(f"프론트엔드 로그 처리 성공: level={entry.level}")
        return {"status": "ok"}
        
    except Exception as e:
        # If logging from frontend fails, log it to the backend log
        backend_logger.error(f"프론트엔드 로그 처리 실패: level={entry.level}, error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process log entry")
