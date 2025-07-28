# src/prompt_loader.py
from .config_loader import load_config
from .vector_db.rag_manager import RAGManager

# 전역 RAG 매니저 인스턴스
_rag_manager = None

def get_rag_manager():
    """RAG 매니저 싱글톤 인스턴스 반환"""
    global _rag_manager
    if _rag_manager is None:
        config = load_config()
        if config and config.get('rag', {}).get('enabled', False):
            rag_config = config['rag']
            _rag_manager = RAGManager(
                persist_directory=rag_config.get('persist_directory', 'vector_db_data'),
                embedding_model=rag_config.get('embedding_model', 'jhgan/ko-sroberta-multitask'),
                chunk_size=rag_config.get('chunk_size', 1000),
                chunk_overlap=rag_config.get('chunk_overlap', 200)
            )
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
            rag_manager = get_rag_manager()
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
        rag_manager = get_rag_manager()
        if rag_manager:
            return rag_manager.add_git_analysis(git_analysis, repo_path)
    except Exception as e:
        print(f"RAG에 Git 분석 추가 중 오류 발생: {e}")
    
    return 0

def get_rag_info():
    """RAG 시스템 정보 반환"""
    config = load_config()
    if not config or not config.get('rag', {}).get('enabled', False):
        return {'enabled': False}
    
    try:
        rag_manager = get_rag_manager()
        if rag_manager:
            info = rag_manager.get_system_info()
            info['enabled'] = True
            return info
    except Exception as e:
        print(f"RAG 정보 조회 중 오류 발생: {e}")
    
    return {'enabled': False}