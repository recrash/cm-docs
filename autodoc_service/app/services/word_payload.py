"""
Word Document Payload Mapping Layer

This module creates a centralized mapping layer that transforms parsed HTML data
into a consistent format expected by Word document templates, handling missing
fields and providing fallback values as per VBA macro requirements.
"""
from datetime import datetime
from typing import Dict, Any


def build_word_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform parsed data into Word-compatible payload with all required fields.
    
    Args:
        data: Parsed HTML data dictionary
        
    Returns:
        Dict with all fields required by Word template mapping
        
    Key transformations:
    - 고객사: Falls back to 요청부서 or last segment of 신청자
    - 작업자-배포자: Combines 처리자_약칭 and 배포자
    - 목적-개선내용: Falls back to 요구사항 상세분석
    - 영향도_대상자: Default policy value
    - 작성일_mmdd: Proper mm/dd format from parser value or today
    """
    
    # 1) 고객사: 없으면 요청부서로 대체(또는 신청자 마지막 세그먼트)
    customer = data.get("고객사")
    if not customer:
        customer = data.get("요청부서")
        if not customer:
            # 신청자에서 마지막 세그먼트 추출 (예: "이대경/Manager/IT운영팀/SK picglobal" → "SK picglobal")
            applicant = data.get("신청자", "")
            if "/" in applicant:
                customer = applicant.split("/")[-1].strip()
            else:
                customer = applicant
    
    # 2) 작업자-배포자: 포맷 합의 ("처리자_약칭 / 배포자")
    worker_deployer = data.get("작업자-배포자")
    if not worker_deployer:
        worker = data.get("처리자_약칭", "")
        deployer = data.get("배포자", "")
        
        # 둘 다 있으면 "worker / deployer" 형식
        if worker and deployer:
            worker_deployer = f"{worker} / {deployer}"
        elif worker:
            # 작업자만 있으면 작업자만
            worker_deployer = worker
        elif deployer:
            # 배포자만 있으면 배포자만
            worker_deployer = deployer
        else:
            # 둘 다 없으면 요청자로 폴백
            worker_deployer = data.get("요청자", "")
    
    # 3) 목적-개선내용: 구조화된 형식으로 생성
    # "1. 목적\n{요청사유}\n\n2. 주요내용\n{요구사항 상세분석}"
    purpose_reason = data.get("요청사유", "")
    detailed_analysis = data.get("요구사항 상세분석", "")
    
    if purpose_reason or detailed_analysis:
        purpose_content_parts = []
        
        if purpose_reason:
            purpose_content_parts.append("1. 목적")
            purpose_content_parts.append(purpose_reason)
            purpose_content_parts.append("")  # 빈 줄
            
        if detailed_analysis:
            purpose_content_parts.append("2. 주요내용")
            purpose_content_parts.append(detailed_analysis)
            
        purpose_content = "\n".join(purpose_content_parts)
    else:
        # 폴백: 기존 목적-개선내용 필드 사용
        purpose_content = data.get("목적-개선내용", "")
    
    # 4) 영향도_대상자: 도출 규칙이 없다면 정책값
    impact_targets = data.get("영향도_대상자")
    if not impact_targets:
        impact_targets = "- UI 수정"
    
    # 5) 작성일: 기안일 정보를 사용하여 mm/dd 형식으로 생성
    raw_written = data.get("작성일", "")
    draft_date_processed = data.get("기안일_가공", "")  # "2025/07/28" 형식
    
    if raw_written and len(raw_written) == 5 and "/" in raw_written:
        # 이미 "08/06" 형태면 그대로 사용
        written_mmdd = raw_written
    elif draft_date_processed:
        # "2025/07/28" → "07/28" 변환
        try:
            parts = draft_date_processed.split("/")
            if len(parts) == 3:
                written_mmdd = f"{parts[1]}/{parts[2]}"
            else:
                written_mmdd = datetime.now().strftime("%m/%d")
        except:
            written_mmdd = datetime.now().strftime("%m/%d")
    else:
        written_mmdd = datetime.now().strftime("%m/%d")
    
    # 6) details 객체 구성 (summary와 plan 필드를 포함)
    details = {
        "summary": purpose_content,
        "plan": data.get("plan", "")
    }
    
    # 기존 데이터에 파생/보정 필드 추가
    enhanced_data = {
        # 기존 키들 전달
        **data,
        
        # Word 템플릿 매크로가 기대하는 파생/보정 키들
        "고객사": customer,
        "작업자-배포자": worker_deployer, 
        "목적-개선내용": purpose_content,
        "영향도_대상자": impact_targets,
        "작성일_mmdd": written_mmdd,
        
        # ChangeRequest 모델에서 기대하는 필드들
        "customer": customer,
        "worker_deployer": worker_deployer,
        "impact_targets": impact_targets,
        "created_date": written_mmdd,
        "doc_no": data.get("문서번호", ""),
        "work_datetime": data.get("작업일시", ""),
        "deploy_datetime": data.get("배포일시", ""),
        "request_dept": data.get("요청부서", ""),
        "requester": data.get("요청자", ""),
        "details": details
    }
    
    return enhanced_data


def validate_word_payload(payload: Dict[str, Any]) -> Dict[str, str]:
    """
    Validate Word payload and return any missing or problematic fields.
    
    Args:
        payload: Word payload dictionary
        
    Returns:
        Dict of field_name: issue_description for validation issues
    """
    issues = {}
    
    required_fields = [
        "제목", "변경관리번호", "시스템", "고객사", "작업자-배포자",
        "목적-개선내용", "영향도_대상자", "작성일_mmdd"
    ]
    
    for field in required_fields:
        if not payload.get(field):
            issues[field] = "Missing or empty value"
    
    return issues