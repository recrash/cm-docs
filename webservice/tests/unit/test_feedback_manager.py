"""
feedback_manager.py 모듈 테스트
"""
import pytest
import sqlite3
import os
import tempfile
from unittest.mock import patch
from src.feedback_manager import FeedbackManager


class TestFeedbackManager:
    """피드백 매니저 테스트"""
    
    @pytest.fixture
    def temp_db(self):
        """임시 데이터베이스 픽스처"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_file:
            db_path = temp_file.name
        
        yield db_path
        
        # 정리
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    def test_database_initialization(self, temp_db):
        """데이터베이스 초기화 테스트"""
        feedback_manager = FeedbackManager(temp_db)
        
        # 테이블 존재 확인
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            
            # scenario_feedback 테이블 확인
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scenario_feedback'")
            assert cursor.fetchone() is not None
            
            # testcase_feedback 테이블 확인
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='testcase_feedback'")
            assert cursor.fetchone() is not None
    
    def test_save_feedback(self, temp_db):
        """피드백 저장 테스트"""
        feedback_manager = FeedbackManager(temp_db)
        
        feedback_data = {
            "overall_score": 4,
            "usefulness_score": 5,
            "accuracy_score": 3,
            "completeness_score": 4,
            "category": "good",
            "comments": "테스트 코멘트"
        }
        
        scenario_content = {"test": "scenario content"}
        
        result = feedback_manager.save_feedback(
            git_analysis="test git analysis",
            scenario_content=scenario_content,
            feedback_data=feedback_data,
            repo_path="/test/repo"
        )
        
        assert result is True
        
        # 데이터베이스에서 확인
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM scenario_feedback")
            rows = cursor.fetchall()
            assert len(rows) == 1
            
            row = rows[0]
            assert row[4] == "/test/repo"  # repo_path
            assert row[6] == 4  # overall_score
            assert row[10] == "good"  # category
    
    def test_get_feedback_stats(self, temp_db):
        """피드백 통계 조회 테스트"""
        feedback_manager = FeedbackManager(temp_db)
        
        # 여러 피드백 저장
        feedback_data_good = {
            "overall_score": 5,
            "usefulness_score": 5,
            "accuracy_score": 4,
            "completeness_score": 5,
            "category": "good",
            "comments": "매우 좋음"
        }
        
        feedback_data_bad = {
            "overall_score": 2,
            "usefulness_score": 2,
            "accuracy_score": 3,
            "completeness_score": 2,
            "category": "bad",
            "comments": "개선 필요"
        }
        
        feedback_manager.save_feedback(
            git_analysis="analysis1",
            scenario_content={"test": "scenario1"},
            feedback_data=feedback_data_good,
            repo_path="/repo1"
        )
        
        feedback_manager.save_feedback(
            git_analysis="analysis2",
            scenario_content={"test": "scenario2"},
            feedback_data=feedback_data_bad,
            repo_path="/repo2"
        )
        
        stats = feedback_manager.get_feedback_stats()
        
        assert stats["total_feedback"] == 2
        assert stats["good_feedback"] == 1
        assert stats["bad_feedback"] == 1
        assert stats["neutral_feedback"] == 0
        assert stats["avg_overall_score"] == 3.5
        assert stats["avg_usefulness_score"] == 3.5
    
    def test_get_feedback_examples(self, temp_db):
        """피드백 예시 조회 테스트"""
        feedback_manager = FeedbackManager(temp_db)
        
        # 좋은 피드백 저장
        feedback_data_good = {
            "overall_score": 5,
            "usefulness_score": 5,
            "accuracy_score": 5,
            "completeness_score": 5,
            "category": "good",
            "comments": "훌륭한 시나리오"
        }
        
        # 나쁜 피드백 저장
        feedback_data_bad = {
            "overall_score": 1,
            "usefulness_score": 2,
            "accuracy_score": 1,
            "completeness_score": 2,
            "category": "bad",
            "comments": "많은 개선 필요"
        }
        
        feedback_manager.save_feedback(
            git_analysis="good analysis",
            scenario_content={"test": "good scenario"},
            feedback_data=feedback_data_good,
            repo_path="/good/repo"
        )
        
        feedback_manager.save_feedback(
            git_analysis="bad analysis",
            scenario_content={"test": "bad scenario"},
            feedback_data=feedback_data_bad,
            repo_path="/bad/repo"
        )
        
        good_examples = feedback_manager.get_feedback_examples(category="good", limit=5)
        bad_examples = feedback_manager.get_feedback_examples(category="bad", limit=5)
        
        assert len(good_examples) == 1
        assert len(bad_examples) == 1
        assert good_examples[0]["comments"] == "훌륭한 시나리오"
        assert bad_examples[0]["comments"] == "많은 개선 필요"
    
    @patch('src.feedback_manager.datetime')
    def test_export_feedback_data(self, mock_datetime, temp_db):
        """피드백 데이터 내보내기 테스트"""
        feedback_manager = FeedbackManager(temp_db)
        
        feedback_data = {
            "overall_score": 4,
            "usefulness_score": 4,
            "accuracy_score": 4,
            "completeness_score": 4,
            "category": "neutral",
            "comments": "보통"
        }
        
        feedback_manager.save_feedback(
            git_analysis="test analysis",
            scenario_content={"test": "scenario"},
            feedback_data=feedback_data,
            repo_path="/test/repo"
        )
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
            export_path = temp_file.name
        
        try:
            result = feedback_manager.export_feedback_data(export_path)
            assert result is True
            assert os.path.exists(export_path)
        finally:
            if os.path.exists(export_path):
                os.unlink(export_path)
    
    @patch('src.feedback_manager.datetime')
    def test_clear_all_feedback(self, mock_datetime, temp_db):
        """전체 피드백 삭제 테스트"""
        mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
        
        feedback_manager = FeedbackManager(temp_db)
        
        # 테스트 데이터 저장
        feedback_data = {
            "overall_score": 3,
            "usefulness_score": 3,
            "accuracy_score": 3,
            "completeness_score": 3,
            "category": "neutral",
            "comments": "테스트"
        }
        
        feedback_manager.save_feedback(
            git_analysis="test",
            scenario_content={"test": "scenario"},
            feedback_data=feedback_data,
            repo_path="/test"
        )
        
        # 전체 삭제
        result = feedback_manager.clear_all_feedback(create_backup=False)
        
        assert result is True
        
        # 데이터 삭제 확인
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM scenario_feedback")
            assert cursor.fetchone()[0] == 0
    
    @patch('src.feedback_manager.datetime')
    def test_clear_feedback_by_category(self, mock_datetime, temp_db):
        """카테고리별 피드백 삭제 테스트"""
        mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
        
        feedback_manager = FeedbackManager(temp_db)
        
        # 다른 카테고리의 피드백 저장
        good_feedback = {
            "overall_score": 5,
            "usefulness_score": 5,
            "accuracy_score": 5,
            "completeness_score": 5,
            "category": "good",
            "comments": "좋음"
        }
        
        bad_feedback = {
            "overall_score": 1,
            "usefulness_score": 1,
            "accuracy_score": 1,
            "completeness_score": 1,
            "category": "bad",
            "comments": "나쁨"
        }
        
        feedback_manager.save_feedback(
            git_analysis="good_analysis",
            scenario_content={"test": "good"},
            feedback_data=good_feedback,
            repo_path="/good"
        )
        
        feedback_manager.save_feedback(
            git_analysis="bad_analysis",
            scenario_content={"test": "bad"},
            feedback_data=bad_feedback,
            repo_path="/bad"
        )
        
        # 'bad' 카테고리만 삭제
        result = feedback_manager.clear_feedback_by_category("bad", create_backup=False)
        
        assert result is True
        
        # 'good' 카테고리는 남아있는지 확인
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM scenario_feedback WHERE category = 'good'")
            assert cursor.fetchone()[0] == 1
            
            cursor.execute("SELECT COUNT(*) FROM scenario_feedback WHERE category = 'bad'")
            assert cursor.fetchone()[0] == 0
    
    def test_generate_scenario_id(self, temp_db):
        """시나리오 ID 생성 테스트"""
        feedback_manager = FeedbackManager(temp_db)
        
        git_analysis = "test analysis"
        scenario_content = {"test": "content"}
        
        id1 = feedback_manager.generate_scenario_id(git_analysis, scenario_content)
        id2 = feedback_manager.generate_scenario_id(git_analysis, scenario_content)
        
        # 같은 입력에 대해 같은 ID 생성
        assert id1 == id2
        assert len(id1) == 16  # 16자리 해시
        
        # 다른 입력에 대해 다른 ID 생성
        different_content = {"different": "content"}
        id3 = feedback_manager.generate_scenario_id(git_analysis, different_content)
        assert id1 != id3
    
    def test_invalid_feedback_data(self, temp_db):
        """잘못된 피드백 데이터 처리 테스트"""
        feedback_manager = FeedbackManager(temp_db)
        
        # 잘못된 점수 (범위 밖)
        invalid_feedback = {
            "overall_score": 6,  # 1-5 범위 밖
            "usefulness_score": 0,  # 1-5 범위 밖
            "accuracy_score": 3,
            "completeness_score": 4,
            "category": "invalid_category",  # 허용되지 않는 카테고리
            "comments": "테스트"
        }
        
        scenario_content = {"test": "content"}
        
        # 예외가 발생해야 함 (SQLite 제약 조건 위반)
        with pytest.raises(Exception):
            feedback_manager.save_feedback(
                git_analysis="test",
                scenario_content=scenario_content,
                feedback_data=invalid_feedback,
                repo_path="/test"
            )