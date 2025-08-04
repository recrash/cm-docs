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

# 로깅 설정 초기화
setup_logging()
logger = logging.getLogger(__name__)

async def startup_rag_system():
    """백엔드 시작 시 RAG 시스템 자동 초기화"""
    try:
        logger.info("🚀 RAG 시스템 자동 초기화 시작...")
        
        # 설정 로드 및 RAG 활성화 확인
        from src.config_loader import load_config
        config = load_config()
        
        if not config or not config.get('rag', {}).get('enabled', False):
            logger.warning("❌ RAG가 설정에서 비활성화되어 있습니다.")
            return
            
        logger.info("✅ RAG 설정 확인 완료")
        
        # RAG 매니저 초기화 (지연 로딩 비활성화)
        from src.prompt_loader import get_rag_manager
        rag_manager = get_rag_manager(lazy_load=False)
        
        if rag_manager:
            logger.info("✅ RAG 매니저 초기화 완료")
            
            # 문서 폴더 자동 인덱싱 시도
            documents_folder = config.get('documents_folder', 'documents')
            
            # 상대 경로를 절대 경로로 변환
            if not os.path.isabs(documents_folder):
                # backend 폴더에서 프로젝트 루트로 이동
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                documents_folder = os.path.abspath(os.path.join(project_root, documents_folder))
            
            if os.path.exists(documents_folder):
                logger.info(f"📚 문서 폴더 발견: {documents_folder}")
                logger.info("📊 백그라운드에서 문서 인덱싱 시작...")
                
                # 백그라운드에서 인덱싱 실행 (서버 시작을 차단하지 않음)
                asyncio.create_task(auto_index_documents())
            else:
                logger.info(f"📁 문서 폴더가 없습니다: {documents_folder}")
                logger.info("💡 문서를 추가하면 자동으로 인덱싱됩니다.")
        else:
            logger.error("❌ RAG 매니저 초기화 실패")
            
    except Exception as e:
        logger.exception(f"⚠️ RAG 시스템 자동 초기화 중 치명적인 오류 발생")
        logger.info("💡 수동으로 /api/rag/index 엔드포인트를 사용하여 초기화할 수 있습니다.")

async def auto_index_documents():
    """백그라운드에서 문서 자동 인덱싱"""
    try:
        from src.prompt_loader import index_documents_folder
        result = index_documents_folder(force_reindex=False)
        
        if result.get('status') == 'success':
            indexed_count = result.get('indexed_documents', 0)
            total_chunks = result.get('total_chunks', 0)
            logger.info(f"📊 문서 인덱싱 완료: {indexed_count}개 문서, {total_chunks}개 청크")
        else:
            message = result.get('message', '알 수 없는 오류')
            logger.error(f"❌ 문서 인덱싱 실패: {message}")
            
    except Exception as e:
        logger.exception(f"⚠️ 백그라운드 문서 인덱싱 중 오류 발생")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 애플리케이션 라이프사이클 매니저"""
    # 시작 시 실행
    logger.info("🚀 애플리케이션 시작...")
    await startup_rag_system()
    yield
    # 종료 시 실행
    logger.info("🛑 애플리케이션 종료.")

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
