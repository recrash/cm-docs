"""
v2 API 전용 Pydantic 모델
CLI 연동을 위한 데이터 모델 정의
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from enum import Enum


class V2GenerationStatus(str, Enum):
    """v2 생성 상태 열거형"""
    RECEIVED = "received"           # 요청 수신
    ANALYZING_GIT = "analyzing_git" # Git 분석 중
    STORING_RAG = "storing_rag"     # RAG 저장 중
    CALLING_LLM = "calling_llm"     # LLM 호출 중
    PARSING_RESPONSE = "parsing_response"  # 응답 파싱 중
    GENERATING_EXCEL = "generating_excel"  # Excel 생성 중
    COMPLETED = "completed"         # 완료
    ERROR = "error"                 # 오류


class V2GenerationRequest(BaseModel):
    """CLI에서 보내는 생성 요청"""
    client_id: str = Field(..., description="고유 클라이언트 식별자")
    repo_path: str = Field(..., description="Git 저장소 경로")
    use_performance_mode: bool = Field(True, description="성능 최적화 모드 사용 여부")


class V2ProgressMessage(BaseModel):
    """WebSocket을 통해 전송되는 진행 상황 메시지"""
    client_id: str = Field(..., description="클라이언트 식별자")
    status: V2GenerationStatus = Field(..., description="현재 상태")
    message: str = Field(..., description="상태 설명 메시지")
    progress: float = Field(..., ge=0, le=100, description="진행률 (0-100)")
    details: Optional[Dict[str, Any]] = Field(None, description="추가 세부 정보")
    result: Optional[Dict[str, Any]] = Field(None, description="완료 시 결과 데이터")


class V2GenerationResponse(BaseModel):
    """v2 생성 요청에 대한 즉시 응답"""
    client_id: str = Field(..., description="클라이언트 식별자")
    status: str = Field("accepted", description="요청 수락 상태")
    message: str = Field("생성 작업이 시작되었습니다.", description="응답 메시지")
    websocket_url: str = Field(..., description="진행 상황을 확인할 WebSocket URL")


class V2ResultData(BaseModel):
    """완료 시 전달되는 결과 데이터"""
    filename: str = Field(..., description="생성된 Excel 파일명")
    description: str = Field(..., description="시나리오 설명")
    download_url: str = Field(..., description="파일 다운로드 URL")
    # 통계 정보 추가
    llm_response_time: float = Field(0.0, description="LLM 응답 시간 (초)")
    prompt_size: int = Field(0, description="프롬프트 크기 (문자 수)")
    added_chunks: int = Field(0, description="RAG에 추가된 청크 수")
    # 테스트 케이스 데이터 추가
    test_cases: list = Field(default_factory=list, description="테스트 케이스 목록")
    test_scenario_name: str = Field("", description="테스트 시나리오 이름")