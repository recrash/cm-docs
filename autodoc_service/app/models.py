"""
Pydantic models for autodoc_service

단일 진실 소스(Single Source of Truth) - 모든 데이터 구조 정의
"""
from typing import Optional, List, Union, Dict, Any
from pydantic import BaseModel, Field


class ChangeDetails(BaseModel):
    """변경 세부사항"""
    summary: Optional[str] = None
    risk: Optional[str] = None
    plan: Optional[str] = None


class ChangeRequest(BaseModel):
    """변경관리 요청 데이터 모델"""
    
    # 필수 필드
    change_id: str = Field(..., description="변경관리번호")
    system: str = Field(..., description="시스템명(요청시스템 정규화)")
    title: str = Field(..., description="제목")
    
    # 선택 필드 - 기본 정보
    system_short: Optional[str] = Field(None, description="시스템_약칭")
    requester: Optional[str] = Field(None, description="요청자")
    request_dept: Optional[str] = Field(None, description="요청부서")
    customer: Optional[str] = Field(None, description="고객사")
    writer_short: Optional[str] = Field(None, description="처리자_약칭")
    doc_no: Optional[str] = Field(None, description="문서번호")
    
    # 일시 관련
    work_datetime: Optional[str] = Field(None, description="작업일시 (예: '08/06 18:00')")
    deploy_datetime: Optional[str] = Field(None, description="배포일시 (예: '08/07 13:00')")
    biz_test_date: Optional[str] = Field(None, description="현업_테스트_일자 YYYY-MM-DD")
    created_date: Optional[str] = Field(None, description="작성일(없으면 오늘 mm/dd)")
    
    # 세부 정보
    details: ChangeDetails = Field(default_factory=ChangeDetails)
    impact_targets: Optional[str] = Field(None, description="영향도_대상자")
    worker_deployer: Optional[str] = Field(None, description="작업자-배포자")
    
    # 목록/부가 항목
    deploy_type: Optional[str] = Field("정기배포", description="배포종류")
    program: Optional[str] = Field("Appl.", description="Program")
    it_request_html: Optional[str] = Field(None, description="IT 지원의뢰서")
    deployer: Optional[str] = Field(None, description="배포자")
    has_cm_doc: Optional[str] = Field("O", description="변경관리문서유무")
    author: Optional[str] = Field(None, description="작성자")


class ParseHtmlResponse(BaseModel):
    """HTML 파싱 응답 모델"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class CreateDocumentResponse(BaseModel):
    """문서 생성 응답 모델"""
    ok: bool
    filename: Optional[str] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """헬스체크 응답 모델"""
    status: str
    templates_available: bool
    documents_dir_writable: bool


class EnhancedScenarioRequest(BaseModel):
    """통합 테스트 시나리오 생성 요청 모델"""
    change_request: ChangeRequest = Field(..., description="기본 변경관리 데이터")
    test_cases: Optional[List[Dict[str, Any]]] = Field(None, description="LLM이 생성한 추가 테스트 케이스")