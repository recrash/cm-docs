# src/excel_writer.py
import shutil
import openpyxl
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# 상수 정의
# 현재 스크립트 파일 위치를 기준으로 상대경로 설정
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_TEMPLATE_PATH = PROJECT_ROOT / "templates" / "template.xlsx"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
FILE_NAME_FORMAT = "{timestamp}_테스트_시나리오_결과.xlsx"
TIME_FORMAT = "%Y%m%d_%H%M%S"
NEWLINE_ESCAPE = "\\n"
NEWLINE_CHAR = "\n"
START_ROW = 11
DATA_JSON_INDENT = 2

# 엑셀 셉 위치
DESCRIPTION_CELL = 'B5'
TITLE_CELL = 'F4'

# 기본값
DEFAULT_DESCRIPTION = "개요 생성 실패"
DEFAULT_TITLE = "제목 생성 실패"


def _generate_filename() -> str:
    """
    현재 시간을 기반으로 파일명을 생성합니다.
    
    Returns:
        생성된 파일명
    """
    timestamp = datetime.now().strftime(TIME_FORMAT)
    return str(OUTPUT_DIR / FILE_NAME_FORMAT.format(timestamp=timestamp))


def _copy_template(template_path: str, destination: str) -> bool:
    """
    템플릿 파일을 대상 위치로 복사합니다.
    
    Args:
        template_path: 원본 템플릿 파일 경로
        destination: 복사할 대상 경로
    
    Returns:
        복사 성공 여부
    """
    try:
        # 템플릿 파일 존재 여부 확인
        template_file = Path(template_path)
        if not template_file.exists():
            print(f"오류: 원본 템플릿 파일('{template_path}')을 찾을 수 없습니다.")
            print(f"현재 확인한 경로: {template_file.absolute()}")
            return False
            
        shutil.copy(template_path, destination)
        return True
    except Exception as e:
        print(f"오류: 템플릿 파일 복사 중 오류가 발생했습니다: {e}")
        return False


def _fill_header_info(sheet, result_json: Dict[str, Any]) -> None:
    """
    엑셀 시트의 헤더 정보를 채웁니다.
    
    Args:
        sheet: openpyxl 워크시트 객체
        result_json: LLM 결과 JSON 데이터
    """
    sheet[DESCRIPTION_CELL] = result_json.get("Scenario Description", DEFAULT_DESCRIPTION)
    sheet[TITLE_CELL] = result_json.get("Test Scenario Name", DEFAULT_TITLE)


def _convert_newlines(text: str) -> str:
    """
    이스케이프된 개행 문자를 실제 개행으로 변환합니다.
    
    Args:
        text: 변환할 텍스트
    
    Returns:
        변환된 텍스트
    """
    return text.replace(NEWLINE_ESCAPE, NEWLINE_CHAR)


def _format_test_data(test_data: Any) -> str:
    """
    테스트 데이터를 엑셀에 저장할 형식으로 변환합니다.
    
    Args:
        test_data: 변환할 테스트 데이터
    
    Returns:
        형식화된 텍스트
    """
    if isinstance(test_data, (dict, list)):
        return json.dumps(test_data, indent=DATA_JSON_INDENT, ensure_ascii=False)
    else:
        return _convert_newlines(str(test_data))



def _fill_test_cases(sheet, test_cases: List[Dict[str, Any]]) -> None:
    """
    엑셀 시트에 테스트 케이스 데이터를 채웁니다.
    
    Args:
        sheet: openpyxl 워크시트 객체
        test_cases: 테스트 케이스 리스트
    """
    for i, scenario in enumerate(test_cases):
        current_row = START_ROW + i
        
        # ID 설정
        test_id = scenario.get("ID", f"CMP_MES_{i+1:03d}")
        sheet[f'A{current_row}'] = test_id
        
        # 절차
        procedure = _convert_newlines(scenario.get("절차", ""))
        sheet[f'B{current_row}'] = procedure
        
        # 사전조건
        precondition = _convert_newlines(scenario.get("사전조건", ""))
        sheet[f'C{current_row}'] = precondition
        
        # 데이터
        test_data = _format_test_data(scenario.get("데이터", ""))
        sheet[f'D{current_row}'] = test_data
        
        # 예상결과
        expected_result = _convert_newlines(scenario.get("예상결과", ""))
        sheet[f'E{current_row}'] = expected_result
        
        # Unit/Integration 테스트 플래그 (JSON에서 직접 읽기)
        unit_flag = scenario.get("Unit", "")
        integration_flag = scenario.get("Integration", "")
        sheet[f'F{current_row}'] = unit_flag
        sheet[f'G{current_row}'] = integration_flag


def save_results_to_excel(result_json: Dict[str, Any], template_path: str = None) -> Optional[str]:
    """
    LLM이 생성한 JSON 객체를 파싱하여 엑셀에 저장합니다.
    
    Args:
        result_json: LLM이 생성한 결과 JSON
        template_path: 엑셀 템플릿 파일 경로
    
    Returns:
        생성된 엑셀 파일 경로 또는 None (실패 시)
    """
    print("\n" + "="*50)
    print("최종 단계: 생성된 시나리오를 엑셀 파일에 저장합니다.")
    print("="*50)
    
    # 템플릿 경로가 지정되지 않은 경우 기본값 사용
    if template_path is None:
        template_path = str(DEFAULT_TEMPLATE_PATH)
    
    # outputs 디렉토리가 없으면 생성
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    final_filename = _generate_filename()
    
    # 템플릿 복사
    if not _copy_template(template_path, final_filename):
        return None
    
    # 엑셀 파일 열기 및 수정
    workbook = openpyxl.load_workbook(final_filename)
    sheet = workbook.active
    
    # 헤더 정보 채우기
    _fill_header_info(sheet, result_json)
    
    # 테스트 케이스 채우기
    test_cases = result_json.get("Test Cases", [])
    _fill_test_cases(sheet, test_cases)
    
    # 파일 저장
    workbook.save(final_filename)
    print(f"\n✅ 성공! '{final_filename}' 파일에 {len(test_cases)}개의 테스트 시나리오를 저장했습니다.")
    
    return final_filename