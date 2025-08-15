"""
Word Document Payload Mapping Layer

This module creates a centralized mapping layer that transforms parsed HTML data
into a consistent format expected by Word document templates, handling missing
fields and providing fallback values as per VBA macro requirements.
"""
from datetime import datetime
from typing import Dict, Any


def get_system_deployer(system: str, system_abbr: str) -> str:
    """
    시스템별 배포자 매핑 함수
    
    Args:
        system: 요청시스템 (예: "울산 실험정보(LIMS)")
        system_abbr: 시스템 약칭 (예: "LIMS")
        
    Returns:
        str: 해당 시스템의 배포자 이름
        
    Note:
        이 함수는 향후 시스템별 배포자를 확장할 수 있도록 설계되었습니다.
        현재는 기본값을 반환하며, 필요에 따라 매핑 로직을 추가할 수 있습니다.
    """
    # 시스템별 배포자 매핑 테이블 (향후 확장 가능)
    system_deployer_mapping = {
        # 예시: 시스템 이름 또는 약칭으로 배포자 매핑
        # "LIMS": "김배포",
        # "MES": "이배포", 
        # "ERP": "박배포",
        # "울산 실험정보(LIMS)": "김배포",
    }
    
    # 1) 시스템 이름으로 직접 매핑 확인
    if system in system_deployer_mapping:
        return system_deployer_mapping[system]
    
    # 2) 시스템 약칭으로 매핑 확인
    if system_abbr in system_deployer_mapping:
        return system_deployer_mapping[system_abbr]
    
    # 3) 시스템 이름에 특정 키워드가 포함된 경우 매핑
    system_lower = system.lower() if system else ""
    if "lims" in system_lower:
        # return "LIMS전담배포자"  # 향후 활성화 가능
        pass
    elif "mes" in system_lower:
        # return "MES전담배포자"   # 향후 활성화 가능
        pass
    
    # 4) 기본값: 매핑되지 않은 시스템은 빈 문자열 반환 (기존 로직 유지)
    return ""


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
    
    # 1-1) 요청부서: 신청자에서 세 번째 세그먼트 추출 (부서 정보) - 강제 덮어쓰기
    # HTML 파서가 마지막 세그먼트를 요청부서로 설정하지만, 실제로는 세 번째가 부서임
    applicant = data.get("신청자", "")
    if "/" in applicant:
        segments = applicant.split("/")
        if len(segments) >= 3:
            request_dept = segments[2].strip()  # 세 번째 세그먼트가 실제 부서
        else:
            request_dept = data.get("요청부서", "")
    else:
        request_dept = data.get("요청부서", "")
    
    # 2) 작업자-배포자: 포맷 합의 ("처리자_약칭 / 배포자")
    worker_deployer = data.get("작업자-배포자")
    if not worker_deployer:
        worker = data.get("처리자_약칭", "")
        deployer = data.get("배포자", "")
        
        # 시스템별 배포자 매핑 (향후 확장 가능)
        if not deployer:
            deployer = get_system_deployer(data.get("요청시스템", ""), data.get("시스템_약칭", ""))
        
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
        "요청부서": request_dept,  # 신청자에서 추출된 부서 정보
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
        "request_dept": request_dept,  # 업데이트된 부서 정보
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