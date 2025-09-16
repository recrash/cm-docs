# src/excel_writer.py
import shutil
import openpyxl
import json
import locale
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# 환경 변수 기반 경로 관리 임포트
from .paths import get_templates_dir, get_outputs_dir

# Windows 인코딩 문제 해결을 위한 초기화
def _ensure_utf8_encoding():
    """Windows 환경에서 UTF-8 인코딩을 보장합니다."""
    try:
        # Python 3.7+ 에서 Windows UTF-8 모드 지원
        if sys.platform.startswith('win'):
            # 환경변수 설정
            import os
            os.environ['PYTHONIOENCODING'] = 'utf-8'
            os.environ['PYTHONLEGACYWINDOWSSTDIO'] = '0'
            
            # UTF-8 로케일 설정 시도
            try:
                locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
            except locale.Error:
                try:
                    locale.setlocale(locale.LC_ALL, 'C.UTF-8')
                except locale.Error:
                    try:
                        # Windows 특화 UTF-8 설정
                        locale.setlocale(locale.LC_ALL, '.UTF8')
                    except locale.Error:
                        # 모든 로케일 설정 실패 시에도 환경변수로 처리
                        pass
    except Exception:
        # 인코딩 설정 실패해도 진행
        pass

def _safe_str_convert(value):
    """Windows charmap 에러를 방지하는 안전한 문자열 변환"""
    if value is None:
        return ""
    
    try:
        # 이미 문자열인 경우
        if isinstance(value, str):
            return value
        
        # bytes인 경우 UTF-8로 디코딩
        if isinstance(value, bytes):
            return value.decode('utf-8', errors='replace')
        
        # 기타 타입은 문자열로 변환
        return str(value)
    except (UnicodeDecodeError, UnicodeEncodeError):
        # 변환 실패 시 안전한 ASCII 변환
        return str(value).encode('ascii', errors='replace').decode('ascii')

# 모듈 로드 시 UTF-8 인코딩 보장
_ensure_utf8_encoding()

# 상수 정의
# 환경 변수 기반 경로 사용
DEFAULT_TEMPLATE_PATH = get_templates_dir() / "template.xlsx"
OUTPUT_DIR = get_outputs_dir()
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
    description = _safe_str_convert(result_json.get("Scenario Description", DEFAULT_DESCRIPTION))
    title = _safe_str_convert(result_json.get("Test Scenario Name", DEFAULT_TITLE))
    
    sheet[DESCRIPTION_CELL] = description
    sheet[TITLE_CELL] = title


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
        # UTF-8 인코딩 명시 및 한글 문자 보존
        return json.dumps(test_data, indent=DATA_JSON_INDENT, ensure_ascii=False)
    else:
        # 한글 문자가 포함된 문자열 처리
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
        
        # ID 설정 (안전한 문자열 변환)
        test_id = _safe_str_convert(scenario.get("ID", f"CMP_MES_{i+1:03d}"))
        sheet[f'A{current_row}'] = test_id
        
        # 절차 (안전한 문자열 변환 + 개행 처리)
        procedure = _convert_newlines(_safe_str_convert(scenario.get("절차", "")))
        sheet[f'B{current_row}'] = procedure
        
        # 사전조건 (안전한 문자열 변환 + 개행 처리)
        precondition = _convert_newlines(_safe_str_convert(scenario.get("사전조건", "")))
        sheet[f'C{current_row}'] = precondition
        
        # 데이터 (JSON 형식 데이터도 안전하게 처리)
        test_data = _format_test_data(scenario.get("데이터", ""))
        sheet[f'D{current_row}'] = _safe_str_convert(test_data)
        
        # 예상결과 (안전한 문자열 변환 + 개행 처리)
        expected_result = _convert_newlines(_safe_str_convert(scenario.get("예상결과", "")))
        sheet[f'E{current_row}'] = expected_result
        
        # Unit/Integration 테스트 플래그 (안전한 문자열 변환)
        unit_flag = _safe_str_convert(scenario.get("Unit", ""))
        integration_flag = _safe_str_convert(scenario.get("Integration", ""))
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
    
    try:
        # Windows charmap 에러 방지를 위한 환경 변수 설정
        import os
        old_pythonioencoding = os.environ.get('PYTHONIOENCODING')
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        
        try:
            # UTF-8 인코딩을 명시하여 엑셀 파일 열기 및 수정
            workbook = openpyxl.load_workbook(final_filename)
        sheet = workbook.active
        
        # 헤더 정보 채우기
        _fill_header_info(sheet, result_json)
        
        # 테스트 케이스 채우기
        test_cases = result_json.get("Test Cases", [])
        _fill_test_cases(sheet, test_cases)
        
        # UTF-8 인코딩으로 파일 저장 (Windows 호환성)
            workbook.save(final_filename)
            
        finally:
            # 환경 변수 복원
            if old_pythonioencoding is None:
                os.environ.pop('PYTHONIOENCODING', None)
            else:
                os.environ['PYTHONIOENCODING'] = old_pythonioencoding
        
    except Exception as e:
        print(f"오류: Excel 파일 생성 중 오류가 발생했습니다: {e}")
        # 실패한 파일 정리
        try:
            Path(final_filename).unlink(missing_ok=True)
        except:
            pass
        return None
    print(f"\n✅ 성공! '{final_filename}' 파일에 {len(test_cases)}개의 테스트 시나리오를 저장했습니다.")
    
    return final_filename


def create_excel_file(test_cases: List[Dict[str, Any]], description: str = "", title: str = "") -> str:
    """
    Phase 2: 테스트 케이스로부터 엑셀 파일을 생성합니다.
    
    Args:
        test_cases: 테스트 케이스 리스트
        description: 시나리오 설명
        title: 시나리오 제목
        
    Returns:
        생성된 엑셀 파일의 파일명 (경로 제외)
    """
    # 기존 함수 호환성을 위한 JSON 구조 생성
    result_json = {
        "Test Cases": test_cases,
        "Scenario Description": description or "Phase 2 생성 시나리오",
        "Test Scenario Name": title or f"Phase 2 시나리오 {datetime.now().strftime('%Y%m%d_%H%M%S')}"
    }
    
    # 기존 save_results_to_excel 함수 사용
    full_path = save_results_to_excel(result_json)
    
    if full_path:
        # 파일명만 반환 (경로 제외)
        return Path(full_path).name
    
    # 실패 시 기본 파일명 반환
    timestamp = datetime.now().strftime(TIME_FORMAT)
    return FILE_NAME_FORMAT.format(timestamp=timestamp)