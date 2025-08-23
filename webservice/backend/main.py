"""
FastAPI 백엔드 메인 애플리케이션
TestscenarioMaker의 API 서버
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import sys
import asyncio
import logging
from pathlib import Path
from contextlib import asynccontextmanager

# 기존 src 모듈 import를 위한 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.logging_config import setup_logging
from backend.routers import scenario, feedback, rag, files, logging as logging_router
from backend.routers.v2.router import v2_router

# 로깅 설정 초기화
setup_logging()
logger = logging.getLogger(__name__)

async def startup_rag_system():
    """백엔드 시작 시 RAG 시스템 자동 초기화"""
    logger.info("RAG 시스템 자동 초기화 시작...")
    logger.info("STEP 1: startup_rag_system 함수 진입")
    
    try:
        logger.info("STEP 2: try 블록 진입")
        
        # 설정 로드 및 RAG 활성화 확인
        logger.info("STEP 3: config_loader 모듈 임포트 시도")
        from src.config_loader import load_config
        logger.info("STEP 4: config_loader 모듈 임포트 성공")
        
        # working directory 문제 해결을 위해 하이브리드 경로 사용
        import os
        from pathlib import Path
        
        config_path = None
        
        # 1순위: Production 환경 (WEBSERVICE_DATA_PATH 환경변수 기반)
        if os.getenv('WEBSERVICE_DATA_PATH'):
            config_path = Path(os.getenv('WEBSERVICE_DATA_PATH')) / "config.json"
            logger.info(f"STEP 5A: Production 모드 - 환경변수 기반 경로: {config_path}")
            logger.info(f"STEP 5B: Production config 파일 존재 여부: {config_path.exists()}")
            
            if not config_path.exists():
                logger.warning(f"STEP 5C: Production config 파일이 없음, Development 경로로 fallback")
                config_path = None
        
        # 2순위: Development 환경 (코드 옆 config.json)
        if not config_path or not config_path.exists():
            backend_dir = Path(__file__).parent  # backend 폴더
            webservice_root = backend_dir.parent  # webservice 폴더  
            config_path = webservice_root / "config.json"
            logger.info(f"STEP 5D: Development 모드 - 코드 기반 경로: {config_path}")
            logger.info(f"STEP 5E: Development config 파일 존재 여부: {config_path.exists()}")
        
        logger.info(f"STEP 5F: 최종 선택된 config 경로: {config_path}")
        logger.info(f"STEP 5G: 현재 working directory: {os.getcwd()}")
        
        logger.info("STEP 6: load_config 함수 호출 시도")
        config = load_config(str(config_path))
        logger.info(f"STEP 7: config 로드 완료 - 결과: {config is not None}")
        
        if not config:
            logger.error("STEP 7A: config가 None입니다 - 설정 파일을 읽지 못했습니다")
            logger.warning("RAG가 설정에서 비활성화되어 있습니다.")
            return
        
        rag_enabled = config.get('rag', {}).get('enabled', False)
        logger.info(f"STEP 7B: RAG enabled 상태: {rag_enabled}")
        
        if not rag_enabled:
            logger.info(f"STEP 8: RAG 설정이 비활성화됨: {config.get('rag', 'rag 키 없음')}")
            logger.warning("RAG가 설정에서 비활성화되어 있습니다.")
            return
        
        logger.info("STEP 9: RAG 설정 확인 완료 - 활성화 상태")
            
        logger.info("RAG 설정 확인 완료")
        
        # RAG 매니저 초기화 (지연 로딩 비활성화)
        from src.prompt_loader import get_rag_manager
        rag_manager = get_rag_manager(lazy_load=False)
        
        if rag_manager:
            logger.info("RAG 매니저 초기화 완료")
            
            # 문서 폴더 자동 인덱싱 시도 (webservice/documents 사용)
            documents_folder = config.get('documents_folder', 'webservice/documents')
            
            # 상대 경로를 절대 경로로 변환
            if not os.path.isabs(documents_folder):
                # backend 폴더에서 webservice 폴더로 이동
                webservice_root = os.path.dirname(os.path.abspath(__file__))
                if documents_folder.startswith('webservice/'):
                    # webservice/documents -> documents로 변경
                    documents_folder = documents_folder.replace('webservice/', '')
                documents_folder = os.path.abspath(os.path.join(webservice_root, documents_folder))
            
            if os.path.exists(documents_folder):
                logger.info(f"문서 폴더 발견: {documents_folder}")
                logger.info("백그라운드에서 문서 인덱싱 시작...")
                
                # 백그라운드에서 인덱싱 실행 (서버 시작을 차단하지 않음)
                asyncio.create_task(auto_index_documents())
            else:
                logger.info(f"문서 폴더가 없습니다: {documents_folder}")
                logger.info("문서를 추가하면 자동으로 인덱싱됩니다.")
        else:
            logger.error("RAG 매니저 초기화 실패")
            
    except Exception as e:
        logger.error(f"RAG 시스템 자동 초기화 중 치명적인 오류 발생: {str(e)}")
        logger.exception("예외 상세 정보:")
        logger.warning("RAG가 설정에서 비활성화되어 있습니다.")  # 기존 메시지와 동일하게 출력
        logger.info("수동으로 /api/rag/index 엔드포인트를 사용하여 초기화할 수 있습니다.")

async def auto_index_documents():
    """백그라운드에서 문서 자동 인덱싱"""
    try:
        from src.prompt_loader import index_documents_folder
        result = index_documents_folder(force_reindex=False)
        
        if result.get('status') == 'success':
            indexed_count = result.get('indexed_documents', 0)
            total_chunks = result.get('total_chunks', 0)
            logger.info(f"문서 인덱싱 완료: {indexed_count}개 문서, {total_chunks}개 청크")
        else:
            message = result.get('message', '알 수 없는 오류')
            logger.error(f"문서 인덱싱 실패: {message}")
            
    except Exception as e:
        logger.exception(f"백그라운드 문서 인덱싱 중 오류 발생")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 애플리케이션 라이프사이클 매니저"""
    # 시작 시 실행
    logger.info("=== LIFESPAN MANAGER START ===")
    logger.info("애플리케이션 시작...")
    logger.info("startup_rag_system 호출 시작")
    try:
        await startup_rag_system()
        logger.info("startup_rag_system 호출 완료")
    except Exception as e:
        logger.error(f"startup_rag_system 호출 중 예외 발생: {str(e)}")
        logger.exception("라이프사이클 매니저 예외 상세:")
    logger.info("=== LIFESPAN MANAGER START COMPLETE ===")
    yield
    # 종료 시 실행
    logger.info("=== LIFESPAN MANAGER SHUTDOWN ===")
    logger.info("애플리케이션 종료.")

app = FastAPI(
    title="TestscenarioMaker API",
    description="Git 분석 기반 테스트 시나리오 자동 생성 API",
    version="2.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React 개발 서버
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(scenario.router, prefix="/api/scenario", tags=["Scenario"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["Feedback"])
app.include_router(rag.router, prefix="/api/rag", tags=["RAG"])
app.include_router(files.router, prefix="/api/files", tags=["Files"])
app.include_router(logging_router.router, prefix="/api", tags=["Logging"])

# v2 API 라우터 등록 (CLI 연동용)
app.include_router(v2_router, prefix="/api")

# 정적 파일 서빙 (프로덕션용)
static_dir = Path(__file__).parent.parent / "frontend/dist"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

@app.get("/api")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "TestscenarioMaker API v2.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/api/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy"}

if __name__ == "__main__":
    # This is for development purposes only. 
    # For production, use a proper ASGI server like Gunicorn.
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None # Disable uvicorn's default logger to use our custom one
    )
