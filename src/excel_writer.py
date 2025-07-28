# src/excel_writer.py
import shutil
import openpyxl
import json
from datetime import datetime

def save_results_to_excel(result_json, template_path="templates/template.xlsx"):
    """
    LLM이 생성한 단일 JSON 객체를 파싱하여 엑셀에 저장합니다.
    """
    print("\n" + "="*50)
    print("최종 단계: 생성된 시나리오를 엑셀 파일에 저장합니다.")
    print("="*50)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_filename = f"outputs/{timestamp}_테스트_시나리오_결과.xlsx"

    try:
        shutil.copy(template_path, final_filename)
    except FileNotFoundError:
        print(f"오류: 원본 템플릿 파일('{template_path}')을 찾을 수 없습니다.")
        return
    
    workbook = openpyxl.load_workbook(final_filename)
    sheet = workbook.active
    
    # B5(개요)와 F4(제목) 채우기
    sheet['B5'] = result_json.get("Scenario Description", "개요 생성 실패")
    sheet['F4'] = result_json.get("Test Scenario Name", "제목 생성 실패")

    # 테스트 케이스 목록 가져오기
    test_cases = result_json.get("Test Cases", [])

    start_row = 11
    for i, scenario in enumerate(test_cases):
        current_row = start_row + i
        sheet[f'A{current_row}'] = scenario.get("ID", f"CMP_MES_{i+1:03d}")
        
        # 절차 필드에서 \\n을 실제 개행으로 변환
        procedure = scenario.get("절차", "").replace("\\n", "\n")
        sheet[f'B{current_row}'] = procedure
        
        # 사전조건 필드에서도 개행 처리
        precondition = scenario.get("사전조건", "").replace("\\n", "\n")
        sheet[f'C{current_row}'] = precondition
        
        test_data = scenario.get("데이터", "")
        if isinstance(test_data, (dict, list)):
            test_data = json.dumps(test_data, indent=2, ensure_ascii=False)
        else:
            test_data = str(test_data).replace("\\n", "\n")
        sheet[f'D{current_row}'] = test_data
        
        # 예상결과 필드에서도 개행 처리
        expected_result = scenario.get("예상결과", "").replace("\\n", "\n")
        sheet[f'E{current_row}'] = expected_result
        
        test_type = scenario.get("종류", "")
        sheet[f'F{current_row}'] = 'Y' if "단위" in test_type else ""
        sheet[f'G{current_row}'] = 'Y' if "통합" in test_type else ""

    workbook.save(final_filename)
    print(f"\n✅ 성공! '{final_filename}' 파일에 {len(test_cases)}개의 테스트 시나리오를 저장했습니다.")
    
    # --- [수정] 생성된 파일의 전체 경로를 반환 ---
    return final_filename