"""
피드백 관련 Pydantic 모델
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional
from enum import Enum
import logging

# 로거 설정
logger = logging.getLogger(__name__)

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
    
    @validator('testcase_id')
    def validate_testcase_id(cls, v):
        logger.debug(f"테스트케이스 ID 검증: {v}")
        if not v or not v.strip():
            logger.warning("테스트케이스 ID가 비어있음")
            raise ValueError("테스트케이스 ID는 비어있을 수 없습니다.")
        return v.strip()
    
    @validator('score')
    def validate_score(cls, v):
        logger.debug(f"점수 검증: {v}")
        if v < 1 or v > 5:
            logger.warning(f"유효하지 않은 점수: {v}")
            raise ValueError("점수는 1-5 사이여야 합니다.")
        return v

class FeedbackRequest(BaseModel):
    """피드백 제출 요청"""
    feedback_type: FeedbackType
    comments: Optional[str] = None
    testcase_feedback: List[TestCaseFeedback] = []
    repo_path: str
    git_analysis: str
    scenario_content: dict
    
    @validator('repo_path')
    def validate_repo_path(cls, v):
        logger.debug(f"저장소 경로 검증: {v}")
        if not v or not v.strip():
            logger.warning("저장소 경로가 비어있음")
            raise ValueError("저장소 경로는 비어있을 수 없습니다.")
        return v.strip()
    
    @validator('git_analysis')
    def validate_git_analysis(cls, v):
        logger.debug(f"Git 분석 결과 검증: 길이={len(v) if v else 0}")
        if not v or not v.strip():
            logger.warning("Git 분석 결과가 비어있음")
            raise ValueError("Git 분석 결과는 비어있을 수 없습니다.")
        return v.strip()
    
    @validator('scenario_content')
    def validate_scenario_content(cls, v):
        logger.debug(f"시나리오 내용 검증: 키 수={len(v) if v else 0}")
        if not v:
            logger.warning("시나리오 내용이 비어있음")
            raise ValueError("시나리오 내용은 비어있을 수 없습니다.")
        return v

class FeedbackStats(BaseModel):
    """피드백 통계"""
    total_feedback: int = 0
    category_distribution: dict = {}
    average_scores: dict = {}
    
    def __init__(self, **data):
        super().__init__(**data)
        logger.info(f"피드백 통계 생성: total_feedback={self.total_feedback}")

class FeedbackExample(BaseModel):
    """피드백 예시"""
    overall_score: int
    comments: Optional[str]
    scenario_content: dict
    timestamp: str
    
    @validator('overall_score')
    def validate_overall_score(cls, v):
        logger.debug(f"전체 점수 검증: {v}")
        if v < 1 or v > 5:
            logger.warning(f"유효하지 않은 전체 점수: {v}")
            raise ValueError("전체 점수는 1-5 사이여야 합니다.")
        return v

class ImprovementInsights(BaseModel):
    """개선 인사이트"""
    problem_areas: dict = {}
    negative_feedback_count: int = 0
    sample_negative_comments: List[str] = []
    
    def __init__(self, **data):
        super().__init__(**data)
        logger.info(f"개선 인사이트 생성: negative_feedback_count={self.negative_feedback_count}")