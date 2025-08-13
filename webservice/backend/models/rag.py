"""
RAG 시스템 관련 Pydantic 모델
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class RAGInfo(BaseModel):
    """RAG 시스템 정보"""
    chroma_info: Dict[str, Any] = {}
    chunk_size: int = 0
    documents: Dict[str, Any] = {}

class IndexingRequest(BaseModel):
    """문서 인덱싱 요청"""
    force_reindex: bool = Field(default=False, description="강제 재인덱싱 여부")

class IndexingResult(BaseModel):
    """인덱싱 결과"""
    status: str
    indexed_count: int = 0
    total_chunks_added: int = 0
    message: Optional[str] = None

class DocumentsInfo(BaseModel):
    """문서 정보"""
    enabled: bool = False
    folder_path: Optional[str] = None
    supported_files: int = 0
    total_files: int = 0
    file_types: Dict[str, int] = {}