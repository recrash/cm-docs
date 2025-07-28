# app.py
import streamlit as st
import json
import re
import os
from src.git_analyzer import get_git_analysis_text
from src.llm_handler import call_ollama_llm
from src.excel_writer import save_results_to_excel
from src.config_loader import load_config
from src.prompt_loader import create_final_prompt, add_git_analysis_to_rag, get_rag_info, index_documents_folder, get_documents_info

# --- 1. 설정 및 화면 구성 ---
config = load_config()
if config is None:
    st.error("설정 파일(config.json)을 로드하는 데 실패했습니다. 파일을 확인해주세요.")
    st.stop() # 설정 파일 없으면 앱 중지

st.set_page_config(page_title="🤖 테스트 시나리오 자동 생성기", layout="wide")
st.title("🤖 테스트 시나리오 자동 생성기")
st.info("Git 저장소의 변경사항을 분석하여 테스트 시나리오 엑셀 파일을 자동으로 생성합니다.")

# 세션 상태에서 RAG 정보 관리
def get_rag_info_cached():
    """세션 상태를 사용하여 RAG 정보를 캐시"""
    if 'rag_info' not in st.session_state:
        st.session_state.rag_info = get_rag_info()
    return st.session_state.rag_info

def refresh_rag_info():
    """RAG 정보 새로고침"""
    if 'rag_info' in st.session_state:
        del st.session_state.rag_info

# --- RAG 정보 표시 ---
rag_info = get_rag_info_cached()
if not rag_info.get('enabled', False):
    st.error("⚠️ RAG 시스템이 비활성화되어 있습니다. config.json에서 RAG를 활성화해주세요.")
    st.stop()

with st.expander("🧠 RAG 시스템 정보", expanded=False):
    chroma_info = rag_info.get('chroma_info', {})
    loaded_status = "로드됨" if rag_info.get('loaded', False) else "대기 중 (지연 로딩)"
    st.write(f"**벡터 DB 상태:** {loaded_status}")
    st.write(f"**저장된 문서 수:** {chroma_info.get('count', 0)}개")
    st.write(f"**임베딩 모델:** {chroma_info.get('embedding_model', 'Unknown')}")
    st.write(f"**청크 크기:** {rag_info.get('chunk_size', 0)}자")
    
    # 문서 정보 표시
    documents_info = rag_info.get('documents', {})
    if documents_info.get('enabled'):
        st.write(f"**문서 폴더:** {documents_info.get('folder_path', 'Unknown')}")
        st.write(f"**지원 파일:** {documents_info.get('supported_files', 0)}개 / {documents_info.get('total_files', 0)}개")
        
        if documents_info.get('file_types'):
            file_types_str = ", ".join([f"{ext}({count})" for ext, count in documents_info['file_types'].items()])
            st.write(f"**파일 유형:** {file_types_str}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📚 문서 인덱싱"):
            with st.spinner("문서 인덱싱 중..."):
                result = index_documents_folder()
                if result['status'] == 'success':
                    st.success(f"인덱싱 완료! {result['indexed_count']}개 파일, {result['total_chunks_added']}개 청크 추가")
                    refresh_rag_info()
                    st.rerun()
                else:
                    st.error(f"인덱싱 실패: {result.get('message', 'Unknown error')}")
    
    with col2:
        if st.button("🔄 전체 재인덱싱"):
            with st.spinner("전체 재인덱싱 중..."):
                result = index_documents_folder(force_reindex=True)
                if result['status'] == 'success':
                    st.success(f"재인덱싱 완료! {result['indexed_count']}개 파일, {result['total_chunks_added']}개 청크 추가")
                    refresh_rag_info()
                    st.rerun()
                else:
                    st.error(f"재인덱싱 실패: {result.get('message', 'Unknown error')}")
    
    with col3:
        if st.button("🗑️ 벡터 DB 초기화"):
            try:
                from src.prompt_loader import get_rag_manager
                rag_manager = get_rag_manager(lazy_load=False)
                if rag_manager:
                    rag_manager.clear_database()
                    st.success("벡터 데이터베이스가 초기화되었습니다.")
                    refresh_rag_info()
                    st.rerun()
            except Exception as e:
                st.error(f"데이터베이스 초기화 중 오류 발생: {e}")

# --- 2. 사용자 입력 ---
repo_path = st.text_input(
    "분석할 Git 저장소의 로컬 경로를 입력하세요:", 
    config.get("repo_path", "") # 설정 파일에서 기본 경로 가져오기
)

# RAG는 항상 활성화됨을 표시
st.info("🧠 RAG 기능이 자동으로 활성화되어 과거 분석 데이터를 참조합니다.")
st.info("💾 생성된 시나리오와 분석 결과는 자동으로 RAG 시스템에 저장됩니다.")

# RAG 기능은 항상 사용하고, 결과도 항상 저장
use_rag = True
save_to_rag = True

# --- 3. 생성 버튼 및 로직 실행 ---
if st.button("테스트 시나리오 생성하기 🚀"):
    
    if not repo_path or not os.path.isdir(repo_path):
        st.error("유효한 Git 저장소 경로를 입력해주세요.")
    else:
        with st.status("시나리오 생성 중...", expanded=True) as status:
            
            st.write("1. Git 변경 내역을 분석 중입니다...")
            git_analysis = get_git_analysis_text(repo_path)
            
            # RAG에 Git 분석 결과 저장 (항상 실행)
            st.write("1-1. 분석 결과를 RAG 시스템에 저장 중입니다...")
            added_chunks = add_git_analysis_to_rag(git_analysis, repo_path)
            if added_chunks > 0:
                st.write(f"   ✅ {added_chunks}개 청크가 벡터 DB에 저장되었습니다.")
                refresh_rag_info()  # RAG 정보 새로고침
            else:
                st.write("   ⚠️ 벡터 DB 저장에 실패했습니다.")
            
            st.write("2. LLM을 호출하여 모든 정보를 생성합니다... (시간이 걸릴 수 있습니다)")
            st.write("   🧠 RAG 기능을 사용하여 관련 컨텍스트를 포함합니다...")
            
            model_name = config.get("model_name", "qwen3:8b")
            timeout = config.get("timeout", 600)
            
            # RAG 사용 여부에 따라 프롬프트 생성
            final_prompt = create_final_prompt(git_analysis, use_rag=use_rag)
            
            raw_response = call_ollama_llm(final_prompt, model=model_name, timeout=timeout)
            
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
                    
                    # 엑셀 파일 저장하고, 저장된 파일 경로를 돌려받음
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