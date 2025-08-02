"""
피드백 관련 Pydantic 모델
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class FeedbackType(str, Enum):
    """피드백 타입"""
    LIKE = "like"
    DISLIKE = "dislike"

class FeedbackCategory(str, Enum):
    """피드백 카테고리"""
    GOOD = "good"
    BAD = "bad"
    NEUTRAL = "neutral"

class TestCaseFeedback(BaseModel):
    """개별 테스트케이스 피드백"""
    testcase_id: str
    score: int = Field(ge=1, le=5, description="1-5점 척도")
    comments: Optional[str] = None

class FeedbackRequest(BaseModel):
    """피드백 제출 요청"""
    feedback_type: FeedbackType
    comments: Optional[str] = None
    testcase_feedback: List[TestCaseFeedback] = []
    repo_path: str
    git_analysis: str
    scenario_content: dict

class FeedbackStats(BaseModel):
    """피드백 통계"""
    total_feedback: int = 0
    category_distribution: dict = {}
    average_scores: dict = {}

class FeedbackExample(BaseModel):
    """피드백 예시"""
    overall_score: int
    comments: Optional[str]
    scenario_content: dict
    timestamp: str

class ImprovementInsights(BaseModel):
    """개선 인사이트"""
    problem_areas: dict = {}
    negative_feedback_count: int = 0
    sample_negative_comments: List[str] = []