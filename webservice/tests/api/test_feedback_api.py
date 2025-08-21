"""
피드백 API 테스트
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime

def test_get_feedback_stats(client, mock_dependencies):
    """피드백 통계 조회 테스트"""
    
    # Mock 통계 데이터 설정
    mock_stats = {
        "total_feedback": 10,
        "category_distribution": {"good": 7, "bad": 3},
        "average_scores": {"overall": 4.2, "usefulness": 4.0}
    }
    
    with patch('backend.routers.feedback.feedback_manager') as mock_manager:
        mock_manager.get_feedback_stats.return_value = mock_stats
        
        response = client.get("/api/feedback/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_feedback"] == 10
        assert "category_distribution" in data
        assert "average_scores" in data

def test_submit_feedback_success(client, mock_dependencies):
    """피드백 제출 성공 테스트"""
    
    with patch('backend.routers.feedback.feedback_manager') as mock_manager:
        mock_manager.save_feedback.return_value = True
        
        request_data = {
            "feedback_type": "like",
            "comments": "좋은 시나리오입니다",
            "testcase_feedback": [
                {
                    "testcase_id": "TC001",
                    "score": 5,
                    "comments": "완벽합니다"
                }
            ],
            "repo_path": "/test/repo",
            "git_analysis": "mock analysis",
            "scenario_content": {"test": "data"}
        }
        
        response = client.post("/api/feedback/submit", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "성공적으로 제출" in data["message"]

def test_submit_feedback_failure(client, mock_dependencies):
    """피드백 제출 실패 테스트"""
    
    with patch('backend.routers.feedback.feedback_manager') as mock_manager:
        mock_manager.save_feedback.return_value = False
        
        request_data = {
            "feedback_type": "dislike",
            "comments": "개선이 필요합니다",
            "testcase_feedback": [],
            "repo_path": "/test/repo",
            "git_analysis": "mock analysis",
            "scenario_content": {"test": "data"}
        }
        
        response = client.post("/api/feedback/submit", json=request_data)
        
        assert response.status_code == 500
        assert "피드백 저장 중 오류" in response.json()["detail"]

def test_get_feedback_examples(client):
    """피드백 예시 조회 테스트"""
    
    mock_examples = [
        {
            "overall_score": 5,
            "comments": "매우 좋습니다",
            "scenario_content": {"test": "data"},
            "timestamp": "2023-01-01"
        }
    ]
    
    with patch('backend.routers.feedback.feedback_manager') as mock_manager:
        mock_manager.get_feedback_examples.return_value = mock_examples
        
        response = client.get("/api/feedback/examples/good?limit=5")
        
        assert response.status_code == 200
        data = response.json()
        assert "examples" in data
        assert len(data["examples"]) == 1

def test_get_improvement_insights(client):
    """개선 인사이트 조회 테스트"""
    
    mock_insights = {
        "problem_areas": {"accuracy": 0.2, "completeness": 0.1},
        "negative_feedback_count": 3,
        "sample_negative_comments": ["부정확합니다", "불완전합니다"]
    }
    
    with patch('backend.routers.feedback.feedback_manager') as mock_manager:
        mock_manager.get_improvement_insights.return_value = mock_insights
        
        response = client.get("/api/feedback/insights")
        
        assert response.status_code == 200
        data = response.json()
        assert "problem_areas" in data
        assert "negative_feedback_count" in data

def test_get_prompt_enhancement_info(client):
    """프롬프트 개선 정보 조회 테스트"""
    
    mock_summary = {
        "feedback_count": 5,
        "improvement_areas": ["accuracy"],
        "good_examples_available": 3,
        "bad_examples_available": 2
    }
    
    with patch('backend.routers.feedback.get_prompt_enhancer') as mock_enhancer:
        mock_instance = MagicMock()
        mock_instance.get_enhancement_summary.return_value = mock_summary
        mock_enhancer.return_value = mock_instance
        
        response = client.get("/api/feedback/prompt-enhancement")
        
        assert response.status_code == 200
        data = response.json()
        assert "enhancement_summary" in data
        assert "feedback_count" in data
        assert data["feedback_count"] == 5  # 실제 응답에 포함되는 필드 검증

def test_get_enhancement_preview_available(client):
    """프롬프트 개선 지침 미리보기 (사용 가능) 테스트"""
    
    mock_summary = {"feedback_count": 5}
    
    with patch('backend.routers.feedback.get_prompt_enhancer') as mock_enhancer:
        mock_instance = MagicMock()
        mock_instance.get_enhancement_summary.return_value = mock_summary
        mock_instance.get_enhanced_prompt_preview.return_value = "개선된 프롬프트 미리보기"
        mock_enhancer.return_value = mock_instance
        
        response = client.get("/api/feedback/prompt-enhancement/preview")
        
        assert response.status_code == 200
        data = response.json()
        assert "preview" in data
        assert data["preview"] == "개선된 프롬프트 미리보기"

def test_get_enhancement_preview_not_available(client):
    """프롬프트 개선 지침 미리보기 (사용 불가) 테스트"""
    
    mock_summary = {"feedback_count": 1}
    
    with patch('backend.routers.feedback.get_prompt_enhancer') as mock_enhancer:
        mock_instance = MagicMock()
        mock_instance.get_enhancement_summary.return_value = mock_summary
        mock_instance.get_enhanced_prompt_preview.return_value = "기본 프롬프트"
        mock_enhancer.return_value = mock_instance
        
        response = client.get("/api/feedback/prompt-enhancement/preview")
        
        assert response.status_code == 200
        data = response.json()
        assert "preview" in data
        assert data["preview"] == "기본 프롬프트"

def test_export_feedback_data(client):
    """피드백 데이터 내보내기 테스트"""
    
    # scenario_feedback 테이블 컬럼에 맞는 Mock 데이터 생성
    mock_results = [
        (1, 'test_scenario', '2024-01-01 10:00:00', 'hash123', '/test/repo', '{"test": "data"}', 4.5, 4, 4, 5, 'positive', 'Good test', '2024-01-01 10:00:00', 'TC001:4:Good test|TC002:3:')
    ]
    
    with patch('sqlite3.connect') as mock_connect, \
         patch('pathlib.Path.mkdir') as mock_mkdir, \
         patch('builtins.open', mock_open()) as mock_file:
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = mock_results
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.__exit__.return_value = None
        mock_connect.return_value = mock_conn
        
        response = client.get("/api/feedback/export")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "filename" in data
        assert "total_records" in data

def test_get_feedback_count_by_category(client):
    """카테고리별 피드백 개수 조회 테스트"""
    
    mock_counts = {"good": 5, "bad": 3, "neutral": 2}
    
    with patch('backend.routers.feedback.feedback_manager') as mock_manager:
        mock_manager.get_feedback_count_by_category.return_value = mock_counts
        
        response = client.get("/api/feedback/count-by-category")
        
        assert response.status_code == 200
        data = response.json()
        assert "good" in data
        assert "bad" in data
        assert "neutral" in data
        assert data["good"] == 5
        assert data["bad"] == 3
        assert data["neutral"] == 2

def test_reset_all_feedback(client):
    """전체 피드백 초기화 테스트"""
    
    with patch('backend.routers.feedback.feedback_manager') as mock_manager:
        
        mock_manager.reset_all_feedback.return_value = True
        
        response = client.delete("/api/feedback/reset/all?create_backup=true")
        
        assert response.status_code == 200
        data = response.json()
        assert "성공적으로 초기화" in data["message"]
        assert data["success"] is True

def test_reset_feedback_by_category(client):
    """카테고리별 피드백 초기화 테스트"""
    
    with patch('backend.routers.feedback.feedback_manager') as mock_manager:
        
        mock_manager.reset_feedback_by_category.return_value = True
        
        response = client.delete("/api/feedback/reset/category/good?create_backup=true")
        
        assert response.status_code == 200
        data = response.json()
        assert "성공적으로 초기화" in data["message"]
        assert data["success"] is True

# 새로운 API들에 대한 테스트

def test_list_backup_files_success(client):
    """백업 파일 목록 조회 성공 테스트"""
    
    # Mock 백업 파일 목록
    mock_files = [
        {
            "filename": "feedback_backup_20240101_120000.json",
            "size": 1024,
            "created_at": "2024-01-01T12:00:00",
            "modified_at": "2024-01-01T12:00:00"
        },
        {
            "filename": "feedback_backup_20240102_130000.json", 
            "size": 2048,
            "created_at": "2024-01-02T13:00:00",
            "modified_at": "2024-01-02T13:00:00"
        }
    ]
    
    with patch('backend.routers.feedback.PathlibPath') as mock_path:
        # 백업 디렉토리 존재 설정
        mock_backup_dir = MagicMock()
        mock_backup_dir.exists.return_value = True
        mock_path.return_value = mock_backup_dir
        
        # 백업 파일들 설정
        mock_files_list = []
        for file_info in mock_files:
            mock_file = MagicMock()
            mock_file.name = file_info["filename"]
            mock_stat = MagicMock()
            mock_stat.st_size = file_info["size"]
            mock_stat.st_ctime = datetime.fromisoformat(file_info["created_at"]).timestamp()
            mock_stat.st_mtime = datetime.fromisoformat(file_info["modified_at"]).timestamp()
            mock_file.stat.return_value = mock_stat
            mock_files_list.append(mock_file)
        
        mock_backup_dir.glob.return_value = mock_files_list
        
        response = client.get("/api/feedback/backup-files")
        
        assert response.status_code == 200
        data = response.json()
        assert "files" in data
        assert len(data["files"]) == 2
        assert data["files"][0]["filename"] == "feedback_backup_20240102_130000.json"  # 최신 파일 먼저

def test_list_backup_files_no_directory(client):
    """백업 폴더가 없는 경우 테스트"""
    
    with patch('backend.routers.feedback.PathlibPath') as mock_path:
        mock_backup_dir = MagicMock()
        mock_backup_dir.exists.return_value = False
        mock_path.return_value = mock_backup_dir
        
        response = client.get("/api/feedback/backup-files")
        
        assert response.status_code == 200
        data = response.json()
        assert data["files"] == []

def test_delete_backup_file_success(client):
    """백업 파일 삭제 성공 테스트"""
    
    filename = "feedback_backup_20240101_120000.json"
    
    with patch('backend.routers.feedback.PathlibPath') as mock_path_class:
        # Mock the path construction chain
        mock_backup_dir = MagicMock()
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_file.unlink.return_value = None
        
        # Mock: PathlibPath("../backups") / filename
        mock_backup_dir.__truediv__.return_value = mock_file
        mock_path_class.return_value = mock_backup_dir
        
        response = client.delete(f"/api/feedback/backup-files/{filename}")
        
        assert response.status_code == 200
        data = response.json()
        assert "성공적으로 삭제되었습니다" in data["message"]
        assert data["success"] is True
        mock_file.unlink.assert_called_once()

def test_delete_backup_file_invalid_filename(client):
    """잘못된 파일명으로 백업 파일 삭제 테스트"""
    
    invalid_filename = "invalid_file.txt"
    
    response = client.delete(f"/api/feedback/backup-files/{invalid_filename}")
    
    assert response.status_code == 400
    data = response.json()
    assert "유효하지 않은 백업 파일명" in data["detail"]

def test_delete_backup_file_not_found(client):
    """존재하지 않는 백업 파일 삭제 테스트"""
    
    filename = "feedback_backup_20240101_120000.json"
    
    with patch('backend.routers.feedback.PathlibPath') as mock_path_class:
        # Mock the path construction chain
        mock_backup_dir = MagicMock()
        mock_file = MagicMock()
        mock_file.exists.return_value = False
        
        # Mock: PathlibPath("../backups") / filename
        mock_backup_dir.__truediv__.return_value = mock_file
        mock_path_class.return_value = mock_backup_dir
        
        response = client.delete(f"/api/feedback/backup-files/{filename}")
        
        assert response.status_code == 404
        data = response.json()
        assert "백업 파일을 찾을 수 없습니다" in data["detail"]

def test_download_backup_file_success(client):
    """백업 파일 다운로드 성공 테스트"""
    
    filename = "feedback_backup_20240101_120000.json"
    
    with patch('backend.routers.feedback.PathlibPath') as mock_path, \
         patch('backend.routers.feedback.FileResponse') as mock_file_response:
        
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_path.return_value = mock_file
        
        mock_file_response.return_value = "mock_file_response"
        
        response = client.get(f"/api/feedback/backup-files/{filename}/download")
        
        # FileResponse 가 호출되었는지 확인
        mock_file_response.assert_called_once()
        call_args = mock_file_response.call_args
        assert call_args[1]["filename"] == filename
        assert call_args[1]["media_type"] == "application/json"

def test_download_backup_file_invalid_filename(client):
    """잘못된 파일명으로 백업 파일 다운로드 테스트"""
    
    invalid_filename = "invalid_file.txt"
    
    response = client.get(f"/api/feedback/backup-files/{invalid_filename}/download")
    
    assert response.status_code == 400
    data = response.json()
    assert "유효하지 않은 백업 파일명" in data["detail"]

def test_generate_summary_report_success(client):
    """요약 보고서 생성 성공 테스트"""
    
    mock_stats = {
        "total_feedback": 10,
        "category_distribution": {"good": 7, "bad": 3},
        "average_scores": {"overall": 4.2, "usefulness": 4.0}
    }
    
    mock_insights = {
        "negative_feedback_count": 3,
        "common_issues": ["정확성 부족", "완성도 부족"],
        "improvement_suggestions": ["더 상세한 분석 필요"]
    }
    
    with patch('backend.routers.feedback.feedback_manager') as mock_manager:
        mock_manager.get_feedback_stats.return_value = mock_stats
        mock_manager.get_improvement_insights.return_value = mock_insights
        
        response = client.post("/api/feedback/summary-report")
        
        assert response.status_code == 200
        data = response.json()
        assert "report_data" in data
        assert "filename" in data
        assert data["success"] is True
        
        # 보고서 데이터 구조 확인
        report_data = data["report_data"]
        assert "generated_at" in report_data
        assert "summary" in report_data
        assert "insights" in report_data
        assert "report_metadata" in report_data
        
        # 요약 데이터 확인
        assert report_data["summary"]["total_feedback"] == 10
        assert report_data["insights"]["negative_feedback_count"] == 3
        assert report_data["report_metadata"]["report_type"] == "feedback_summary"

def test_generate_summary_report_error(client):
    """요약 보고서 생성 실패 테스트"""
    
    with patch('backend.routers.feedback.feedback_manager') as mock_manager:
        mock_manager.get_feedback_stats.side_effect = Exception("Database error")
        
        response = client.post("/api/feedback/summary-report")
        
        assert response.status_code == 500
        data = response.json()
        assert "요약 보고서 생성 중 오류가 발생했습니다" in data["detail"]