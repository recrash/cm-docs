# src/prompt_loader.py
from .config_loader import load_config
from .vector_db.rag_manager import RAGManager
from .vector_db.document_indexer import DocumentIndexer

# 전역 인스턴스들 (지연 로딩을 위해 None으로 시작)
_rag_manager = None
_document_indexer = None

def get_rag_manager(lazy_load=True):
    """RAG 매니저 싱글톤 인스턴스 반환"""
    global _rag_manager
    if _rag_manager is None and not lazy_load:
        config = load_config()
        if config and config.get('rag', {}).get('enabled', False):
            rag_config = config['rag']
            print("RAG Manager 초기화 중... (임베딩 모델 로딩)")
            _rag_manager = RAGManager(
                persist_directory=rag_config.get('persist_directory', 'vector_db_data'),
                embedding_model=rag_config.get('embedding_model', 'jhgan/ko-sroberta-multitask'),
                chunk_size=rag_config.get('chunk_size', 1000),
                chunk_overlap=rag_config.get('chunk_overlap', 200)
            )
            print("RAG Manager 초기화 완료")
    return _rag_manager

def load_prompt(path="prompts/final_prompt.txt"):
    """텍스트 파일에서 프롬프트 템플릿을 읽어옵니다."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"오류: 프롬프트 파일('{path}')을 찾을 수 없습니다.")
        return None

def create_final_prompt(git_analysis, use_rag=True):
    """
    프롬프트 템플릿을 로드하고, RAG를 사용하여 향상된 프롬프트를 생성합니다.
    
    Args:
        git_analysis: Git 분석 결과
        use_rag: RAG 사용 여부
    
    Returns:
        완성된 프롬프트 문자열
    """
    template = load_prompt()
    if not template:
        return None
    
    # RAG가 활성화되어 있고 use_rag가 True인 경우
    config = load_config()
    if use_rag and config and config.get('rag', {}).get('enabled', False):
        try:
            # 실제 RAG 사용시에만 로딩
            rag_manager = get_rag_manager(lazy_load=False)
            if rag_manager:
                return rag_manager.create_enhanced_prompt(template, git_analysis, use_rag=True)
        except Exception as e:
            print(f"RAG 프롬프트 생성 중 오류 발생: {e}")
            print("기본 프롬프트를 사용합니다.")
    
    # RAG를 사용하지 않거나 오류가 발생한 경우 기본 프롬프트 사용
    return template.format(git_analysis=git_analysis)

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
        print(f"RAG에 Git 분석 추가 중 오류 발생: {e}")
    
    return 0

def get_document_indexer(lazy_load=True):
    """문서 인덱서 싱글톤 인스턴스 반환"""
    global _document_indexer
    if _document_indexer is None and not lazy_load:
        config = load_config()
        if config and config.get('rag', {}).get('enabled', False):
            rag_manager = get_rag_manager(lazy_load=False)
            if rag_manager:
                documents_folder = config.get('documents_folder', 'documents')
                _document_indexer = DocumentIndexer(rag_manager, documents_folder)
    return _document_indexer

def index_documents_folder(force_reindex=False):
    """documents 폴더의 모든 문서를 인덱싱"""
    config = load_config()
    if not config or not config.get('rag', {}).get('enabled', False):
        return {'status': 'error', 'message': 'RAG가 비활성화되어 있습니다.'}
    
    try:
        # 실제 인덱싱시에만 로딩
        indexer = get_document_indexer(lazy_load=False)
        if indexer:
            return indexer.index_documents_folder(force_reindex)
    except Exception as e:
        print(f"문서 인덱싱 중 오류 발생: {e}")
        return {'status': 'error', 'message': str(e)}
    
    return {'status': 'error', 'message': '인덱서 초기화 실패'}

def get_documents_info():
    """문서 폴더 정보 반환 (지연 로딩)"""
    config = load_config()
    if not config or not config.get('rag', {}).get('enabled', False):
        return {'enabled': False}
    
    # 인덱서가 로드되지 않은 경우 기본 정보만 반환
    indexer = get_document_indexer(lazy_load=True)
    if indexer is None:
        import os
        documents_folder = config.get('documents_folder', 'documents')
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
        print(f"문서 정보 조회 중 오류 발생: {e}")
    
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
            'documents': {'enabled': True, 'folder_path': config.get('documents_folder', 'documents'), 'supported_files': 0, 'total_files': 0, 'file_types': {}}
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
        print(f"RAG 정보 조회 중 오류 발생: {e}")
    
    return {'enabled': False, 'loaded': False}