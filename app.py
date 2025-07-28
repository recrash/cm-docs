# app.py
import streamlit as st
import json
import re
import os
from src.git_analyzer import get_git_analysis_text
from src.llm_handler import call_ollama_llm
from src.excel_writer import save_results_to_excel

# --- 1. 화면 구성 ---
st.set_page_config(page_title="🤖 테스트 시나리오 자동 생성기", layout="wide")

st.title("🤖 테스트 시나리오 자동 생성기")
st.info("Git 저장소의 변경사항을 분석하여 테스트 시나리오 엑셀 파일을 자동으로 생성합니다.")

repo_path = st.text_input(
    "분석할 Git 저장소의 로컬 경로를 입력하세요:", 
    "/Users/recrash/Documents/Workspace/CPMES" # 예시 경로
)

if st.button("테스트 시나리오 생성하기 🚀"):
    
    if not repo_path or not os.path.isdir(repo_path):
        st.error("유효한 Git 저장소 경로를 입력해주세요.")
    else:
        # --- [수정] expand -> expanded 로 오타 수정 ---
        with st.status("시나리오 생성 중...", expanded=True) as status:
            
            st.write("1. Git 변경 내역을 분석 중입니다...")
            git_analysis = get_git_analysis_text(repo_path)
            
            st.write("2. LLM을 호출하여 모든 정보를 생성합니다... (시간이 걸릴 수 있습니다)")
            model_name = "qwen3:14b"
            
            final_prompt = f"""너는 주어진 Git 변경 내역을 분석하여, 완벽한 테스트 시나리오 문서를 생성하는 전문가다.
            반드시 최종 응답은 단 하나의 완벽한 JSON 객체여야 한다. 다른 설명은 절대 추가하지 마라.
            모든 문자열 값은 반드시 한국어로 작성해야 하며, 어떤 필드도 비워두어서는 안 된다.
            ### 분석할 Git 변경 내역:
            {git_analysis}
            ### 최종 JSON 출력 형식:
            {{
              "Scenario Description": "사용자 관점에서 이 테스트 전체의 목적을 요약한 설명.",
              "Test Scenario Name": "테스트 시나오 전체를 대표하는 명확한 제목.",
              "Test Cases": [
                {{ "ID": "CMP_MES_001", "절차": "...", "사전조건": "...", "데이터": "...", "예상결과": "...", "종류": "..." }},
                {{ "ID": "CMP_MES_002", "절차": "...", "사전조건": "...", "데이터": "...", "예상결과": "...", "종류": "..." }},
                {{ "ID": "CMP_MES_003", "절차": "...", "사전조건": "...", "데이터": "...", "예상결과": "...", "종류": "..." }}
              ]
            }}
            ### 출력 (오직 위 JSON 형식의 최종본 하나만 응답):
            """
            raw_response = call_ollama_llm(final_prompt, model=model_name, format="json", timeout=600)
            
            if not raw_response:
                status.update(label="오류 발생!", state="error", expanded=True)
                st.error("LLM으로부터 응답을 받지 못했습니다.")
            else:
                try:
                    result_json = json.loads(raw_response)
                    st.write("3. 생성된 시나리오를 엑셀 파일로 저장합니다...")
                    
                    final_filename = save_results_to_excel(result_json)
                    
                    status.update(label="생성 완료!", state="complete", expanded=False)
                    
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

                except json.JSONDecodeError:
                    status.update(label="오류 발생!", state="error", expanded=True)
                    st.error(f"최종 JSON 파싱에 실패했습니다.")
                    st.code(raw_response)