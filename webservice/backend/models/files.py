"""
파일 처리 관련 Pydantic 모델들
"""

from pydantic import BaseModel, Field
from typing import Optional, List

class RepoPathValidationRequest(BaseModel):
    """Git 저장소 경로 검증 요청 모델"""
    repo_path: str = Field(..., description="검증할 Git 저장소 경로")
    
class RepoPathValidationResponse(BaseModel):
    """Git 저장소 경로 검증 응답 모델"""
    valid: bool = Field(..., description="경로 유효성 여부")
    message: str = Field(..., description="검증 결과 메시지")

class FileInfo(BaseModel):
    """파일 정보 모델"""
    filename: str = Field(..., description="파일명")
    size: int = Field(..., description="파일 크기 (bytes)")
    created_at: float = Field(..., description="생성 시간 (timestamp)")
    modified_at: float = Field(..., description="수정 시간 (timestamp)")

class FileListResponse(BaseModel):
    """파일 목록 응답 모델"""
    files: List[FileInfo] = Field(..., description="파일 목록")

class FileUploadResponse(BaseModel):
    """파일 업로드 응답 모델"""
    message: str = Field(..., description="업로드 결과 메시지")
    filename: str = Field(..., description="업로드된 파일명")
    temp_path: str = Field(..., description="임시 파일 경로")
    size: int = Field(..., description="파일 크기 (bytes)")

class FileDeleteResponse(BaseModel):
    """파일 삭제 응답 모델"""
    message: str = Field(..., description="삭제 결과 메시지")