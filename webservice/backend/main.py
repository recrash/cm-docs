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

# 로깅 설정 완료
logger.info("메인 애플리케이션 로딩 완료")

async def startup_rag_system():
    """백엔드 시작 시 RAG 시스템 자동 초기화"""
    logger.info("RAG 시스템 자동 초기화 시작...")
    
    try:
        from src.config_loader import load_config
        
        # 설정 파일 로드
        config = load_config()
        
        if not config:
            logger.warning("RAG가 설정에서 비활성화되어 있습니다.")
            return
        
        rag_enabled = config.get('rag', {}).get('enabled', False)
        if not rag_enabled:
            logger.warning("RAG가 설정에서 비활성화되어 있습니다.")
            return
        
        logger.info("RAG 설정 확인 완료")
        
        # RAG 매니저 초기화 (지연 로딩 비활성화)
        from src.prompt_loader import get_rag_manager
        rag_manager = get_rag_manager(lazy_load=False)
        
        if rag_manager:
            logger.info("RAG 매니저 초기화 완료")
            
            # 통합된 데이터 디렉토리 기반 documents 폴더 설정
            from src.config_loader import get_data_directory_path
            data_root = get_data_directory_path()
            documents_folder = os.path.join(data_root, 'documents')
            
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
    logger.info("=== 백그라운드 문서 인덱싱 시작 ===")
    try:
        logger.info("STEP 1: prompt_loader 모듈 import 시도")
        from src.prompt_loader import index_documents_folder
        logger.info("STEP 2: prompt_loader 모듈 import 성공")
        
        logger.info("STEP 3: 간단한 테스트 함수 호출")
        
        # 직접 함수 호출 테스트
        def test_function():
            print("[TEST] 테스트 함수 실행됨!")
            return {"status": "test_success", "message": "테스트 완료"}
        
        logger.info("STEP 3.1: 테스트 함수 실행 시작")
        test_result = test_function()
        logger.info(f"STEP 3.2: 테스트 함수 결과: {test_result}")
        
        logger.info("STEP 3.3: index_documents_folder 함수 호출 시작")
        
        # 타임아웃을 적용하여 안전하게 실행
        try:
            import time
            start_time = time.time()
            
            result = await asyncio.get_event_loop().run_in_executor(
                None, index_documents_folder, False
            )
            
            elapsed_time = time.time() - start_time
            logger.info(f"STEP 4: index_documents_folder 함수 호출 완료 ({elapsed_time:.1f}초 소요) - 결과: {result}")
            
            if result.get('status') == 'success':
                indexed_count = result.get('indexed_documents', 0)
                total_chunks = result.get('total_chunks', 0)
                logger.info(f"문서 인덱싱 완료: {indexed_count}개 문서, {total_chunks}개 청크")
            else:
                message = result.get('message', '알 수 없는 오류')
                logger.error(f"문서 인덱싱 실패: {message}")
                
        except asyncio.TimeoutError:
            logger.error("백그라운드 인덱싱 타임아웃")
            logger.info("타임아웃되었지만 애플리케이션은 계속 실행됩니다")
            
    except ImportError as ie:
        logger.error(f"백그라운드 인덱싱 모듈 임포트 오류: {str(ie)}")
        logger.info("임포트 오류가 발생했지만 애플리케이션은 계속 실행됩니다")
    except Exception as e:
        logger.error(f"백그라운드 문서 인덱싱 중 예상치 못한 오류 발생: {str(e)}")
        logger.exception("백그라운드 인덱싱 예외 상세:")
        logger.info("인덱싱 오류가 발생했지만 애플리케이션은 계속 실행됩니다")
    finally:
        logger.info("=== 백그라운드 문서 인덱싱 종료 ===")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 애플리케이션 라이프사이클 매니저"""
    # 시작 시 실행
    try:
        logger.info("=== LIFESPAN MANAGER START ===")
        logger.info("애플리케이션 시작...")
        logger.info("startup_rag_system 호출 시작")
        try:
            await startup_rag_system()
            logger.info("startup_rag_system 호출 완료")
        except ImportError as ie:
            logger.error(f"startup_rag_system 임포트 오류: {str(ie)}")
            logger.exception("임포트 오류 상세:")
        except Exception as e:
            logger.error(f"startup_rag_system 호출 중 일반 예외 발생: {str(e)}")
            logger.exception("라이프사이클 매니저 예외 상세:")
        logger.info("=== LIFESPAN MANAGER START COMPLETE ===")
        logger.info("=== FastAPI 애플리케이션 시작 완료 ===")
    except Exception as fatal_error:
        logger.error(f"라이프사이클 매니저 치명적 오류: {str(fatal_error)}")
        logger.exception("치명적 오류 상세:")
        logger.info("=== LIFESPAN MANAGER FAILED ===")
        # 에러가 발생해도 앱은 시작되도록 함
        logger.info("=== FastAPI 애플리케이션 시작 완료 (오류 있음) ===")
    
    yield
    
    # 종료 시 실행
    try:
        logger.info("=== LIFESPAN MANAGER SHUTDOWN ===")
        logger.info("애플리케이션 종료.")
    except Exception as shutdown_error:
        logger.error(f"라이프사이클 매니저 종료 중 오류: {str(shutdown_error)}")

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
