# app.py
import streamlit as st
import json
import re
import os
# 리팩토링된 모듈에서 함수들을 가져옴
from src.git_analyzer import get_git_analysis_text
from src.llm_handler import call_ollama_llm
from src.excel_writer import save_results_to_excel

# --- 1. 화면 구성 ---
st.set_page_config(page_title="🤖 테스트 시나리오 자동 생성기", layout="wide")

st.title("🤖 테스트 시나리오 자동 생성기")
st.info("Git 저장소의 변경사항을 분석하여 테스트 시나리오 엑셀 파일을 자동으로 생성합니다.")

# 사용자 입력
repo_path = st.text_input(
    "분석할 Git 저장소의 로컬 경로를 입력하세요:", 
    "/Users/recrash/Documents/Workspace/CPMES" # 예시 경로
)

# --- 2. 생성 버튼 ---
if st.button("테스트 시나리오 생성하기 🚀"):
    
    # 입력값 검증
    if not repo_path or not os.path.isdir(repo_path):
        st.error("유효한 Git 저장소 경로를 입력해주세요.")
    else:
        # st.status를 사용해 진행 상황을 깔끔하게 표시
        with st.status("시나리오 생성 중...", expanded=True) as status:
            
            st.write("1. Git 변경 내역을 분석 중입니다...")
            git_analysis = get_git_analysis_text(repo_path)
            
            
            st.write("2. LLM을 호출하여 모든 정보를 생성합니다... (시간이 걸릴 수 있습니다)")
            model_name = "qwen3:8b" # 안정적인 모델 추천
            
            # --- [수정] main.py와 동일한 최종 프롬프트로 교체 ---
            final_prompt = f"""너는 주어진 Git 변경 내역을 분석하여, 완벽한 테스트 시나리오 문서를 생성하는 전문가다.

**지시사항:**
1. 먼저, 주어진 '분석할 Git 변경 내역'을 바탕으로 최종 JSON 결과물을 만들기 위한 너의 생각 과정을 `<thinking>` 태그 안에 단계별로 서술해라. 모든 생각은 한국어로 작성한다.
2. 생각 과정이 끝나면, 그 생각을 바탕으로 최종 결과물을 `<json>` 태그 안에 완벽한 JSON 객체로 생성해라.
3. 최종 JSON 객체의 모든 문자열 값은 **반드시 한국어로** 작성해야 하며, 어떤 필드도 비워두어서는 안 된다.

### 분석할 Git 변경 내역:
{git_analysis}

### 최종 출력 형식:
<thinking>
1. Git 변경 내역 분석: 핵심 변경 사항 파악.
2. 개요 및 제목 구상: 전체 시나리오를 대표할 'Scenario Description'과 'Test Scenario Name' 구상.
3. 테스트 케이스 3개 구상: 각 변경 사항을 검증할 구체적인 ID, 절차, 사전조건 등을 작성.
4. 최종 JSON 생성: 위 내용을 종합하여 최종 JSON 구조에 맞게 내용 채우기.
</thinking>
<json>
{{
  "Scenario Description": "사용자 관점에서 이 테스트 전체의 목적을 요약한 설명.",
  "Test Scenario Name": "테스트 시나리오 전체를 대표하는 명확한 제목.",
  "Test Cases": [
    {{ "ID": "CMP_MES_001", "절차": "...", "사전조건": "...", "데이터": "...", "예상결과": "...", "종류": "..." }},
    {{ "ID": "CMP_MES_002", "절차": "...", "사전조건": "...", "데이터": "...", "예상결과": "...", "종류": "..." }},
    {{ "ID": "CMP_MES_003", "절차": "...", "사전조건": "...", "데이터": "...", "예상결과": "...", "종류": "..." }}
  ]
}}
</json>
"""
            raw_response = call_ollama_llm(final_prompt, model=model_name, timeout=600)
            
            if not raw_response:
                status.update(label="오류 발생!", state="error", expanded=True)
                st.error("LLM으로부터 응답을 받지 못했습니다.")
            else:
                try:
                    st.write("3. LLM 응답을 파싱하여 엑셀 파일을 준비합니다...")
                    json_match = re.search(r'<json>(.*?)</json>', raw_response, re.DOTALL)
                    if not json_match:
                        raise ValueError("LLM 응답에서 <json> 블록을 찾을 수 없습니다.")
                    
                    json_string = json_match.group(1).strip()
                    result_json = json.loads(json_string)
                    
                    final_filename = save_results_to_excel(result_json)
                    
                    status.update(label="생성 완료!", state="complete", expanded=False)
                    
                    # --- 4. 결과 출력 및 다운로드 ---
                    st.success("테스트 시나리오 생성이 완료되었습니다!")
                    
                    with open(final_filename, "rb") as file:
                        st.download_button(
                            label="엑셀 파일 다운로드 📥",
                            data=file,
                            file_name=os.path.basename(final_filename),
                            mime="application/vnd.ms-excel"
                        )
                    
                    st.subheader("📊 생성 결과 미리보기")
                    st.write(f"**개요:** {result_json.get('Scenario Description', '')}")
                    st.write(f"**제목:** {result_json.get('Test Scenario Name', '')}")
                    st.dataframe(result_json.get('Test Cases', []), use_container_width=True)

                except Exception as e:
                    status.update(label="오류 발생!", state="error", expanded=True)
                    st.error(f"결과 처리 중 오류가 발생했습니다: {e}")
                    st.code(raw_response) # 오류 시 LLM 원본 응답 보여주기