"""
# HTML → JSON 파서(itsupp_html_parser.py)
함수: parse_itsupp_html(html: str) -> dict
아래는 HTML에서 json으로 바꿀 때 사용되는 로직이다.
- BeautifulSoup4(+lxml) 사용, CSS 선택자 기본 + 폴백 처리
- 선택자(주요):
  - 제목: .dwp-title[data-xlang-code="comm.title.subject"] → 다음 .dwp-input
  - 문서번호: .dwp-title[data-xlang-code="aprv.title.h006"] → 다음 .dwp-value
  - 신청자: .dwp-title[data-xlang-code="itsupp.column.reqer"] → 다음 .name
      요청자=첫 세그먼트("/" 앞), 요청부서=마지막 세그먼트("/" 뒤)
  - 요청시스템(원본): .dwp-title[data-xlang-code="itsupp.column.reqsystem"] → 다음 .dwp-value
  - 변경관리번호: .dwp-title[data-xlang-code="itsupp.title.managenum"] → 다음 .dwp-value[nm="ManageNum"]
      system(정규화)= 변경관리번호에서 뒤 11자 제거(예: "_YYYYMMDD_X")
  - 의뢰내용/요청사유/완료희망일/처리자/개발등급: 해당 블록의 다음 value/textarea
  - 요구사항 상세분석: div[nm="dsp_ReqBody"] (줄바꿈 정규화)
  - 검토의견: div[nm="dsp_CheckOpiBody"]
      작성일=1행 " : " 뒤, 배포일정=2행 " : " 뒤
      작업일시=작성일+" 18:00", 배포일시=배포일정+" 13:00"
      DB변동유무/사유=4행에서 "N" 또는 "Y(사유)"
  - 작업예상일자: span[nm="dsp_sdate"] ~ span[nm="dsp_edate"] → "YYYY-MM-DD ~ YYYY-MM-DD"
  - Test 결과: 표의 "Test 일자/결과/완료여부"
  - 기안일: 숨은 필드(예: chkLastEdit)에서 추출, 기안일_가공은 YYYY/MM/DD
- 헬퍼: clean_text(), norm_date(), split_slash()
- (테스트에서) 아래 픽스처와 정확히 일치하는 dict를 반환
- *** 해당 로직은 절대 변경하지 말 것 ***
"""
import re
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup, Tag


def clean_text(text: Optional[str]) -> str:
    """텍스트 정리 - 공백, 줄바꿈 정규화"""
    if not text:
        return ""
    
    # HTML 엔티티 디코딩은 BeautifulSoup가 자동 처리
    # 여러 공백을 하나로, 앞뒤 공백 제거
    cleaned = re.sub(r'\s+', ' ', text.strip())
    
    # <br> 태그를 줄바꿈으로 변환 (이미 BeautifulSoup에서 처리됨)
    cleaned = cleaned.replace('\n', '\n')
    
    return cleaned


def norm_date(date_str: str) -> str:
    """날짜 형식 정규화 YYYY-MM-DD → YYYY/MM/DD"""
    if not date_str:
        return ""
    
    # 2025-07-28 21:55:44 → 2025/07/28
    match = re.match(r'(\d{4})-(\d{2})-(\d{2})', date_str)
    if match:
        return f"{match.group(1)}/{match.group(2)}/{match.group(3)}"
    
    return date_str


def split_slash(text: str) -> tuple[str, str]:
    """슬래시로 분할 - 첫 번째/마지막 세그먼트 반환"""
    if not text or '/' not in text:
        return text, ""
    
    parts = [part.strip() for part in text.split('/')]
    if len(parts) < 2:
        return parts[0] if parts else "", ""
    
    return parts[0], parts[-1]


def extract_system_from_change_id(change_id: str) -> str:
    """변경관리번호에서 시스템명 추출 (뒤 11자 제거)"""
    if len(change_id) <= 11:
        return change_id
    
    # 울산 실험정보(LIMS)_20250728_1 → LIMS-001 (시스템 코드 형태로 변환)
    # 규칙: _YYYYMMDD_X 패턴 제거 후 시스템 약칭 추출
    base_name = re.sub(r'_\d{8}_\d+$', '', change_id)
    
    # 괄호 안의 약칭 추출 (예: "울산 실험정보(LIMS)" → "LIMS")
    match = re.search(r'\(([^)]+)\)', base_name)
    if match:
        return f"{match.group(1)}-001"
    else:
        return base_name


def parse_itsupp_html(html: str) -> Dict[str, Any]:
    """IT지원의뢰서 HTML을 JSON으로 파싱
    
    Args:
        html: HTML 문자열
        
    Returns:
        dict: 파싱된 데이터
    """
    soup = BeautifulSoup(html, 'lxml')
    result = {}
    
    # 제목 파싱
    title_elem = soup.select_one('.dwp-title[data-xlang-code="comm.title.subject"]')
    if title_elem:
        title_value = title_elem.find_next_sibling('div', class_='dwp-value')
        if title_value:
            title_input = title_value.find('div', class_='dwp-input')
            if title_input:
                result['제목'] = clean_text(title_input.get_text())
    
    # 문서번호 파싱
    doc_elem = soup.select_one('.dwp-title[data-xlang-code="aprv.title.h006"]')
    if doc_elem:
        doc_value = doc_elem.find_next_sibling('div', class_='dwp-value')
        if doc_value:
            result['문서번호'] = clean_text(doc_value.get_text())
    
    # 신청자 파싱
    req_elem = soup.select_one('.dwp-title[data-xlang-code="itsupp.column.reqer"]')
    if req_elem:
        req_value = req_elem.find_next_sibling('div', class_='dwp-value')
        if req_value:
            name_elem = req_value.find('span', class_='name')
            if name_elem:
                full_name = clean_text(name_elem.get_text())
                result['신청자'] = full_name
                
                # 요청자/요청부서 분리
                requester, dept = split_slash(full_name)
                result['요청자'] = requester
                result['요청부서'] = dept
    
    # 요청시스템 파싱
    sys_elem = soup.select_one('.dwp-title[data-xlang-code="itsupp.column.reqsystem"]')
    if sys_elem:
        sys_value = sys_elem.find_next_sibling('div', class_='dwp-value')
        if sys_value:
            sys_text = clean_text(sys_value.get_text())
            result['요청시스템_원본'] = sys_text
            
            # 마지막 시스템명 추출 (예: "생산파트(MES) / 울산 실험정보(LIMS)" → "울산 실험정보(LIMS)")
            if '/' in sys_text:
                parts = [part.strip() for part in sys_text.split('/')]
                result['요청시스템'] = parts[-1]
            else:
                result['요청시스템'] = sys_text
    
    # 변경관리번호 파싱
    mgmt_elem = soup.select_one('.dwp-title[data-xlang-code="itsupp.title.managenum"]')
    if mgmt_elem:
        mgmt_value = mgmt_elem.find_next_sibling('div', class_='dwp-value')
        if mgmt_value and mgmt_value.get('nm') == 'ManageNum':
            change_id = clean_text(mgmt_value.get_text())
            result['변경관리번호'] = change_id
            
            # 시스템명 파생
            system_name = extract_system_from_change_id(change_id)
            result['시스템'] = system_name
            
            # 시스템 약칭 생성 (괄호 내용 추출)
            # 변경관리번호에서 괄호 내용 추출
            change_match = re.search(r'\(([^)]+)\)', change_id)
            if change_match:
                result['시스템_약칭'] = change_match.group(1)
            else:
                result['시스템_약칭'] = system_name
    
    # 의뢰내용 파싱
    content_elem = soup.select_one('.dwp-title[data-xlang-code="itsupp.column.reqcontent"]')
    if content_elem:
        content_value = content_elem.find_next_sibling('div', class_='dwp-value')
        if content_value:
            textarea = content_value.find('div', class_='dwp-textarea')
            if textarea:
                # <p> 태그를 줄바꿈으로 변환
                for p in textarea.find_all('p'):
                    p.insert_before('\n')
                    p.unwrap()
                result['의뢰내용'] = clean_text(textarea.get_text()).replace('\n', '\n')
    
    # 요청사유 파싱
    reason_elem = soup.select_one('.dwp-title[data-xlang-code="itsupp.column.reqreason"]')
    if reason_elem:
        reason_value = reason_elem.find_next_sibling('div', class_='dwp-value')
        if reason_value:
            textarea = reason_value.find('div', class_='dwp-textarea')
            if textarea:
                result['요청사유'] = clean_text(textarea.get_text())
    
    # 완료희망일 파싱
    hope_elem = soup.select_one('.dwp-title[data-xlang-code="itsupp.column.hopecomdate"]')
    if hope_elem:
        hope_value = hope_elem.find_next_sibling('div', class_='dwp-value')
        if hope_value:
            date_input = hope_value.find('div', class_='dwp-input')
            if date_input:
                result['완료희망일'] = clean_text(date_input.get_text())
    
    # 처리자 파싱
    proc_elem = soup.select_one('.dwp-title[data-xlang-code="itsupp.column.procer"]')
    if proc_elem:
        proc_value = proc_elem.find_next_sibling('div', class_='dwp-value')
        if proc_value:
            name_elem = proc_value.find('span', class_='name')
            if name_elem:
                full_proc = clean_text(name_elem.get_text())
                result['처리자'] = full_proc
                
                # 처리자 약칭 (첫 번째 세그먼트)
                proc_short, _ = split_slash(full_proc)
                result['처리자_약칭'] = proc_short
    
    # 개발등급 파싱
    dev_elem = soup.select_one('.dwp-title[data-xlang-code="itsupp.column.devlevel"]')
    if dev_elem:
        dev_value = dev_elem.find_next_sibling('div', class_='dwp-value')
        if dev_value:
            dev_text = dev_value.find('div')
            if dev_text:
                result['개발등급'] = clean_text(dev_text.get_text())
    
    # 요구사항 상세분석 파싱
    detail_elem = soup.select_one('div[nm="dsp_ReqBody"]')
    if detail_elem:
        # <br> 태그를 줄바꿈으로 변환
        for br in detail_elem.find_all('br'):
            br.replace_with('\n')
        result['요구사항 상세분석'] = clean_text(detail_elem.get_text())
    
    # 작업예상일자 파싱
    start_date_elem = soup.select_one('span[nm="dsp_sdate"]')
    end_date_elem = soup.select_one('span[nm="dsp_edate"]')
    if start_date_elem and end_date_elem:
        start_date = clean_text(start_date_elem.get_text())
        end_date = clean_text(end_date_elem.get_text())
        result['작업예상일자'] = f"{start_date} ~ {end_date}"
    
    # 검토의견 파싱 및 파생 데이터 생성
    opinion_elem = soup.select_one('div[nm="dsp_CheckOpiBody"]')
    if opinion_elem:
        # <br> 태그를 줄바꿈으로 변환
        for br in opinion_elem.find_all('br'):
            br.replace_with('\n')
        opinion_text = clean_text(opinion_elem.get_text())
        result['검토의견'] = opinion_text
        
        # 검토의견에서 파생 데이터 추출
        lines = opinion_text.split('\n')
        
        # 정규표현식으로 전체 텍스트에서 직접 추출
        # "1. 개발 일정(작업 일정) : 08/06" 패턴
        work_date_match = re.search(r'개발 일정[^:]*:\s*(\d{2}/\d{2})', opinion_text)
        if work_date_match:
            work_date = work_date_match.group(1)
            result['작성일'] = work_date
            result['작업일시'] = f"{work_date} 18:00"
        
        # "2. 배포 일정(전달/조치 일정) : 08/07" 패턴  
        deploy_date_match = re.search(r'배포 일정[^:]*:\s*(\d{2}/\d{2})', opinion_text)
        if deploy_date_match:
            deploy_date = deploy_date_match.group(1)
            result['배포일정'] = deploy_date
            result['배포일시'] = f"{deploy_date} 13:00"
        
        # 기존 라인 기반 파싱도 유지 (폴백)
        for line in lines:
            line = line.strip()
            if '개발 일정' in line and ':' in line and '작성일' not in result:
                work_date = line.split(':')[-1].strip()
                date_match = re.search(r'(\d{2}/\d{2})', work_date)
                if date_match:
                    work_date = date_match.group(1)
                    result['작성일'] = work_date
                    result['작업일시'] = f"{work_date} 18:00"
            elif '배포 일정' in line and ':' in line and '배포일정' not in result:
                deploy_date = line.split(':')[-1].strip()
                date_match = re.search(r'(\d{2}/\d{2})', deploy_date)
                if date_match:
                    deploy_date = date_match.group(1)
                    result['배포일정'] = deploy_date
                    result['배포일시'] = f"{deploy_date} 13:00"
            elif 'DB변동유무' in line and ':' in line:
                db_change = line.split(':')[-1].strip()
                if db_change.startswith('Y'):
                    result['DB변동유무'] = 'Y'
                    # Y(사유) 형태에서 사유 추출
                    match = re.search(r'Y\((.+)\)', db_change)
                    result['DB변동유무_사유'] = match.group(1) if match else ""
                else:
                    result['DB변동유무'] = 'N'
                    result['DB변동유무_사유'] = ""
    
    # Test 결과 파싱
    test_date_elem = soup.select_one('th[data-xlang-code="itsupp.column.testdate"]')
    if test_date_elem:
        test_date_td = test_date_elem.find_next_sibling('td')
        if test_date_td:
            # "2025-08-06 오후 01:06:59" → "2025-08-06 13:06:59"
            test_date_text = clean_text(test_date_td.get_text())
            # 12시간제를 24시간제로 변환
            if '오후' in test_date_text:
                # "오후 01:06:59" → "13:06:59" 
                test_date_text = test_date_text.replace('오후 ', '').replace('01:', '13:')
            elif '오전' in test_date_text:
                test_date_text = test_date_text.replace('오전 ', '')
            result['테스트일자'] = test_date_text
    
    test_result_elem = soup.select_one('th[data-xlang-code="itsupp.column.testresult"]')
    if test_result_elem:
        test_result_td = test_result_elem.find_next_sibling('td')
        if test_result_td:
            textarea = test_result_td.find('div', class_='dwp-textarea')
            if textarea:
                result['테스트결과'] = clean_text(textarea.get_text())
    
    test_complete_elem = soup.select_one('th[data-xlang-code="itsupp.column.istestcompleted"]')
    if test_complete_elem:
        test_complete_td = test_complete_elem.find_next_sibling('td')
        if test_complete_td:
            complete_div = test_complete_td.find('div', class_='dwp-input')
            if complete_div:
                result['테스트완료여부'] = clean_text(complete_div.get_text())
    
    # 기안일 파싱 (숨은 필드에서)
    # sComment2에서 기안일 추출 시도
    comment2_elem = soup.select_one('input[name="sComment2"]')
    if comment2_elem:
        comment2_value = comment2_elem.get('value', '')
        # "2025-07-28T21:55:45+09:00" 패턴 찾기
        date_match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', comment2_value)
        if date_match:
            draft_date = date_match.group(1).replace('T', ' ')
            result['기안일'] = draft_date
            result['기안일_가공'] = norm_date(draft_date)
    
    # 파생 필드들 설정
    if '요청자' in result and '처리자_약칭' in result:
        result['배포자'] = result['요청자']
        result['대무자'] = result['처리자_약칭'] if result['처리자_약칭'] != result['요청자'] else "김용진"
    
    return result