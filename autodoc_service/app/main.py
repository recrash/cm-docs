"""
AutoDoc Service FastAPI 애플리케이션

Office-less 환경에서 동작하는 문서 자동화 서비스
템플릿 기반 Word/Excel 문서 생성 API
"""
import json
from pathlib import Path
from typing import List, Union, Dict, Any

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from .models import (
    ChangeRequest, 
    ParseHtmlResponse, 
    CreateDocumentResponse, 
    HealthResponse
)
from .parsers.itsupp_html_parser import parse_itsupp_html
from .services.label_based_word_builder import build_change_request_doc_label_based
from .services.excel_test_builder import build_test_scenario_xlsx
from .services.excel_list_builder import build_change_list_xlsx
from .services.paths import (
    get_templates_dir, 
    get_documents_dir, 
    verify_documents_writable,
    verify_template_exists
)

# FastAPI 앱 초기화
app = FastAPI(
    title="AutoDoc Service",
    description="Office-less 문서 자동화 서비스",
    version="1.0.0"
)

# CORS 설정 (개발 환경용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 운영환경에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=Dict[str, str])
async def root():
    """루트 엔드포인트"""
    return {"message": "AutoDoc Service API", "version": "1.0.0"}


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """헬스 체크 엔드포인트"""
    try:
        # 템플릿 파일 존재 여부 확인
        templates_available = True
        template_files = ["template.docx", "template.xlsx", "template_list.xlsx"]
        
        for template in template_files:
            try:
                verify_template_exists(template)
            except FileNotFoundError:
                templates_available = False
                break
        
        # 문서 디렉터리 쓰기 권한 확인
        documents_writable = verify_documents_writable()
        
        status = "ok" if templates_available and documents_writable else "warning"
        
        return HealthResponse(
            status=status,
            templates_available=templates_available,
            documents_dir_writable=documents_writable
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"헬스 체크 실패: {str(e)}")


@app.post("/parse-html", response_model=ParseHtmlResponse)
async def parse_html_endpoint(file: UploadFile = File(...)):
    """HTML 파일 파싱 엔드포인트
    
    업로드된 HTML 파일을 파싱하여 JSON 형태로 반환
    """
    try:
        # 파일 타입 검증
        if not file.content_type or 'html' not in file.content_type.lower():
            if not file.filename or not file.filename.lower().endswith('.html'):
                raise HTTPException(
                    status_code=400, 
                    detail="HTML 파일만 업로드 가능합니다"
                )
        
        # 파일 내용 읽기
        content = await file.read()
        html_content = content.decode('utf-8')
        
        # HTML 파싱
        parsed_data = parse_itsupp_html(html_content)
        
        return ParseHtmlResponse(
            success=True,
            data=parsed_data
        )
        
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="파일 인코딩 오류: UTF-8로 인코딩된 HTML 파일이 필요합니다"
        )
    except Exception as e:
        return ParseHtmlResponse(
            success=False,
            error=f"HTML 파싱 실패: {str(e)}"
        )


@app.post("/create-cm-word-enhanced", response_model=CreateDocumentResponse)
async def create_change_management_word_enhanced(request: dict):
    """
    향상된 변경관리 Word 문서 생성 엔드포인트
    
    Raw 파싱 데이터를 받아서 누락 필드를 자동으로 보완하여 Word 문서를 생성합니다.
    """
    try:
        # 요청에서 raw_data와 ChangeRequest 데이터 분리
        raw_data = request.get("raw_data", {})
        change_request_data = request.get("change_request", {})
        
        # ChangeRequest 객체 생성
        data = ChangeRequest(**change_request_data)
        
        # raw_data를 함께 전달하여 라벨-기반 Word 문서 생성
        output_path = build_change_request_doc_label_based(data, raw_data=raw_data)
        
        return CreateDocumentResponse(
            ok=True,
            filename=output_path.name
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        return CreateDocumentResponse(
            ok=False,
            error=f"향상된 Word 문서 생성 실패: {str(e)}"
        )


@app.post("/create-test-excel", response_model=CreateDocumentResponse)
async def create_test_scenario_excel(data: ChangeRequest):
    """테스트 시나리오 Excel 파일 생성 엔드포인트"""
    try:
        # Excel 파일 생성
        output_path = build_test_scenario_xlsx(data)
        
        return CreateDocumentResponse(
            ok=True,
            filename=output_path.name
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        return CreateDocumentResponse(
            ok=False,
            error=f"Excel 테스트 시나리오 생성 실패: {str(e)}"
        )


@app.post("/create-cm-list", response_model=CreateDocumentResponse)
async def create_change_management_list(data: List[Union[ChangeRequest, Dict[str, Any]]]):
    """변경관리 문서 목록 Excel 파일 생성 엔드포인트"""
    try:
        if not data:
            raise HTTPException(status_code=400, detail="데이터가 비어있습니다")
        
        # Excel 목록 파일 생성
        output_path = build_change_list_xlsx(data)
        
        return CreateDocumentResponse(
            ok=True,
            filename=output_path.name
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        return CreateDocumentResponse(
            ok=False,
            error=f"Excel 목록 생성 실패: {str(e)}"
        )


@app.get("/download/{filename}")
async def download_file(filename: str):
    """파일 다운로드 엔드포인트
    
    documents/ 디렉터리의 파일을 스트리밍으로 제공
    """
    try:
        # 파일 경로 생성
        documents_dir = get_documents_dir()
        file_path = documents_dir / filename
        
        # 파일 존재 여부 확인
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다")
        
        # 파일이 documents 디렉터리 내부에 있는지 확인 (보안)
        try:
            file_path.resolve().relative_to(documents_dir.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="접근 권한이 없습니다")
        
        # MIME 타입 결정
        content_type = "application/octet-stream"
        if filename.lower().endswith('.docx'):
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif filename.lower().endswith('.xlsx'):
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        return FileResponse(
            path=str(file_path),
            media_type=content_type,
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 다운로드 실패: {str(e)}")


@app.get("/templates")
async def list_templates():
    """사용 가능한 템플릿 목록 반환"""
    try:
        templates_dir = get_templates_dir()
        templates = []
        
        for template_file in templates_dir.glob("*.docx"):
            templates.append({
                "name": template_file.name,
                "type": "word",
                "exists": template_file.exists()
            })
        
        for template_file in templates_dir.glob("*.xlsx"):
            templates.append({
                "name": template_file.name,
                "type": "excel", 
                "exists": template_file.exists()
            })
        
        return {"templates": templates}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"템플릿 목록 조회 실패: {str(e)}")


@app.get("/documents")
async def list_documents():
    """생성된 문서 목록 반환"""
    try:
        documents_dir = get_documents_dir()
        documents = []
        
        for doc_file in documents_dir.glob("*"):
            if doc_file.is_file():
                documents.append({
                    "name": doc_file.name,
                    "size": doc_file.stat().st_size,
                    "modified": doc_file.stat().st_mtime
                })
        
        # 수정일 기준 역순 정렬
        documents.sort(key=lambda x: x['modified'], reverse=True)
        
        return {"documents": documents}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"문서 목록 조회 실패: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)