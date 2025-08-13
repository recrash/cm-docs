"""
RAG 시스템 관련 API 라우터
"""

from fastapi import APIRouter, HTTPException
import os
import sys
import logging

# 기존 모듈 import
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.prompt_loader import (
    get_rag_info, 
    index_documents_folder, 
    get_rag_manager
)

from backend.models.rag import (
    RAGInfo,
    IndexingRequest,
    IndexingResult,
    DocumentsInfo
)

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/info", response_model=RAGInfo)
async def get_rag_system_info():
    """RAG 시스템 정보 조회 API"""
    
    logger.info("RAG 시스템 정보 조회 요청")
    
    try:
        rag_info = get_rag_info()
        logger.info(f"RAG 시스템 정보 조회 성공: 문서 수={rag_info.get('documents', {}).get('count', 0)}")
        return RAGInfo(**rag_info)
        
    except Exception as e:
        logger.error(f"RAG 시스템 정보 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"RAG 시스템 정보 조회 중 오류가 발생했습니다: {str(e)}")

@router.post("/index", response_model=IndexingResult)
async def index_documents(request: IndexingRequest):
    """문서 인덱싱 API"""
    
    logger.info(f"문서 인덱싱 요청: force_reindex={request.force_reindex}")
    
    try:
        # 싱글톤 인스턴스 강제 리셋 (path fix 적용)
        import src.prompt_loader as pl
        pl._document_indexer = None
        
        result = index_documents_folder(force_reindex=request.force_reindex)
        logger.info(f"문서 인덱싱 성공: 인덱싱된 문서 수={result.get('indexed_count', 0)}")
        return IndexingResult(**result)
        
    except Exception as e:
        logger.error(f"문서 인덱싱 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"문서 인덱싱 중 오류가 발생했습니다: {str(e)}")

@router.delete("/clear")
async def clear_vector_database():
    """벡터 데이터베이스 초기화 API"""
    
    logger.info("벡터 데이터베이스 초기화 요청")
    
    try:
        rag_manager = get_rag_manager(lazy_load=False)
        if not rag_manager:
            logger.error("RAG 매니저를 초기화할 수 없음")
            raise HTTPException(status_code=500, detail="RAG 시스템을 초기화할 수 없습니다.")
        
        rag_manager.clear_database()
        logger.info("벡터 데이터베이스 초기화 성공")
        
        return {"message": "벡터 데이터베이스가 성공적으로 초기화되었습니다."}
        
    except Exception as e:
        logger.error(f"벡터 데이터베이스 초기화 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"벡터 데이터베이스 초기화 중 오류가 발생했습니다: {str(e)}")

@router.get("/documents/info", response_model=DocumentsInfo)
async def get_documents_info():
    """문서 정보 조회 API"""
    
    logger.info("문서 정보 조회 요청")
    
    try:
        rag_info = get_rag_info()
        documents_info = rag_info.get('documents', {})
        logger.info(f"문서 정보 조회 성공: 문서 수={documents_info.get('count', 0)}")
        return DocumentsInfo(**documents_info)
        
    except Exception as e:
        logger.error(f"문서 정보 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"문서 정보 조회 중 오류가 발생했습니다: {str(e)}")

@router.get("/status")
async def get_rag_status():
    """RAG 시스템 상태 조회 API"""
    
    logger.info("RAG 시스템 상태 조회 요청")
    
    try:
        # 설정에서 RAG 활성화 여부 먼저 확인
        from src.config_loader import load_config
        config = load_config()
        
        if not config or not config.get('rag', {}).get('enabled', False):
            logger.info("RAG 시스템이 설정에서 비활성화됨")
            return {
                "status": "disabled",
                "message": "RAG 시스템이 설정에서 비활성화되어 있습니다.",
                "auto_activated": False,
                "document_count": 0,
                "embedding_model": "Unknown",
                "chunk_size": 0
            }
        
        # RAG 매니저 상태 확인
        try:
            rag_manager = get_rag_manager(lazy_load=True)
            if rag_manager:
                status = "active"
                message = "RAG 시스템이 서버 시작 시 자동으로 활성화되었습니다."
                auto_activated = True
                logger.info("RAG 시스템이 활성 상태")
            else:
                # RAG가 설정에서 활성화되어 있지만 아직 로드되지 않은 경우
                status = "ready"
                message = "RAG 시스템이 활성화되어 있으며 필요 시 자동으로 로드됩니다."
                auto_activated = True
                logger.info("RAG 시스템이 준비 상태")
        except Exception as e:
            status = "error"
            message = f"RAG 시스템 오류: {str(e)}"
            auto_activated = False
            logger.error(f"RAG 시스템 오류: {str(e)}")
        
        # 기본 정보 수집
        rag_info = get_rag_info()
        chroma_info = rag_info.get('chroma_info', {})
        
        result = {
            "status": status,
            "message": message,
            "auto_activated": auto_activated,
            "document_count": chroma_info.get('count', 0),
            "embedding_model": chroma_info.get('embedding_model', 'Unknown'),
            "chunk_size": rag_info.get('chunk_size', 0)
        }
        
        logger.info(f"RAG 상태 조회 성공: status={status}, document_count={result['document_count']}")
        return result
        
    except Exception as e:
        logger.error(f"RAG 상태 조회 실패: {str(e)}")
        return {
            "status": "error",
            "message": f"RAG 상태 조회 중 오류가 발생했습니다: {str(e)}",
            "auto_activated": False,
            "document_count": 0,
            "embedding_model": "Unknown",
            "chunk_size": 0
        }

@router.get("/auto-activation")
async def get_auto_activation_status():
    """RAG 시스템 자동 활성화 상태 조회 API"""
    
    logger.info("RAG 자동 활성화 상태 조회 요청")
    
    try:
        from src.config_loader import load_config
        config = load_config()
        
        if not config or not config.get('rag', {}).get('enabled', False):
            logger.info("RAG 자동 활성화가 설정에서 비활성화됨")
            return {
                "auto_activation_enabled": False,
                "reason": "RAG가 설정에서 비활성화되어 있습니다.",
                "documents_folder": config.get('documents_folder', 'documents') if config else 'documents',
                "documents_folder_exists": False,
                "startup_initialization": False
            }
        
        documents_folder = config.get('documents_folder', 'documents')
        documents_folder_exists = os.path.exists(documents_folder)
        
        # RAG 매니저가 이미 로드되었는지 확인
        rag_manager = get_rag_manager(lazy_load=True)
        startup_initialization = rag_manager is not None
        
        result = {
            "auto_activation_enabled": True,
            "reason": "RAG 시스템이 서버 시작 시 자동으로 활성화됩니다.",
            "documents_folder": os.path.abspath(documents_folder) if documents_folder_exists else documents_folder,
            "documents_folder_exists": documents_folder_exists,
            "startup_initialization": startup_initialization,
            "background_indexing": documents_folder_exists
        }
        
        logger.info(f"RAG 자동 활성화 상태 조회 성공: enabled=True, startup_init={startup_initialization}")
        return result
        
    except Exception as e:
        logger.error(f"RAG 자동 활성화 상태 조회 실패: {str(e)}")
        return {
            "auto_activation_enabled": False,
            "reason": f"오류: {str(e)}",
            "documents_folder": "Unknown",
            "documents_folder_exists": False,
            "startup_initialization": False
        }

@router.get("/debug")
async def debug_rag_system():
    """RAG 시스템 디버깅 정보 조회 API"""
    import os
    
    logger.info("RAG 시스템 디버깅 정보 조회 요청")
    
    try:
        from src.config_loader import load_config
        config = load_config()
        
        debug_info = {
            "working_directory": os.getcwd(),
            "config_loaded": config is not None,
            "rag_enabled": config.get('rag', {}).get('enabled', False) if config else False,
            "documents_folder_config": config.get('documents_folder', 'documents') if config else None,
        }
        
        if config:
            documents_folder = config.get('documents_folder', 'documents')
            # 절대 경로로 변환 테스트
            if not os.path.isabs(documents_folder):
                current_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(os.path.dirname(current_dir))
                abs_documents_folder = os.path.join(project_root, documents_folder)
            else:
                abs_documents_folder = documents_folder
                
            debug_info.update({
                "documents_folder_absolute": abs_documents_folder,
                "documents_folder_exists": os.path.exists(abs_documents_folder),
                "project_root": os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            })
        
        logger.info(f"RAG 디버깅 정보 조회 성공: config_loaded={debug_info['config_loaded']}, rag_enabled={debug_info['rag_enabled']}")
        return debug_info
        
    except Exception as e:
        logger.error(f"RAG 디버깅 정보 조회 실패: {str(e)}")
        return {
            "error": str(e),
            "working_directory": os.getcwd()
        }