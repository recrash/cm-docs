# app.py
import streamlit as st
import json
import re
import os
# 리팩토링된 모듈에서 함수들을 가져옴
from src.git_analyzer import get_git_analysis_text
from src.llm_handler import call_ollama_llm
from src.excel_writer import save_results_to_excel
from src.prompt_loader import create_final_prompt

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
            
            # 현재 하드코딩된 프롬프트를 제거하고 create_final_prompt() 함수 사용
            final_prompt = create_final_prompt(
                git_analysis, 
                use_rag=False,  # main.py는 RAG 기능 없이 기본 기능만 사용
                use_feedback_enhancement=False,
                performance_mode=False
            )
            
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