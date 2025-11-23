"""
Excel 변경관리 문서 목록 생성 서비스

openpyxl을 사용하여 템플릿 기반 Excel 목록 생성
테이블 append 방식으로 데이터 추가
"""
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Union, Dict, Any

# Windows 인코딩 문제 해결
if sys.platform.startswith('win'):
    os.environ['PYTHONIOENCODING'] = 'utf-8'

from openpyxl import load_workbook
from openpyxl.styles import Font

from ..models import ChangeRequest
from .paths import verify_template_exists, get_documents_dir
from .filename import generate_excel_list_filename, unique_path
from ..logging_config import get_logger

logger = get_logger(__name__)


def _format_deploy_date(deploy_datetime: Optional[str]) -> str:
    """배포일자 포맷팅
    
    deploy_datetime가 있으면 날짜만 추출, 없으면 내일 날짜를 "M월 d일" 형식으로 반환
    """
    if deploy_datetime:
        # "08/07 13:00" 형식에서 날짜 부분만 추출
        if ' ' in deploy_datetime:
            date_part = deploy_datetime.split(' ')[0]
            # "08/07" → "8월 7일"
            try:
                month, day = date_part.split('/')
                return f"{int(month)}월 {int(day)}일"
            except:
                return deploy_datetime
        else:
            return deploy_datetime
    else:
        # 내일 날짜를 "M월 d일" 형식으로
        tomorrow = datetime.now() + timedelta(days=1)
        return f"{tomorrow.month}월 {tomorrow.day}일"


def _extract_filename_only(file_path: Optional[str]) -> str:
    """파일 경로에서 파일명만 추출"""
    if not file_path:
        return ""
    
    # 경로에서 파일명만 추출
    if '/' in file_path or '\\' in file_path:
        return Path(file_path).name
    
    return file_path


def build_change_list_xlsx(
    items: List[Union[ChangeRequest, Dict[str, Any]]], 
    out_dir: Optional[Path] = None
) -> Path:
    """변경관리 문서 목록 Excel 파일 생성
    
    Args:
        items: 변경관리 요청 데이터 목록
        out_dir: 출력 디렉터리 (None이면 기본 documents 디렉터리 사용)
        
    Returns:
        Path: 생성된 파일 경로
        
    Raises:
        FileNotFoundError: 템플릿 파일이 없는 경우
        ValueError: 데이터가 없는 경우
    """
    if not items:
        raise ValueError("items는 비어있을 수 없습니다")
    
    # 템플릿 로드
    template_path = verify_template_exists("template_list.xlsx")
    wb = load_workbook(str(template_path))
    
    # 출력 디렉터리 설정
    if out_dir is None:
        out_dir = get_documents_dir()
    
    # 첫 번째 워크시트 사용
    ws = wb.active
    
    # 기존 데이터가 있는 마지막 행 찾기
    max_row = ws.max_row

    # 8행부터 시작
    start_row = 8
    
    for row in range(8, max_row + 2):
        # 해당 행의 모든 셀 값이 None인지 확인 (A~K열)
        is_empty = True
        for col in range(1, 12):
            if ws.cell(row=row, column=col).value is not None:
                is_empty = False
                break
        
        if is_empty:
            start_row = row
            break
        else:
            start_row = row + 1
            
    logger.info(f"[DEBUG] Writing starts at row: {start_row}")
            
    # 오늘 날짜 생성 (yyyy.m.dd 형식)
    from datetime import datetime
    today_str = datetime.now().strftime("%Y.%-m.%-d")
            
    # 각 항목을 행으로 추가
    for i, item in enumerate(items):
        # ChangeRequest 객체를 dict로 변환
        if isinstance(item, ChangeRequest):
            logger.info(f"[DEBUG] Item {i} is ChangeRequest: {item}")
            data = item.dict()
        else:
            logger.info(f"[DEBUG] Item {i} is Dict: {item}")
            data = item
        
        row_num = start_row + i
        logger.info(f"[DEBUG] Writing item {i} to row {row_num}: {data}")
        
        # 2025-11-22 요청된 새로운 컬럼 매핑 (A~R)
        columns = [
            data.get('change_id', ''),                             # A: change_id
            today_str,                                             # B: 오늘(yyyy.m.dd)
            data.get('writer_short', ''),                          # C: writer_short
            _format_deploy_date(data.get('deploy_datetime')),       # D: deploy_datetime
            data.get('deployer', ''),                              # E: deployer
            data.get('system', ''),                                # F: system
            _format_deploy_date(data.get('created_date')),          # G: created_date
            data.get('requester', ''),                             # H: requester
            data.get('title', ''),                                 # I: title
            data.get('requirement_detail', ''),                    # J: requirement_detail
            '',                                                    # K: 공란
            'Y',                                                   # L: Y
            'Y',                                                   # M: Y
            '',                                                    # N: 공란
            '',                                                    # O: 공란
            '',                                                    # P: 공란
            data.get('deployer', ''),                              # Q: deployer (G열 중복 -> Q열로 추정)
            data.get('replace_manager', '')                        # R: replace_manager
        ]
        
        # 데이터 쓰기
        for col_idx, value in enumerate(columns, 1):
            cell = ws.cell(row=row_num, column=col_idx)
            cell.value = value
            
            # 스타일 적용 (기본 스타일)
            # cell.alignment = Alignment(horizontal='center', vertical='center')
            # cell.border = Border(left=Side(style='thin'), right=Side(style='thin'), 
            #                     top=Side(style='thin'), bottom=Side(style='thin'))
        
        # 폰트 설정 (선택 사항)
        # for col_idx in range(1, len(columns) + 1):
        #     cell = ws.cell(row=row_num, column=col_idx)
        #     cell.font = Font(name='맑은 고딕')
    
    # 파일명 생성
    filename = generate_excel_list_filename()
    
    # 중복 방지 경로 생성
    output_path = unique_path(out_dir, filename)
    
    # 파일 저장 (Windows 인코딩 안전 모드)
    try:
        # UTF-8 인코딩으로 저장
        wb.save(str(output_path))
    except (UnicodeEncodeError, UnicodeDecodeError) as e:
        # 인코딩 에러 발생 시 안전한 경로로 재시도
        safe_filename = output_path.name.encode('ascii', errors='replace').decode('ascii')
        safe_path = output_path.parent / safe_filename
        wb.save(str(safe_path))
        output_path = safe_path
        print(f"Warning: 파일명 인코딩 문제로 안전한 이름으로 저장: {safe_filename}")
    finally:
        wb.close()
    
    return output_path