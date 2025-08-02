"""
피드백 API 테스트
"""

import pytest
from unittest.mock import patch, MagicMock

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
        assert "is_active" in data
        assert data["is_active"] is True  # feedback_count >= 3

def test_get_enhancement_preview_available(client):
    """프롬프트 개선 지침 미리보기 (사용 가능) 테스트"""
    
    mock_summary = {"feedback_count": 5}
    
    with patch('backend.routers.feedback.get_prompt_enhancer') as mock_enhancer:
        mock_instance = MagicMock()
        mock_instance.get_enhancement_summary.return_value = mock_summary
        mock_instance.generate_enhancement_instructions.return_value = "개선 지침입니다"
        mock_enhancer.return_value = mock_instance
        
        response = client.get("/api/feedback/prompt-enhancement/preview")
        
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
        assert "instructions" in data

def test_get_enhancement_preview_not_available(client):
    """프롬프트 개선 지침 미리보기 (사용 불가) 테스트"""
    
    mock_summary = {"feedback_count": 1}
    
    with patch('backend.routers.feedback.get_prompt_enhancer') as mock_enhancer:
        mock_instance = MagicMock()
        mock_instance.get_enhancement_summary.return_value = mock_summary
        mock_enhancer.return_value = mock_instance
        
        response = client.get("/api/feedback/prompt-enhancement/preview")
        
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is False
        assert "추가 피드백이 필요" in data["message"]

def test_export_feedback_data(client):
    """피드백 데이터 내보내기 테스트"""
    
    with patch('backend.routers.feedback.feedback_manager') as mock_manager:
        mock_manager.export_feedback_data.return_value = True
        
        response = client.get("/api/feedback/export")
        
        assert response.status_code == 200
        data = response.json()
        assert "성공적으로 내보내졌습니다" in data["message"]
        assert "filename" in data

def test_get_feedback_count_by_category(client):
    """카테고리별 피드백 개수 조회 테스트"""
    
    mock_counts = {"good": 5, "bad": 3, "neutral": 2}
    
    with patch('backend.routers.feedback.feedback_manager') as mock_manager:
        mock_manager.get_feedback_count_by_category.return_value = mock_counts
        
        response = client.get("/api/feedback/count-by-category")
        
        assert response.status_code == 200
        data = response.json()
        assert "category_counts" in data
        assert data["category_counts"]["good"] == 5

def test_reset_all_feedback(client):
    """전체 피드백 초기화 테스트"""
    
    with patch('backend.routers.feedback.feedback_manager') as mock_manager, \
         patch('backend.routers.feedback.reset_feedback_cache') as mock_reset:
        
        mock_manager.clear_all_feedback.return_value = True
        
        response = client.delete("/api/feedback/reset/all?create_backup=true")
        
        assert response.status_code == 200
        data = response.json()
        assert "성공적으로 삭제" in data["message"]
        assert data["backup_created"] is True
        mock_reset.assert_called_once()

def test_reset_feedback_by_category(client):
    """카테고리별 피드백 초기화 테스트"""
    
    with patch('backend.routers.feedback.feedback_manager') as mock_manager, \
         patch('backend.routers.feedback.reset_feedback_cache') as mock_reset:
        
        mock_manager.clear_feedback_by_category.return_value = True
        
        response = client.delete("/api/feedback/reset/category/good?create_backup=true")
        
        assert response.status_code == 200
        data = response.json()
        assert "성공적으로 삭제" in data["message"]
        assert data["backup_created"] is True
        mock_reset.assert_called_once()