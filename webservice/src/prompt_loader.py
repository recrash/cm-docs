# src/prompt_loader.py
import os
import logging
from .config_loader import load_config
from .vector_db.rag_manager import RAGManager
from .vector_db.document_indexer import DocumentIndexer
from .feedback_manager import FeedbackManager
from .prompt_enhancer import PromptEnhancer

logger = logging.getLogger(__name__)

# 전역 인스턴스들 (지연 로딩을 위해 None으로 시작)
_rag_manager = None
_document_indexer = None
_feedback_manager = None
_prompt_enhancer = None

def get_rag_manager(lazy_load=True):
    """RAG 매니저 싱글톤 인스턴스 반환"""
    global _rag_manager
    if _rag_manager is None and not lazy_load:
        # config_loader의 표준 로직 사용
        config = load_config()
        if config and config.get('rag', {}).get('enabled', False):
            rag_config = config['rag']
            logger.info("RAG Manager initializing... (loading embedding model)")
            _rag_manager = RAGManager(
                persist_directory=rag_config.get('persist_directory', 'vector_db_data'),
                embedding_model=rag_config.get('embedding_model', 'jhgan/ko-sroberta-multitask'),
                local_model_path=rag_config.get('local_embedding_model_path'),
                chunk_size=rag_config.get('chunk_size', 1000),
                chunk_overlap=rag_config.get('chunk_overlap', 200)
            )
            logger.info("RAG Manager initialization complete")
    return _rag_manager

def get_feedback_manager():
    """피드백 매니저 싱글톤 인스턴스 반환"""
    global _feedback_manager
    if _feedback_manager is None:
        _feedback_manager = FeedbackManager()
    return _feedback_manager

def get_prompt_enhancer():
    """프롬프트 개선기 싱글톤 인스턴스 반환"""
    global _prompt_enhancer
    if _prompt_enhancer is None:
        feedback_manager = get_feedback_manager()
        _prompt_enhancer = PromptEnhancer(feedback_manager)
    return _prompt_enhancer

def reset_feedback_cache():
    """피드백 관련 캐시 리셋 (피드백 데이터 초기화 후 호출)"""
    global _feedback_manager, _prompt_enhancer
    # 기존 인스턴스들을 리셋하여 다음 호출 시 새로 생성되도록 함
    _feedback_manager = None
    _prompt_enhancer = None
    logger.info("Feedback related cache has been reset.")

def load_prompt(path="prompts/final_prompt.txt"):
    """텍스트 파일에서 프롬프트 템플릿을 읽어옵니다."""
    try:
        # 상대 경로인 경우 프로젝트 루트에서 찾기
        if not os.path.isabs(path):
            # 현재 파일의 절대 경로를 기준으로 프로젝트 루트 찾기
            current_file = os.path.abspath(__file__)
            # /path/to/project/src/prompt_loader.py -> /path/to/project
            project_root = os.path.dirname(os.path.dirname(current_file))
            path = os.path.join(project_root, path)
        
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Error: Prompt file ('{path}') not found.")
        return None

def create_final_prompt(
        git_analysis: str,
        use_rag: bool = True,
        use_feedback_enhancement: bool = True,
        performance_mode: bool = False
) -> str:
    """
    프롬프트 템플릿을 로드하고, RAG·피드백을 반영해 최종 프롬프트를 생성한다.

    Args:
        git_analysis                : Git 변경 분석 결과
        use_rag                     : RAG 사용 여부
        use_feedback_enhancement    : 피드백 기반 개선 적용 여부
        performance_mode            : True 시 프롬프트 길이를 제한해 속도 우선
    """
    template = load_prompt()
    if not template:
        return None

    final_prompt = None

    # RAG가 활성화되어 있고 use_rag가 True인 경우
    config = load_config()
    if use_rag and config and config.get('rag', {}).get('enabled', False):
        try:
            # 실제 RAG 사용시에만 로딩
            rag_manager = get_rag_manager(lazy_load=False)
            if rag_manager:
                final_prompt = rag_manager.create_enhanced_prompt(template, git_analysis, use_rag=True)
        except Exception as e:
            logger.error(f"Error occurred during RAG prompt generation: {e}")
            logger.info("Using basic prompt.")

    # RAG를 사용하지 않거나 오류가 발생한 경우 기본 프롬프트 사용
    if final_prompt is None:
        final_prompt = template.format(git_analysis=git_analysis)

    # 피드백 기반 프롬프트 개선 적용
    if use_feedback_enhancement:
        try:
            prompt_enhancer = get_prompt_enhancer()
            enhanced_prompt = prompt_enhancer.enhance_prompt(final_prompt)

            # 개선 요약 출력 (디버깅용)
            enhancement_summary = prompt_enhancer.get_enhancement_summary()
            if enhancement_summary['feedback_count'] >= 3:
                logger.info(f"Feedback-based prompt improvement applied: {enhancement_summary['feedback_count']} feedback items reflected")
                logger.info(f"Average score: {enhancement_summary['average_score']:.1f}/5.0")
                if enhancement_summary['improvement_areas']:
                    logger.info(f"Improvement areas: {', '.join(enhancement_summary['improvement_areas'])}")

            return enhanced_prompt
        except Exception as e:
            logger.error(f"Error occurred during feedback-based prompt improvement: {e}")
            logger.info("Using basic prompt.")

    # --- NEW : 성능 모드 프롬프트 길이 제한 ----------------
    if performance_mode and len(final_prompt) > 32000:   # ≒ 8k 토큰
        logger.info(f"[PERF] Prompt length {len(final_prompt)} > 32000 → trimming.")
        final_prompt = final_prompt[:32000]
    # ------------------------------------------------------

    return final_prompt

def add_git_analysis_to_rag(git_analysis, repo_path):
    """
    Git 분석 결과를 RAG 시스템에 추가

    Args:
        git_analysis: Git 분석 결과
        repo_path: Git 저장소 경로

    Returns:
        추가된 청크 수
    """
    config = load_config()
    if not config or not config.get('rag', {}).get('enabled', False):
        return 0

    try:
        # 실제 RAG 사용시에만 로딩
        rag_manager = get_rag_manager(lazy_load=False)
        if rag_manager:
            return rag_manager.add_git_analysis(git_analysis, repo_path)
    except Exception as e:
        logger.error(f"Error occurred while adding Git analysis to RAG: {e}")

    return 0

def get_document_indexer(lazy_load=True):
    """문서 인덱서 싱글톤 인스턴스 반환"""
    global _document_indexer
    if _document_indexer is None and not lazy_load:
        config = load_config()
        if config and config.get('rag', {}).get('enabled', False):
            rag_manager = get_rag_manager(lazy_load=False)
            if rag_manager:
                from .config_loader import get_data_directory_path
                import os
                data_root = get_data_directory_path()
                documents_folder = os.path.join(data_root, 'documents')
                _document_indexer = DocumentIndexer(rag_manager, documents_folder)
    return _document_indexer

def index_documents_folder(force_reindex=False):
    """documents 폴더의 모든 문서를 인덱싱"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"[DEBUG] index_documents_folder 함수 시작 - force_reindex: {force_reindex}")
    
    config = load_config()
    if not config or not config.get('rag', {}).get('enabled', False):
        logger.warning("[DEBUG] RAG가 비활성화되어 있습니다.")
        return {'status': 'error', 'message': 'RAG가 비활성화되어 있습니다.'}

    logger.info("[DEBUG] RAG 설정 확인 완료, 인덱서 로딩 시작")
    try:
        # 실제 인덱싱시에만 로딩
        logger.info("[DEBUG] get_document_indexer 호출 시작")
        indexer = get_document_indexer(lazy_load=False)
        logger.info(f"[DEBUG] get_document_indexer 호출 완료 - indexer: {indexer is not None}")
        
        if indexer:
            logger.info("[DEBUG] indexer.index_documents_folder 호출 시작")
            result = indexer.index_documents_folder(force_reindex)
            logger.info(f"[DEBUG] indexer.index_documents_folder 호출 완료 - 결과: {result}")
            return result
    except Exception as e:
        logger.error(f"[DEBUG] 문서 인덱싱 중 오류 발생: {e}")
        logger.exception("[DEBUG] 예외 상세 정보:")
        return {'status': 'error', 'message': str(e)}

    logger.warning("[DEBUG] 인덱서 초기화 실패")
    return {'status': 'error', 'message': '인덱서 초기화 실패'}

def get_documents_info():
    """문서 폴더 정보 반환 (지연 로딩)"""
    config = load_config()
    if not config or not config.get('rag', {}).get('enabled', False):
        return {'enabled': False}

    # 인덱서가 로드되지 않은 경우 기본 정보만 반환
    indexer = get_document_indexer(lazy_load=True)
    if indexer is None:
        from .config_loader import get_data_directory_path
        import os
        data_root = get_data_directory_path()
        documents_folder = os.path.join(data_root, 'documents')
        return {
            'enabled': True,
            'folder_path': os.path.abspath(documents_folder) if os.path.exists(documents_folder) else documents_folder,
            'total_files': 0,
            'supported_files': 0,
            'file_types': {}
        }

    try:
        folder_info = indexer.get_folder_info()
        folder_info['enabled'] = True
        return folder_info
    except Exception as e:
        logger.error(f"Error occurred while retrieving document information: {e}")

    return {'enabled': False}

def get_rag_info():
    """RAG 시스템 정보 반환 (지연 로딩)"""
    config = load_config()
    if not config or not config.get('rag', {}).get('enabled', False):
        return {'enabled': False}

    # RAG가 활성화되어 있지만 아직 로드되지 않은 경우
    rag_manager = get_rag_manager(lazy_load=True)
    if rag_manager is None:
        # 기본 정보만 반환 (실제 로딩은 하지 않음)
        from .config_loader import get_data_directory_path
        import os
        rag_config = config.get('rag', {})
        return {
            'enabled': True,
            'loaded': False,
            'chroma_info': {
                'count': 0,
                'embedding_model': rag_config.get('embedding_model', 'jhgan/ko-sroberta-multitask')
            },
            'chunk_size': rag_config.get('chunk_size', 1000),
            'chunk_overlap': rag_config.get('chunk_overlap', 200),
            'documents': {
                'enabled': True, 
                'folder_path': os.path.join(get_data_directory_path(), 'documents'), 
                'supported_files': 0, 
                'total_files': 0, 
                'file_types': {}
            }
        }

    try:
        info = rag_manager.get_system_info()
        info['enabled'] = True
        info['loaded'] = True

        # 문서 정보도 포함
        documents_info = get_documents_info()
        if documents_info.get('enabled'):
            info['documents'] = documents_info

        return info
    except Exception as e:
        logger.error(f"Error occurred while retrieving RAG information: {e}")

    return {'enabled': False, 'loaded': False}