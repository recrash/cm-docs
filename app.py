# app.py
import streamlit as st
import json
import re
import os
from src.git_analyzer import get_git_analysis_text
from src.llm_handler import call_ollama_llm
from src.excel_writer import save_results_to_excel
from src.config_loader import load_config
from src.prompt_loader import create_final_prompt, add_git_analysis_to_rag, get_rag_info, index_documents_folder, get_documents_info, get_prompt_enhancer
from src.feedback_manager import FeedbackManager

# --- 1. 설정 및 화면 구성 ---
config = load_config()
if config is None:
    st.error("설정 파일(config.json)을 로드하는 데 실패했습니다. 파일을 확인해주세요.")
    st.stop() # 설정 파일 없으면 앱 중지

# 피드백 매니저 초기화
feedback_manager = FeedbackManager()

st.set_page_config(page_title="🤖 테스트 시나리오 자동 생성기", layout="wide")
st.title("🤖 테스트 시나리오 자동 생성기")

# 탭 생성
tab1, tab2 = st.tabs(["🚀 시나리오 생성", "📊 피드백 분석"])

with tab2:
    st.header("📊 피드백 분석 대시보드")
    
    # 피드백 통계 조회
    stats = feedback_manager.get_feedback_stats()
    
    if stats['total_feedback'] == 0:
        st.info("아직 수집된 피드백이 없습니다. 시나리오를 생성하고 평가를 남겨주세요!")
    else:
        # 전체 통계
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
        
        # 상세 점수 분석
        st.subheader("📈 상세 점수 분석")
        score_cols = st.columns(4)
        score_labels = ['전체 만족도', '유용성', '정확성', '완성도']
        score_keys = ['overall', 'usefulness', 'accuracy', 'completeness']
        
        for i, (col, label, key) in enumerate(zip(score_cols, score_labels, score_keys)):
            with col:
                score = stats['average_scores'][key]
                st.metric(label, f"{score:.1f}/5.0")
        
        # 개선 포인트 분석
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
        
        # 좋은 예시와 나쁜 예시
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
        
        # 프롬프트 개선 정보
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
                
                # 개선 지침 미리보기
                if st.checkbox("개선 지침 미리보기"):
                    instructions = prompt_enhancer.generate_enhancement_instructions()
                    st.text_area("현재 적용되는 개선 지침", instructions, height=200, disabled=True)
            else:
                st.info(f"💡 {3 - enhancement_summary['feedback_count']}개의 추가 피드백이 필요합니다. 피드백이 충분히 수집되면 자동으로 프롬프트 개선이 활성화됩니다.")
        
        except Exception as e:
            st.error(f"프롬프트 개선 정보 로드 중 오류: {e}")

        # 데이터 내보내기
        st.subheader("💾 데이터 내보내기")
        if st.button("피드백 데이터 JSON으로 내보내기"):
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

with tab1:
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
                
                # RAG와 피드백 기반 개선을 사용하여 프롬프트 생성
                final_prompt = create_final_prompt(git_analysis, use_rag=use_rag, use_feedback_enhancement=True)
                
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
                        
                        # --- 5. 피드백 수집 섹션 ---
                        st.subheader("📝 시나리오 평가 및 피드백")
                        st.info("생성된 시나리오에 대한 평가를 남겨주시면 향후 더 나은 시나리오 생성에 도움이 됩니다.")
                        
                        with st.form("feedback_form"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.write("**전체적인 평가**")
                                overall_score = st.slider("전체 만족도", 1, 5, 3, 
                                                        help="1: 매우 불만족, 5: 매우 만족")
                                usefulness_score = st.slider("유용성", 1, 5, 3,
                                                           help="실무에 도움이 되는 정도")
                                accuracy_score = st.slider("정확성", 1, 5, 3,
                                                         help="코드 변경사항을 정확히 반영한 정도")
                                completeness_score = st.slider("완성도", 1, 5, 3,
                                                             help="테스트 시나리오의 완성도")
                            
                            with col2:
                                st.write("**분류 및 의견**")
                                category = st.selectbox("이 시나리오를 어떻게 평가하시나요?", 
                                                      ["neutral", "good", "bad"],
                                                      format_func=lambda x: {
                                                          "good": "🟢 좋은 예시",
                                                          "bad": "🔴 나쁜 예시", 
                                                          "neutral": "🟡 보통"
                                                      }[x])
                                
                                comments = st.text_area("상세 의견 (선택사항)", 
                                                      placeholder="개선 사항이나 좋은 점을 자유롭게 작성해주세요...",
                                                      height=100)
                            
                            # 개별 테스트케이스 평가 (옵션)
                            st.write("**개별 테스트케이스 평가 (선택사항)**")
                            testcase_feedback = []
                            
                            test_cases = result_json.get('Test Cases', [])
                            if test_cases and st.checkbox("개별 테스트케이스도 평가하기"):
                                for i, test_case in enumerate(test_cases[:5]):  # 최대 5개만
                                    tc_id = test_case.get('ID', f'TC{i+1:03d}')
                                    with st.expander(f"테스트케이스 {tc_id} 평가"):
                                        tc_score = st.slider(f"점수 - {tc_id}", 1, 5, 3, key=f"tc_score_{i}")
                                        tc_comment = st.text_input(f"의견 - {tc_id}", 
                                                                 placeholder="이 테스트케이스에 대한 의견...",
                                                                 key=f"tc_comment_{i}")
                                        testcase_feedback.append({
                                            'testcase_id': tc_id,
                                            'score': tc_score,
                                            'comments': tc_comment
                                        })
                            
                            # 피드백 제출
                            if st.form_submit_button("피드백 제출하기 ✅", type="primary"):
                                feedback_data = {
                                    'overall_score': overall_score,
                                    'usefulness_score': usefulness_score,
                                    'accuracy_score': accuracy_score,
                                    'completeness_score': completeness_score,
                                    'category': category,
                                    'comments': comments,
                                    'testcase_feedback': testcase_feedback
                                }
                                
                                # 피드백 저장
                                success = feedback_manager.save_feedback(
                                    git_analysis=git_analysis,
                                    scenario_content=result_json,
                                    feedback_data=feedback_data,
                                    repo_path=repo_path
                                )
                                
                                if success:
                                    st.success("🎉 피드백이 성공적으로 저장되었습니다! 소중한 의견 감사합니다.")
                                    
                                    # 피드백 통계 표시
                                    stats = feedback_manager.get_feedback_stats()
                                    st.info(f"현재까지 총 {stats['total_feedback']}개의 피드백이 수집되었습니다.")
                                else:
                                    st.error("피드백 저장 중 오류가 발생했습니다. 다시 시도해주세요.")

                    except Exception as e:
                        status.update(label="오류 발생!", state="error", expanded=True)
                        st.error(f"결과 처리 중 오류가 발생했습니다: {e}")
                        st.code(raw_response) # 오류 시 LLM 원본 응답 보여주기