"""
v2 API 전용 Pydantic 모델
CLI 연동을 위한 데이터 모델 정의
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime


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


class FullGenerationStatus(str, Enum):
    """Phase 2: 전체 문서 생성 상태 열거형"""
    RECEIVED = "received"                    # 요청 수신
    ANALYZING_VCS = "analyzing_vcs"          # VCS 분석 중 (Git/SVN)
    GENERATING_SCENARIOS = "generating_scenarios"  # 시나리오 생성 중
    GENERATING_WORD_DOC = "generating_word_doc"    # Word 문서 생성 중
    GENERATING_EXCEL_LIST = "generating_excel_list"  # Excel 목록 생성 중
    GENERATING_BASE_SCENARIOS = "generating_base_scenarios"  # 기본 시나리오 생성 중
    MERGING_EXCEL = "merging_excel"          # Excel 파일 병합 중
    COMPLETED = "completed"                  # 완료
    ERROR = "error"                          # 오류


class V2GenerationRequest(BaseModel):
    """CLI에서 보내는 생성 요청"""
    client_id: str = Field(..., description="고유 클라이언트 식별자")
    repo_path: str = Field(..., description="저장소 경로")
    use_performance_mode: bool = Field(True, description="성능 최적화 모드 사용 여부")
    is_valid_repo: bool = Field(True, description="CLI에서 검증한 저장소 유효성")
    vcs_type: str = Field("git", description="VCS 타입 (git 또는 svn)")
    changes_text: str = Field(..., description="CLI에서 분석한 변경사항 텍스트")


class FullGenerationRequest(BaseModel):
    """Phase 2: 전체 문서 생성 요청"""
    session_id: str = Field(..., min_length=1, description="세션 ID (마스터 키)")
    vcs_analysis_text: str = Field(..., description="VCS 분석 텍스트 (Git/SVN 공통)")
    metadata_json: Dict[str, Any] = Field(..., description="프론트엔드에서 전달받은 메타데이터")
    
    class Config:
        schema_extra = {
            "example": {
                "session_id": "session_20240101_123456",
                "git_analysis_text": "변경사항 분석 결과...",
                "metadata_json": {
                    "change_id": "CM-20240101-001",
                    "system": "테스트시스템", 
                    "title": "테스트 변경사항",
                    "requester": "김개발자"
                }
            }
        }


class V2ProgressMessage(BaseModel):
    """WebSocket을 통해 전송되는 진행 상황 메시지"""
    client_id: str = Field(..., description="클라이언트 식별자")
    status: V2GenerationStatus = Field(..., description="현재 상태")
    message: str = Field(..., description="상태 설명 메시지")
    progress: float = Field(..., ge=0, le=100, description="진행률 (0-100)")
    details: Optional[Dict[str, Any]] = Field(None, description="추가 세부 정보")
    result: Optional[Dict[str, Any]] = Field(None, description="완료 시 결과 데이터")


class FullGenerationProgressMessage(BaseModel):
    """Phase 2: WebSocket을 통해 전송되는 전체 문서 생성 진행 상황 메시지"""
    session_id: str = Field(..., description="세션 식별자")
    status: FullGenerationStatus = Field(..., description="현재 상태")
    message: str = Field(..., description="상태 설명 메시지")
    progress: float = Field(..., ge=0, le=100, description="진행률 (0-100)")
    current_step: str = Field(..., description="현재 진행 중인 단계")
    steps_completed: int = Field(0, description="완료된 단계 수")
    total_steps: int = Field(0, description="전체 단계 수")
    details: Optional[Dict[str, Any]] = Field(None, description="추가 세부 정보")
    result: Optional["FullGenerationResultData"] = Field(None, description="완료 시 결과 데이터")


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


class FullGenerationResponse(BaseModel):
    """Phase 2: 전체 문서 생성 요청에 대한 즉시 응답"""
    session_id: str = Field(..., description="세션 식별자")
    status: str = Field("accepted", description="요청 수락 상태")
    message: str = Field("전체 문서 생성 작업이 시작되었습니다.", description="응답 메시지")
    websocket_url: Optional[str] = Field(None, description="진행 상황을 확인할 WebSocket URL (선택사항)")


class FullGenerationResultData(BaseModel):
    """Phase 2: 완료 시 전달되는 전체 결과 데이터"""
    session_id: str = Field(..., description="세션 식별자")
    
    # 생성된 문서들
    word_filename: Optional[str] = Field(None, description="생성된 Word 문서 파일명")
    excel_list_filename: Optional[str] = Field(None, description="생성된 Excel 목록 파일명")
    base_scenario_filename: Optional[str] = Field(None, description="생성된 기본 시나리오 파일명")
    merged_excel_filename: Optional[str] = Field(None, description="병합된 Excel 파일명")
    
    # 다운로드 URL들
    download_urls: Dict[str, str] = Field(default_factory=dict, description="파일 다운로드 URL들")
    
    # 통계 정보
    generation_time: float = Field(0.0, description="전체 생성 시간 (초)")
    steps_completed: int = Field(0, description="완료된 단계 수")
    total_steps: int = Field(0, description="전체 단계 수")
    
    # 오류 정보 (있는 경우)
    errors: list = Field(default_factory=list, description="발생한 오류 목록")
    warnings: list = Field(default_factory=list, description="경고 메시지 목록")


# 세션 관리 관련 모델들
class SessionStatus(str, Enum):
    """세션 상태 열거형"""
    PREPARED = "prepared"       # 준비됨
    IN_PROGRESS = "in_progress" # 진행 중
    COMPLETED = "completed"     # 완료됨
    FAILED = "failed"          # 실패함
    EXPIRED = "expired"        # 만료됨


class PrepareSessionRequest(BaseModel):
    """세션 준비 요청"""
    session_id: Optional[str] = Field(None, description="기존 세션 ID (없으면 자동 생성)")
    metadata_json: Dict[str, Any] = Field(..., description="HTML 파싱된 메타데이터")
    html_file_path: Optional[str] = Field(None, description="원본 HTML 파일 경로")
    vcs_analysis_text: Optional[str] = Field(None, description="VCS 분석 텍스트 (선택적)")
    

class PrepareSessionResponse(BaseModel):
    """세션 준비 응답"""
    session_id: str = Field(..., description="생성/사용된 세션 ID")
    status: str = Field(..., description="준비 상태")
    retry_attempt: Optional[int] = Field(None, description="재시도 횟수")
    max_retries: Optional[int] = Field(None, description="최대 재시도 횟수")
    message: Optional[str] = Field(None, description="상태 메시지")


class SessionStatusResponse(BaseModel):
    """세션 상태 응답"""
    session_id: str
    status: SessionStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    retry_count: int = 0
    usage_count: int = 0
    last_error: Optional[Dict[str, Any]] = None
    previous_errors: list = []