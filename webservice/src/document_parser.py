from docx import Document

def parse_change_request(file_path):
    """
    변경관리요청서(.docx) 파일을 파싱하여 주요 정보를 추출합니다.
    """
    try:
        doc = Document(file_path)
        extracted_data = {}

        # 문서의 모든 표(table)를 순회
        for table in doc.tables:
            for row in table.rows:
                # 표의 각 행(row)을 돌면서 키워드를 찾는다.
                # 셀이 비어있는 경우를 대비해 예외처리
                try:
                    key_cell = row.cells[0].text.strip()
                    value_cell = row.cells[1].text.strip()

                    if "제 목" in key_cell:
                        # '제 목'과 'Title'이 같은 셀에 있으므로,
                        # '변경관리번호' 앞까지 잘라서 제목만 추출
                        title_text = row.cells[1].text
                        extracted_data['title'] = title_text.split(',')[0].strip()

                    if "목적/개선내용" in key_cell:
                        extracted_data['purpose'] = row.cells[1].text.strip()

                except IndexError:
                    # 행에 셀이 부족한 경우 건너뛰기
                    continue
        
        return extracted_data

    except FileNotFoundError:
        return {"error": "파일을 찾을 수 없습니다. 파일 경로를 확인하세요."}
    except Exception as e:
        return {"error": f"파일을 읽는 중 오류가 발생했습니다: {e}"}

# --- 메인 코드 실행 부분 ---
if __name__ == "__main__":
    # 네가 업로드한 파일 이름을 여기에 넣으면 돼
    file_name = "[250724 전수민] 변경관리요청서 천안) CMP MES_20250710-0002 품종 정렬 기능 추가 요청.docx"
    
    # 가상환경이 켜진 터미널에서 실행해야 해!
    parsed_info = parse_change_request(file_name)

    if "error" in parsed_info:
        print(f"오류: {parsed_info['error']}")
    else:
        print("✅ 문서 파싱 성공!")
        print(f"📄 제 목: {parsed_info.get('title', '추출 실패')}")
        print(f"🎯 목 적: {parsed_info.get('purpose', '추출 실패')}")