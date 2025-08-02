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
from contextlib import asynccontextmanager

# 기존 src 모듈 import를 위한 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.routers import scenario, feedback, rag, files

async def startup_rag_system():
    """백엔드 시작 시 RAG 시스템 자동 초기화"""
    try:
        print("🚀 RAG 시스템 자동 초기화 시작...")
        
        # 설정 로드 및 RAG 활성화 확인
        from src.config_loader import load_config
        config = load_config()
        
        if not config or not config.get('rag', {}).get('enabled', False):
            print("❌ RAG가 설정에서 비활성화되어 있습니다.")
            return
            
        print("✅ RAG 설정 확인 완료")
        
        # RAG 매니저 초기화 (지연 로딩 비활성화)
        from src.prompt_loader import get_rag_manager, index_documents_folder
        rag_manager = get_rag_manager(lazy_load=False)
        
        if rag_manager:
            print("✅ RAG 매니저 초기화 완료")
            
            # 문서 폴더 자동 인덱싱 시도
            documents_folder = config.get('documents_folder', 'documents')
            if os.path.exists(documents_folder):
                print(f"📚 문서 폴더 발견: {documents_folder}")
                print("📊 백그라운드에서 문서 인덱싱 시작...")
                
                # 백그라운드에서 인덱싱 실행 (서버 시작을 차단하지 않음)
                asyncio.create_task(auto_index_documents())
            else:
                print(f"📁 문서 폴더가 없습니다: {documents_folder}")
                print("💡 문서를 추가하면 자동으로 인덱싱됩니다.")
        else:
            print("❌ RAG 매니저 초기화 실패")
            
    except Exception as e:
        print(f"⚠️ RAG 시스템 자동 초기화 중 오류: {e}")
        print("💡 수동으로 /api/rag/index 엔드포인트를 사용하여 초기화할 수 있습니다.")

async def auto_index_documents():
    """백그라운드에서 문서 자동 인덱싱"""
    try:
        from src.prompt_loader import index_documents_folder
        result = index_documents_folder(force_reindex=False)
        
        if result.get('status') == 'success':
            indexed_count = result.get('indexed_documents', 0)
            total_chunks = result.get('total_chunks', 0)
            print(f"📊 문서 인덱싱 완료: {indexed_count}개 문서, {total_chunks}개 청크")
        else:
            message = result.get('message', '알 수 없는 오류')
            print(f"❌ 문서 인덱싱 실패: {message}")
            
    except Exception as e:
        print(f"⚠️ 백그라운드 문서 인덱싱 중 오류: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 애플리케이션 라이프사이클 매니저"""
    # 시작 시 실행
    await startup_rag_system()
    yield
    # 종료 시 실행 (필요 시 정리 작업)

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
app.include_router(scenario.router, prefix="/api/scenario", tags=["scenario"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["feedback"])
app.include_router(rag.router, prefix="/api/rag", tags=["rag"])
app.include_router(files.router, prefix="/api/files", tags=["files"])

# 정적 파일 서빙 (프로덕션용)
if os.path.exists("frontend/dist"):
    app.mount("/static", StaticFiles(directory="frontend/dist"), name="static")

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "TestscenarioMaker API v2.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )