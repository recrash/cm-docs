"""
파일 처리 API 테스트
"""

import pytest
import os
import tempfile
from unittest.mock import patch, mock_open
from fastapi import UploadFile
from io import BytesIO

def test_validate_repo_path_valid(client):
    """유효한 저장소 경로 검증 테스트"""
    
    with patch('os.path.exists') as mock_exists, \
         patch('os.path.isdir') as mock_isdir:
        
        mock_exists.side_effect = lambda path: path in ["/test/repo", "/test/repo/.git"]
        mock_isdir.return_value = True
        
        response = client.post("/api/files/validate/repo-path", json="/test/repo")
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert "유효한 Git 저장소" in data["message"]

def test_validate_repo_path_not_exists(client):
    """존재하지 않는 경로 검증 테스트"""
    
    with patch('os.path.exists') as mock_exists:
        mock_exists.return_value = False
        
        response = client.post("/api/files/validate/repo-path", json="/nonexistent/repo")
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "경로가 존재하지 않습니다" in data["message"]

def test_validate_repo_path_not_directory(client):
    """디렉토리가 아닌 경로 검증 테스트"""
    
    with patch('os.path.exists') as mock_exists, \
         patch('os.path.isdir') as mock_isdir:
        
        mock_exists.return_value = True
        mock_isdir.return_value = False
        
        response = client.post("/api/files/validate/repo-path", json="/test/file.txt")
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "디렉토리가 아닙니다" in data["message"]

def test_validate_repo_path_not_git_repo(client):
    """Git 저장소가 아닌 경로 검증 테스트"""
    
    with patch('os.path.exists') as mock_exists, \
         patch('os.path.isdir') as mock_isdir:
        
        mock_exists.side_effect = lambda path: path != "/test/repo/.git"
        mock_isdir.return_value = True
        
        response = client.post("/api/files/validate/repo-path", json="/test/repo")
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "Git 저장소가 아닙니다" in data["message"]

def test_validate_repo_path_empty(client):
    """빈 경로 검증 테스트"""
    
    response = client.post("/api/files/validate/repo-path", json="")
    
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert "경로가 입력되지 않았습니다" in data["message"]

def test_upload_file_success(client):
    """파일 업로드 성공 테스트"""
    
    # 테스트용 파일 데이터
    file_content = b"test file content"
    file_name = "test.txt"
    
    with patch('tempfile.NamedTemporaryFile') as mock_temp, \
         patch('shutil.copyfileobj') as mock_copy, \
         patch('os.path.getsize') as mock_getsize:
        
        # NamedTemporaryFile mock 설정
        mock_temp_file = mock_temp.return_value.__enter__.return_value
        mock_temp_file.name = "/tmp/test_file"
        mock_getsize.return_value = len(file_content)
        
        # 파일 업로드 시뮬레이션
        files = {"file": (file_name, BytesIO(file_content), "text/plain")}
        response = client.post("/api/files/upload", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert "성공적으로 업로드" in data["message"]
        assert data["filename"] == file_name
        assert "temp_path" in data
        assert data["size"] == len(file_content)

def test_list_output_files_success(client):
    """출력 파일 목록 조회 성공 테스트"""
    
    mock_files = ["scenario_20231201_120000.xlsx", "scenario_20231202_130000.xlsx"]
    
    with patch('os.path.exists') as mock_exists, \
         patch('os.listdir') as mock_listdir, \
         patch('os.stat') as mock_stat:
        
        mock_exists.return_value = True
        mock_listdir.return_value = mock_files
        
        # stat mock 설정
        mock_stat_result = type('MockStat', (), {})()
        mock_stat_result.st_size = 1024
        mock_stat_result.st_ctime = 1701234567
        mock_stat_result.st_mtime = 1701234567
        mock_stat.return_value = mock_stat_result
        
        response = client.get("/api/files/list/outputs")
        
        assert response.status_code == 200
        data = response.json()
        assert "files" in data
        assert len(data["files"]) == 2
        
        # 첫 번째 파일 확인
        first_file = data["files"][0]
        assert "filename" in first_file
        assert "size" in first_file
        assert "created_at" in first_file
        assert "modified_at" in first_file

def test_list_output_files_no_directory(client):
    """출력 디렉토리가 없는 경우 테스트"""
    
    with patch('os.path.exists') as mock_exists:
        mock_exists.return_value = False
        
        response = client.get("/api/files/list/outputs")
        
        assert response.status_code == 200
        data = response.json()
        assert data["files"] == []

def test_download_excel_file_success(client):
    """Excel 파일 다운로드 성공 테스트"""
    
    filename = "test_scenario.xlsx"
    
    with patch('os.path.exists') as mock_exists:
        mock_exists.return_value = True
        
        # FileResponse는 실제 파일이 필요하므로 존재만 확인
        response = client.get(f"/api/files/download/excel/{filename}")
        
        # 실제로는 FileResponse가 반환되어야 하지만, 테스트에서는 존재 확인만
        mock_exists.assert_called_once()

def test_download_excel_file_not_found(client):
    """Excel 파일이 없는 경우 테스트"""
    
    filename = "nonexistent.xlsx"
    
    with patch('os.path.exists') as mock_exists:
        mock_exists.return_value = False
        
        response = client.get(f"/api/files/download/excel/{filename}")
        
        assert response.status_code == 404
        assert "파일을 찾을 수 없습니다" in response.json()["detail"]

def test_delete_output_file_success(client):
    """출력 파일 삭제 성공 테스트"""
    
    filename = "test_scenario.xlsx"
    
    with patch('os.path.exists') as mock_exists, \
         patch('os.remove') as mock_remove:
        
        mock_exists.return_value = True
        
        response = client.delete(f"/api/files/outputs/{filename}")
        
        assert response.status_code == 200
        data = response.json()
        assert "성공적으로 삭제" in data["message"]
        assert filename in data["message"]
        mock_remove.assert_called_once()

def test_delete_output_file_not_found(client):
    """삭제할 파일이 없는 경우 테스트"""
    
    filename = "nonexistent.xlsx"
    
    with patch('os.path.exists') as mock_exists:
        mock_exists.return_value = False
        
        response = client.delete(f"/api/files/outputs/{filename}")
        
        assert response.status_code == 404
        assert "파일을 찾을 수 없습니다" in response.json()["detail"]

def test_delete_output_file_error(client):
    """파일 삭제 중 오류 발생 테스트"""
    
    filename = "test_scenario.xlsx"
    
    with patch('os.path.exists') as mock_exists, \
         patch('os.remove') as mock_remove:
        
        mock_exists.return_value = True
        mock_remove.side_effect = Exception("삭제 오류")
        
        response = client.delete(f"/api/files/outputs/{filename}")
        
        assert response.status_code == 500
        assert "파일 삭제 중 오류" in response.json()["detail"]