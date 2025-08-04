"""
파일 처리 관련 API 라우터
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
import os
import sys
import tempfile
import shutil
import logging
from typing import List

# 기존 모듈 import
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.excel_writer import save_results_to_excel
from backend.models.files import (
    RepoPathValidationRequest, 
    RepoPathValidationResponse,
    FileListResponse,
    FileInfo,
    FileUploadResponse,
    FileDeleteResponse
)

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """파일 업로드 API (향후 확장용)"""
    
    logger.info(f"파일 업로드 요청: filename={file.filename}, size={file.size}")
    
    try:
        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_path = temp_file.name
        
        file_size = os.path.getsize(temp_path)
        logger.info(f"파일 업로드 성공: filename={file.filename}, temp_path={temp_path}, size={file_size}")
        
        return FileUploadResponse(
            message="파일이 성공적으로 업로드되었습니다.",
            filename=file.filename,
            temp_path=temp_path,
            size=file_size
        )
        
    except Exception as e:
        logger.error(f"파일 업로드 실패: filename={file.filename}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"파일 업로드 중 오류가 발생했습니다: {str(e)}")

@router.get("/download/excel/{filename:path}")
async def download_excel_file(filename: str):
    """Excel 파일 다운로드 API"""
    
    logger.info(f"Excel 파일 다운로드 요청: filename={filename}")
    
    try:
        import urllib.parse
        
        # outputs 폴더에서 파일 찾기
        outputs_dir = os.path.join(os.path.dirname(__file__), '../../outputs')
        
        # URL 디코딩 처리
        decoded_filename = urllib.parse.unquote(filename)
        
        # 파일명 정규화 (outputs/ 접두사 제거)
        if decoded_filename.startswith('outputs/'):
            clean_filename = decoded_filename.replace('outputs/', '', 1)
        else:
            clean_filename = decoded_filename
        
        # 파일 경로 생성
        file_path = os.path.join(outputs_dir, clean_filename)
        
        # 파일 존재 확인
        if not os.path.exists(file_path):
            logger.warning(f"Excel 파일을 찾을 수 없음: {clean_filename}")
            raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {clean_filename}")
        
        # 파일이 실제 Excel 파일인지 확인
        if not clean_filename.endswith('.xlsx'):
            logger.warning(f"Excel 파일이 아님: {clean_filename}")
            raise HTTPException(status_code=400, detail="Excel 파일이 아닙니다.")
        
        # UTF-8 파일명 인코딩 처리
        filename_utf8 = urllib.parse.quote(os.path.basename(file_path), safe='')
        
        file_size = os.path.getsize(file_path)
        logger.info(f"Excel 파일 다운로드 성공: filename={clean_filename}, size={file_size}")
        
        return FileResponse(
            path=file_path,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            filename=os.path.basename(file_path),
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{filename_utf8}",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Excel 파일 다운로드 실패: filename={filename}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"파일 다운로드 중 오류가 발생했습니다: {str(e)}")

@router.get("/list/outputs", response_model=FileListResponse)
async def list_output_files():
    """출력 파일 목록 조회 API"""
    
    logger.info("출력 파일 목록 조회 요청")
    
    try:
        outputs_dir = os.path.join(os.path.dirname(__file__), '../../outputs')
        
        if not os.path.exists(outputs_dir):
            logger.info("outputs 디렉토리가 존재하지 않음")
            return FileListResponse(files=[])
        
        files = []
        for filename in os.listdir(outputs_dir):
            if filename.endswith('.xlsx'):
                file_path = os.path.join(outputs_dir, filename)
                file_stat = os.stat(file_path)
                
                files.append(FileInfo(
                    filename=filename,
                    size=file_stat.st_size,
                    created_at=file_stat.st_ctime,
                    modified_at=file_stat.st_mtime
                ))
        
        # 수정 시간 기준으로 내림차순 정렬
        files.sort(key=lambda x: x.modified_at, reverse=True)
        
        logger.info(f"출력 파일 목록 조회 성공: 파일 수={len(files)}")
        return FileListResponse(files=files)
        
    except Exception as e:
        logger.error(f"출력 파일 목록 조회 실패: error={str(e)}")
        raise HTTPException(status_code=500, detail=f"파일 목록 조회 중 오류가 발생했습니다: {str(e)}")

@router.delete("/outputs/{filename}", response_model=FileDeleteResponse)
async def delete_output_file(filename: str):
    """출력 파일 삭제 API"""
    
    logger.info(f"출력 파일 삭제 요청: filename={filename}")
    
    try:
        outputs_dir = os.path.join(os.path.dirname(__file__), '../../outputs')
        file_path = os.path.join(outputs_dir, filename)
        
        if not os.path.exists(file_path):
            logger.warning(f"삭제할 파일을 찾을 수 없음: {filename}")
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
        
        file_size = os.path.getsize(file_path)
        os.remove(file_path)
        
        logger.info(f"출력 파일 삭제 성공: filename={filename}, size={file_size}")
        
        return FileDeleteResponse(
            message=f"파일 '{filename}'이 성공적으로 삭제되었습니다."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"출력 파일 삭제 실패: filename={filename}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"파일 삭제 중 오류가 발생했습니다: {str(e)}")

@router.post("/validate/repo-path", response_model=RepoPathValidationResponse)
async def validate_repo_path(request: RepoPathValidationRequest):
    """Git 저장소 경로 유효성 검사 API"""
    
    logger.info(f"Git 저장소 경로 유효성 검사 요청: repo_path={request.repo_path}")
    
    try:
        repo_path = request.repo_path
        
        if not repo_path:
            logger.warning("경로가 입력되지 않음")
            return RepoPathValidationResponse(
                valid=False, 
                message="경로가 입력되지 않았습니다."
            )
        
        if not os.path.exists(repo_path):
            logger.warning(f"경로가 존재하지 않음: {repo_path}")
            return RepoPathValidationResponse(
                valid=False, 
                message="경로가 존재하지 않습니다."
            )
        
        if not os.path.isdir(repo_path):
            logger.warning(f"디렉토리가 아님: {repo_path}")
            return RepoPathValidationResponse(
                valid=False, 
                message="디렉토리가 아닙니다."
            )
        
        # .git 폴더 확인
        git_dir = os.path.join(repo_path, '.git')
        if not os.path.exists(git_dir):
            logger.warning(f"Git 저장소가 아님: {repo_path}")
            return RepoPathValidationResponse(
                valid=False, 
                message="Git 저장소가 아닙니다."
            )
        
        logger.info(f"Git 저장소 경로 유효성 검사 성공: {repo_path}")
        return RepoPathValidationResponse(
            valid=True, 
            message="유효한 Git 저장소입니다."
        )
        
    except Exception as e:
        logger.error(f"Git 저장소 경로 유효성 검사 실패: repo_path={request.repo_path}, error={str(e)}")
        return RepoPathValidationResponse(
            valid=False, 
            message=f"경로 검사 중 오류가 발생했습니다: {str(e)}"
        )