# app.py
import streamlit as st
import json
import re
import os
from src.git_analyzer import get_git_analysis_text
from src.llm_handler import call_ollama_llm
from src.excel_writer import save_results_to_excel
from src.config_loader import load_config
from src.prompt_loader import create_final_prompt, add_git_analysis_to_rag, get_rag_info, index_documents_folder, get_documents_info, get_prompt_enhancer, reset_feedback_cache
from src.feedback_manager import FeedbackManager

# --- 1. 설정 및 화면 구성 ---
config = load_config()
if config is None:
    st.error("설정 파일(config.json)을 로드하는 데 실패했습니다. 파일을 확인해주세요.")
    st.stop()

# RAG 시스템 미리 로딩
@st.cache_resource
def initialize_rag_system():
    """앱 시작 시 RAG 시스템을 미리 초기화"""
    if config and config.get('rag', {}).get('enabled', False):
        with st.spinner("RAG 시스템 초기화 중..."):
            try:
                from src.prompt_loader import get_rag_manager
                rag_manager = get_rag_manager(lazy_load=False)
                if rag_manager:
                    return True
            except Exception as e:
                st.error(f"RAG 시스템 초기화 실패: {e}")
                return False
    return False

# RAG 시스템 초기화
rag_initialized = initialize_rag_system()

# 피드백 매니저 초기화
feedback_manager = FeedbackManager()

# 세션 상태 초기화 함수
def initialize_session_state():
    """세션 상태를 초기화합니다."""
    if 'generated' not in st.session_state:
        st.session_state.generated = False
    if 'result_json' not in st.session_state:
        st.session_state.result_json = None
    if 'final_filename' not in st.session_state:
        st.session_state.final_filename = None
    if 'git_analysis' not in st.session_state:
        st.session_state.git_analysis = None
    if 'repo_path' not in st.session_state:
        st.session_state.repo_path = None
    if 'file_data' not in st.session_state:
        st.session_state.file_data = None
    if 'file_name' not in st.session_state:
        st.session_state.file_name = None
    if 'real_modal_visible' not in st.session_state:
        st.session_state.real_modal_visible = False
    if 'real_modal_type' not in st.session_state:
        st.session_state.real_modal_type = None
    if 'feedback_submitted' not in st.session_state:
        st.session_state.feedback_submitted = False
    if 'feedback_show_success' not in st.session_state:
        st.session_state.feedback_show_success = False

    if 'rag_info' not in st.session_state:
        st.session_state.rag_info = None

# 세션 상태 초기화
initialize_session_state()

# 실제 피드백 모달 함수 (전역 범위에서 정의)
@st.dialog("피드백")
def show_real_feedback_modal(feedback_type, git_analysis, result_json, repo_path):

    
    st.write("새로 생성된 시나리오에 대한 의견을 주세요 (선택 사항)")
    
    if feedback_type == 'like':
        st.write("👍 **어떤 점이 도움이 되었나요?**")
        placeholder = "예: 시나리오가 구체적이고 실용적이었습니다."
    else:
        st.write("👎 **어떤 점이 아쉬웠나요?**")
        placeholder = "예: 테스트 절차가 불명확하거나 실제 환경과 맞지 않았습니다."
    
    # 피드백 텍스트 입력
    feedback_text = st.text_area(
        "상세한 의견을 알려주세요",
        placeholder=placeholder,
        height=100,
        help="귀하의 피드백은 향후 더 나은 시나리오 생성에 활용됩니다."
    )
    
    # 개별 테스트케이스 평가 옵션
    testcase_feedback = []
    test_cases = result_json.get('Test Cases', [])
    
    with st.expander("개별 테스트케이스 평가 (선택사항)"):
        st.write("각 테스트케이스에 대한 구체적인 평가를 남겨주세요.")
        
        if not test_cases:
            st.info("평가할 테스트케이스가 없습니다.")
        else:
            for i, test_case in enumerate(test_cases[:5]):  # 최대 5개
                tc_id = test_case.get('ID', f'TC{i+1:03d}')
                tc_desc = test_case.get('절차', '테스트 절차')
                # 설명이 길면 자르기
                if len(tc_desc) > 50:
                    tc_desc = tc_desc[:50] + '...'
                
                st.write(f"**{tc_id}: {tc_desc}**")
                
                # 더 직관적인 평가 UI
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    rating = st.select_slider(
                        f"평가 - {tc_id}", 
                        options=['매우 나쁨', '나쁨', '보통', '좋음', '매우 좋음'],
                        value='보통',
                        key=f"real_rating_{i}"
                    )
                
                with col2:
                    comment = st.text_input(
                        f"의견 - {tc_id}", 
                        placeholder="이 테스트케이스에 대한 구체적인 의견...",
                        key=f"real_comment_{i}"
                    )
                
                # 점수로 변환 (매우 나쁨:1, 나쁨:2, 보통:3, 좋음:4, 매우 좋음:5)
                score_map = {'매우 나쁨': 1, '나쁨': 2, '보통': 3, '좋음': 4, '매우 좋음': 5}
                
                testcase_feedback.append({
                    'testcase_id': tc_id,
                    'score': score_map[rating],
                    'comments': comment
                })
                
                # 구분선 추가
                if i < len(test_cases[:5]) - 1:
                    st.divider()
    
    # 제출 완료 후 전체 너비로 성공 메시지 표시
    if st.session_state.feedback_show_success:
        st.markdown(
            """
            <div style="
                background-color: #d4edda;
                border: 1px solid #c3e6cb;
                color: #155724;
                padding: 15px;
                border-radius: 8px;
                text-align: center;
                font-size: 18px;
                font-weight: 600;
                width: 100%;
                margin: 20px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            ">
                🎉 피드백이 성공적으로 제출되었습니다!
            </div>
            """,
            unsafe_allow_html=True
        )
        st.balloons()  # 축하 효과
        
        # 간단한 결과 요약
        if feedback_text:
            st.write(f"**제출된 의견:** {feedback_text[:50]}{'...' if len(feedback_text) > 50 else ''}")
        
        # 통계 표시
        stats = feedback_manager.get_feedback_stats()                        
    
    # 제출되지 않은 경우에만 버튼 표시
    if not st.session_state.feedback_show_success:
        # 버튼
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("취소", key="real_modal_cancel", use_container_width=True):
                st.session_state.real_modal_visible = False
                st.session_state.real_modal_type = None
                st.session_state.feedback_submitted = False
                st.session_state.feedback_show_success = False
                st.rerun()
        
        with col2:
            if st.button("제출", key="real_modal_submit", type="primary", use_container_width=True):
                # 실제 피드백 저장
                feedback_data = {
                    'overall_score': 4 if feedback_type == 'like' else 2,
                    'usefulness_score': 4 if feedback_type == 'like' else 2,
                    'accuracy_score': 4 if feedback_type == 'like' else 2,
                    'completeness_score': 4 if feedback_type == 'like' else 2,
                    'category': 'good' if feedback_type == 'like' else 'bad',
                    'comments': feedback_text,
                    'testcase_feedback': testcase_feedback
                }
                
                success = feedback_manager.save_feedback(
                    git_analysis=git_analysis,
                    scenario_content=result_json,
                    feedback_data=feedback_data,
                    repo_path=repo_path
                )
                
                if success:
                    st.session_state.feedback_submitted = True
                    st.session_state.feedback_show_success = True
                    st.rerun()  # 즉시 다시 렌더링하여 성공 메시지 표시
                else:
                    st.error("피드백 저장 중 오류가 발생했습니다.")

# 페이지 설정
st.set_page_config(page_title="🤖 테스트 시나리오 자동 생성기", layout="wide")
st.title("🤖 테스트 시나리오 자동 생성기")

# 탭 생성
tab1, tab2 = st.tabs(["🚀 시나리오 생성", "📊 피드백 분석"])

# 시나리오 생성 탭
with tab1:
    st.info("Git 저장소의 변경사항을 분석하여 테스트 시나리오 엑셀 파일을 자동으로 생성합니다.")

    # 세션 상태에서 RAG 정보 관리
    def get_rag_info_cached():
        if st.session_state.rag_info is None:
            st.session_state.rag_info = get_rag_info()
        return st.session_state.rag_info

    def refresh_rag_info():
        st.session_state.rag_info = None

    # RAG 정보 표시
    if not rag_initialized:
        st.error("⚠️ RAG 시스템이 비활성화되어 있거나 초기화에 실패했습니다. config.json에서 RAG를 활성화하고 앱을 재시작해주세요.")
        st.stop()
    
    rag_info = get_rag_info_cached()

    with st.expander("🧠 RAG 시스템 정보", expanded=False):
        chroma_info = rag_info.get('chroma_info', {})
        loaded_status = "로드됨" if rag_initialized else "대기 중 (지연 로딩)"
        st.write(f"**벡터 DB 상태:** {loaded_status}")
        st.write(f"**저장된 문서 수:** {chroma_info.get('count', 0)}개")
        st.write(f"**임베딩 모델:** {chroma_info.get('embedding_model', 'Unknown')}")
        st.write(f"**청크 크기:** {rag_info.get('chunk_size', 0)}자")
        
        documents_info = rag_info.get('documents', {})
        if documents_info.get('enabled'):
            st.write(f"**문서 폴더:** {documents_info.get('folder_path', 'Unknown')}")
            st.write(f"**지원 파일:** {documents_info.get('supported_files', 0)}개 / {documents_info.get('total_files', 0)}개")
            
            if documents_info.get('file_types'):
                file_types_str = ", ".join([f"{ext}({count})" for ext, count in documents_info['file_types'].items()])
                st.write(f"**파일 유형:** {file_types_str}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📚 문서 인덱싱", key="index_btn"):
                with st.spinner("문서 인덱싱 중..."):
                    result = index_documents_folder()
                    if result['status'] == 'success':
                        st.success(f"인덱싱 완료! {result['indexed_count']}개 파일, {result['total_chunks_added']}개 청크 추가")
                        refresh_rag_info()
                    else:
                        st.error(f"인덱싱 실패: {result.get('message', 'Unknown error')}")
        
        with col2:
            if st.button("🔄 전체 재인덱싱", key="reindex_btn"):
                with st.spinner("전체 재인덱싱 중..."):
                    result = index_documents_folder(force_reindex=True)
                    if result['status'] == 'success':
                        st.success(f"재인덱싱 완료! {result['indexed_count']}개 파일, {result['total_chunks_added']}개 청크 추가")
                        refresh_rag_info()
                    else:
                        st.error(f"재인덱싱 실패: {result.get('message', 'Unknown error')}")
        
        with col3:
            if st.button("🗑️ 벡터 DB 초기화", key="clear_btn"):
                try:
                    from src.prompt_loader import get_rag_manager
                    rag_manager = get_rag_manager(lazy_load=False)
                    if rag_manager:
                        rag_manager.clear_database()
                        st.success("벡터 데이터베이스가 초기화되었습니다.")
                        refresh_rag_info()
                except Exception as e:
                    st.error(f"데이터베이스 초기화 중 오류 발생: {e}")

    # 사용자 입력
    repo_path = st.text_input(
        "분석할 Git 저장소의 로컬 경로를 입력하세요:", 
        config.get("repo_path", "")
    )

    # --- 사이드바: 성능 최적화 옵션 ---
    st.sidebar.subheader("⚡ 성능 최적화")
    use_performance_mode = st.sidebar.checkbox(
        "성능 최적화 모드",
        value=True,
        key="performance_mode",
        help="프롬프트 크기를 제한하여 LLM 응답 속도를 향상시킵니다."
    )

    # 생성 버튼
    if st.button("테스트 시나리오 생성하기 🚀", key="generate_btn"):
        if not repo_path or not os.path.isdir(repo_path):
            st.error("유효한 Git 저장소 경로를 입력해주세요.")
        else:
            # 결과 변수 초기화
            result_json = None
            final_filename = None

            with st.status("시나리오 생성 중...", expanded=True) as status:
                st.write("1. Git 변경 내역을 분석 중입니다...")
                git_analysis = get_git_analysis_text(repo_path)
                
                st.write("1-1. 분석 결과를 RAG 시스템에 저장 중입니다...")
                added_chunks = add_git_analysis_to_rag(git_analysis, repo_path)
                if added_chunks > 0:
                    st.write(f"   ✅ {added_chunks}개 청크가 벡터 DB에 저장되었습니다.")
                else:
                    st.write("   ⚠️ 벡터 DB 저장에 실패했습니다.")
                
                st.write("2. LLM을 호출하여 모든 정보를 생성합니다... (시간이 걸릴 수 있습니다)")
                st.write("   🧠 RAG 기능을 사용하여 관련 컨텍스트를 포함합니다...")
                
                model_name = config.get("model_name", "qwen3:8b")
                timeout = config.get("timeout", 600)
                
                # 프롬프트 생성 시 성능 모드 적용
                final_prompt = create_final_prompt(
                    git_analysis, 
                    use_rag=True, 
                    use_feedback_enhancement=True,
                    performance_mode=use_performance_mode
                )
                
                # LLM 호출 전후 시간 측정
                import time
                start_time = time.time()
                raw_response = call_ollama_llm(final_prompt, model=model_name, timeout=timeout)
                end_time = time.time()

                st.write(f"⏱️ LLM 응답 시간: {end_time - start_time:.1f}초")
                st.write(f"📏 프롬프트 크기: {len(final_prompt):,}자")
                
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
                        
                        # 파일 데이터를 세션 상태에 저장
                        if final_filename and os.path.exists(final_filename):
                            with open(final_filename, "rb") as file:
                                file_data = file.read()
                                file_name = os.path.basename(final_filename)
                        
                        # 세션 상태에 결과 저장
                        st.session_state.generated = True
                        st.session_state.result_json = result_json
                        st.session_state.final_filename = final_filename
                        st.session_state.git_analysis = git_analysis
                        st.session_state.repo_path = repo_path
                        st.session_state.file_data = file_data
                        st.session_state.file_name = file_name
                        
                        status.update(label="생성 완료!", state="complete", expanded=False)

                    except Exception as e:
                        status.update(label="오류 발생!", state="error", expanded=True)
                        st.error(f"결과 처리 중 오류가 발생했습니다: {e}")
                        st.code(raw_response)

    # ------ 생성된 결과가 있으면 표시 ------
    if st.session_state.generated:                
        # 세션 상태에서 값 불러오기
        result_json = st.session_state.result_json
        final_filename = st.session_state.final_filename
        git_analysis = st.session_state.git_analysis
        repo_path = st.session_state.repo_path
        
        st.success("테스트 시나리오 생성이 완료되었습니다!")

        # 파일 데이터를 세션 상태에 저장하여 재읽기 방지
        if st.session_state.file_data is None and final_filename and os.path.exists(final_filename):
            with open(final_filename, "rb") as file:
                st.session_state.file_data = file.read()
                st.session_state.file_name = os.path.basename(final_filename)
        
        # 세션 상태에서 파일 데이터 사용
        if st.session_state.file_data is not None:
            st.download_button(
                label="엑셀 파일 다운로드 📥",
                data=st.session_state.file_data,
                file_name=st.session_state.file_name,
                mime="application/vnd.ms-excel",
                key="download_button"
            )

        st.subheader("📊 생성 결과 미리보기")
        st.write(f"**개요:** {result_json.get('Scenario Description', '')}")
        st.write(f"**제목:** {result_json.get('Test Scenario Name', '')}")
        
        # Test Cases 데이터 전처리 - \n을 실제 개행으로 변환
        test_cases = result_json.get('Test Cases', [])
        processed_cases = []
        
        for case in test_cases:
            processed_case = {}
            for key, value in case.items():
                if isinstance(value, str):
                    # \n을 실제 개행으로 변환
                    processed_case[key] = value.replace('\\n', '\n')
                else:
                    processed_case[key] = value
            processed_cases.append(processed_case)
        
        st.dataframe(processed_cases, use_container_width=True)

        # 피드백 수집 섹션
        st.subheader("📝 시나리오 평가 및 피드백")
        st.info("생성된 시나리오에 대한 평가를 남겨주시면 향후 더 나은 시나리오 생성에 도움이 됩니다.")

        st.write("**이 시나리오가 도움이 되었나요?**")
        col1, col2, _ = st.columns([1, 1, 8])

        with col1:
            if st.button("👍 좋아요", key="real_like_btn", help="이 시나리오가 유용했습니다", use_container_width=True):
                # 피드백 관련 세션 상태 초기화
                st.session_state.feedback_submitted = False
                st.session_state.feedback_show_success = False
                st.session_state.real_modal_visible = True
                st.session_state.real_modal_type = 'like'

        with col2:
            if st.button("👎 개선 필요", key="real_dislike_btn", help="이 시나리오에 개선이 필요합니다", use_container_width=True):
                # 피드백 관련 세션 상태 초기화
                st.session_state.feedback_submitted = False
                st.session_state.feedback_show_success = False
                st.session_state.real_modal_visible = True
                st.session_state.real_modal_type = 'dislike'

    # ------ 피드백 모달 표시 ------
    if st.session_state.real_modal_visible:    
        modal_type = st.session_state.real_modal_type
        if modal_type and st.session_state.generated:
            result_json = st.session_state.result_json
            git_analysis = st.session_state.git_analysis
            repo_path = st.session_state.repo_path
            
            show_real_feedback_modal(modal_type, git_analysis, result_json, repo_path)

# 피드백 분석 탭
with tab2:
    st.header("📊 피드백 분석 대시보드")
    
    stats = feedback_manager.get_feedback_stats()
    
    if stats['total_feedback'] == 0:
        st.info("아직 수집된 피드백이 없습니다. 시나리오를 생성하고 평가를 남겨주세요!")
    else:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("총 피드백 수", stats['total_feedback'])
        with col2:
            good_count = stats['category_distribution'].get('good', 0)
            st.metric("좋은 예시", good_count, f"{good_count/stats['total_feedback']*100:.1f}%")
        with col3:
            bad_count = stats['category_distribution'].get('bad', 0)
            st.metric("나쁜 예시", bad_count, f"{bad_count/stats['total_feedback']*100:.1f}%")
        with col4:
            avg_score = stats['average_scores']['overall']
            st.metric("평균 만족도", f"{avg_score:.1f}/5.0")
        
        st.subheader("📈 상세 점수 분석")
        score_cols = st.columns(4)
        score_labels = ['전체 만족도', '유용성', '정확성', '완성도']
        score_keys = ['overall', 'usefulness', 'accuracy', 'completeness']
        
        for i, (col, label, key) in enumerate(zip(score_cols, score_labels, score_keys)):
            with col:
                score = stats['average_scores'][key]
                st.metric(label, f"{score:.1f}/5.0")
        
        st.subheader("🎯 개선 포인트 분석")
        insights = feedback_manager.get_improvement_insights()
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**낮은 점수(2점 이하) 비율**")
            problem_areas = insights['problem_areas']
            
            if any(v > 0 for v in problem_areas.values()):
                import pandas as pd
                df = pd.DataFrame([problem_areas])
                st.bar_chart(df.T, height=200)
            else:
                st.success("모든 영역에서 좋은 평가를 받고 있습니다!")
        
        with col2:
            st.write("**부정적 피드백 샘플**")
            if insights['negative_feedback_count'] > 0:
                st.write(f"총 {insights['negative_feedback_count']}개의 부정적 피드백")
                for i, comment in enumerate(insights['sample_negative_comments']):
                    st.write(f"{i+1}. {comment[:100]}...")
            else:
                st.success("부정적 피드백이 없습니다!")
        
        st.subheader("📚 예시 모음")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**🟢 좋은 예시 (최근 5개)**")
            good_examples = feedback_manager.get_feedback_examples('good', 5)
            for example in good_examples:
                with st.expander(f"점수: {example['overall_score']}/5 - {example['timestamp'][:10]}"):
                    st.write(f"**시나리오 제목:** {example['scenario_content'].get('Test Scenario Name', 'N/A')}")
                    if example['comments']:
                        st.write(f"**의견:** {example['comments']}")
        
        with col2:
            st.write("**🔴 나쁜 예시 (최근 5개)**")
            bad_examples = feedback_manager.get_feedback_examples('bad', 5)
            for example in bad_examples:
                with st.expander(f"점수: {example['overall_score']}/5 - {example['timestamp'][:10]}"):
                    st.write(f"**시나리오 제목:** {example['scenario_content'].get('Test Scenario Name', 'N/A')}")
                    if example['comments']:
                        st.write(f"**개선 의견:** {example['comments']}")
        
        st.subheader("🔧 프롬프트 개선 현황")
        try:
            prompt_enhancer = get_prompt_enhancer()
            enhancement_summary = prompt_enhancer.get_enhancement_summary()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("개선 적용 상태", 
                         "활성화" if enhancement_summary['feedback_count'] >= 3 else "대기 중",
                         f"{enhancement_summary['feedback_count']}/3 피드백")
            with col2:
                if enhancement_summary['improvement_areas']:
                    st.metric("개선 필요 영역", f"{len(enhancement_summary['improvement_areas'])}개")
                else:
                    st.metric("개선 필요 영역", "없음")
            with col3:
                available_examples = enhancement_summary['good_examples_available'] + enhancement_summary['bad_examples_available']
                st.metric("사용 가능한 예시", f"{available_examples}개")
            
            if enhancement_summary['feedback_count'] >= 3:
                st.success("✅ 피드백 기반 프롬프트 개선이 활성화되어 있습니다.")
                if st.checkbox("개선 지침 미리보기"):
                    instructions = prompt_enhancer.generate_enhancement_instructions()
                    st.text_area("현재 적용되는 개선 지침", instructions, height=200, disabled=True)
            else:
                st.info(f"💡 {3 - enhancement_summary['feedback_count']}개의 추가 피드백이 필요합니다. 피드백이 충분히 수집되면 자동으로 프롬프트 개선이 활성화됩니다.")
        
        except Exception as e:
            st.error(f"프롬프트 개선 정보 로드 중 오류: {e}")

        st.subheader("💾 데이터 내보내기")
        if st.button("피드백 데이터 JSON으로 내보내기", key="export_btn"):
            success = feedback_manager.export_feedback_data("feedback_export.json")
            if success:
                st.success("피드백 데이터가 feedback_export.json 파일로 저장되었습니다.")
                with open("feedback_export.json", "rb") as file:
                    st.download_button(
                        label="JSON 파일 다운로드",
                        data=file,
                        file_name="feedback_export.json",
                        mime="application/json"
                    )
            else:
                st.error("데이터 내보내기 중 오류가 발생했습니다.")

        st.subheader("🗑️ 피드백 데이터 초기화")
        st.warning("⚠️ 초기화 작업은 되돌릴 수 없습니다. 초기화 전 자동으로 백업이 생성됩니다.")
        
        # 카테고리별 피드백 개수 표시
        category_counts = feedback_manager.get_feedback_count_by_category()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"👍 좋은 피드백: {category_counts['good']}개")
        with col2:
            st.write(f"👎 나쁜 피드백: {category_counts['bad']}개")
        with col3:
            st.write(f"😐 중립 피드백: {category_counts['neutral']}개")
        
        reset_option = st.selectbox(
            "초기화 범위 선택:",
            ["전체 피드백 삭제", "좋은 피드백만 삭제", "나쁜 피드백만 삭제", "중립 피드백만 삭제"],
            key="reset_option"
        )
        
        if st.button("피드백 초기화 실행", key="reset_feedback_btn", type="secondary"):
            if reset_option == "전체 피드백 삭제":
                if stats['total_feedback'] == 0:
                    st.info("삭제할 피드백이 없습니다.")
                else:
                    success = feedback_manager.clear_all_feedback(create_backup=True)
                    if success:
                        reset_feedback_cache()  # 캐시 리셋
                        st.success(f"모든 피드백 {stats['total_feedback']}개가 삭제되었습니다. (백업 생성됨)")
                        st.rerun()  # 화면 새로고침
                    else:
                        st.error("피드백 삭제 중 오류가 발생했습니다.")
            else:
                # 카테고리별 삭제
                category_map = {
                    "좋은 피드백만 삭제": "good",
                    "나쁜 피드백만 삭제": "bad", 
                    "중립 피드백만 삭제": "neutral"
                }
                category = category_map[reset_option]
                target_count = category_counts[category]
                
                if target_count == 0:
                    st.info(f"삭제할 {reset_option.replace('만 삭제', '')}가 없습니다.")
                else:
                    success = feedback_manager.clear_feedback_by_category(category, create_backup=True)
                    if success:
                        reset_feedback_cache()  # 캐시 리셋
                        st.success(f"{reset_option.replace('만 삭제', '')} {target_count}개가 삭제되었습니다. (백업 생성됨)")
                        st.rerun()  # 화면 새로고침
                    else:
                        st.error("피드백 삭제 중 오류가 발생했습니다.")
        
        st.info("💡 백업 파일은 'backups/' 폴더에 'feedback_backup_YYYYMMDD_HHMMSS.json' 형식으로 저장됩니다.")