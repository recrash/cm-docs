"""
피드백 관련 API 라우터
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import os
import sys

# 기존 모듈 import
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from src.feedback_manager import FeedbackManager
from src.prompt_loader import get_prompt_enhancer, reset_feedback_cache

from backend.models.feedback import (
    FeedbackRequest,
    FeedbackStats,
    FeedbackExample,
    ImprovementInsights,
    FeedbackCategory
)

router = APIRouter()

# 피드백 매니저 인스턴스
feedback_manager = FeedbackManager()

@router.post("/submit")
async def submit_feedback(request: FeedbackRequest):
    """피드백 제출 API"""
    
    try:
        # 피드백 데이터 구성
        feedback_data = {
            'overall_score': 4 if request.feedback_type == 'like' else 2,
            'usefulness_score': 4 if request.feedback_type == 'like' else 2,
            'accuracy_score': 4 if request.feedback_type == 'like' else 2,
            'completeness_score': 4 if request.feedback_type == 'like' else 2,
            'category': 'good' if request.feedback_type == 'like' else 'bad',
            'comments': request.comments,
            'testcase_feedback': [tc.dict() for tc in request.testcase_feedback]
        }
        
        success = feedback_manager.save_feedback(
            git_analysis=request.git_analysis,
            scenario_content=request.scenario_content,
            feedback_data=feedback_data,
            repo_path=request.repo_path
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="피드백 저장 중 오류가 발생했습니다.")
        
        return {"message": "피드백이 성공적으로 제출되었습니다.", "success": True}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"피드백 제출 중 오류가 발생했습니다: {str(e)}")

@router.get("/stats", response_model=FeedbackStats)
async def get_feedback_stats():
    """피드백 통계 조회 API"""
    
    try:
        stats = feedback_manager.get_feedback_stats()
        return FeedbackStats(**stats)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"피드백 통계 조회 중 오류가 발생했습니다: {str(e)}")

@router.get("/examples/{category}")
async def get_feedback_examples(category: FeedbackCategory, limit: int = 5):
    """피드백 예시 조회 API"""
    
    try:
        examples = feedback_manager.get_feedback_examples(category.value, limit)
        return {"examples": examples}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"피드백 예시 조회 중 오류가 발생했습니다: {str(e)}")

@router.get("/insights", response_model=ImprovementInsights)
async def get_improvement_insights():
    """개선 인사이트 조회 API"""
    
    try:
        insights = feedback_manager.get_improvement_insights()
        return ImprovementInsights(**insights)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"개선 인사이트 조회 중 오류가 발생했습니다: {str(e)}")

@router.get("/prompt-enhancement")
async def get_prompt_enhancement_info():
    """프롬프트 개선 정보 조회 API"""
    
    try:
        prompt_enhancer = get_prompt_enhancer()
        enhancement_summary = prompt_enhancer.get_enhancement_summary()
        
        return {
            "enhancement_summary": enhancement_summary,
            "is_active": enhancement_summary['feedback_count'] >= 3
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"프롬프트 개선 정보 조회 중 오류가 발생했습니다: {str(e)}")

@router.get("/prompt-enhancement/preview")
async def get_enhancement_preview():
    """프롬프트 개선 지침 미리보기 API"""
    
    try:
        prompt_enhancer = get_prompt_enhancer()
        enhancement_summary = prompt_enhancer.get_enhancement_summary()
        
        if enhancement_summary['feedback_count'] < 3:
            return {
                "available": False,
                "message": f"{3 - enhancement_summary['feedback_count']}개의 추가 피드백이 필요합니다."
            }
        
        instructions = prompt_enhancer.generate_enhancement_instructions()
        return {
            "available": True,
            "instructions": instructions
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"개선 지침 미리보기 중 오류가 발생했습니다: {str(e)}")

@router.get("/export")
async def export_feedback_data():
    """피드백 데이터 내보내기 API"""
    
    try:
        from datetime import datetime
        import os
        
        # backups 폴더 생성 (존재하지 않으면)
        backups_dir = "backups"
        os.makedirs(backups_dir, exist_ok=True)
        
        # 타임스탬프 포함한 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_filename = f"feedback_export_{timestamp}.json"
        export_path = os.path.join(backups_dir, export_filename)
        
        success = feedback_manager.export_feedback_data(export_path)
        
        if not success:
            raise HTTPException(status_code=500, detail="데이터 내보내기 중 오류가 발생했습니다.")
        
        return {
            "message": f"피드백 데이터가 성공적으로 내보내졌습니다. (저장 위치: {export_path})",
            "filename": export_filename,
            "full_path": export_path
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터 내보내기 중 오류가 발생했습니다: {str(e)}")

@router.get("/count-by-category")
async def get_feedback_count_by_category():
    """카테고리별 피드백 개수 조회 API"""
    
    try:
        counts = feedback_manager.get_feedback_count_by_category()
        return {"category_counts": counts}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"카테고리별 피드백 개수 조회 중 오류가 발생했습니다: {str(e)}")

@router.delete("/reset/all")
async def reset_all_feedback(create_backup: bool = True):
    """전체 피드백 초기화 API"""
    
    try:
        success = feedback_manager.clear_all_feedback(create_backup=create_backup)
        
        if not success:
            raise HTTPException(status_code=500, detail="피드백 삭제 중 오류가 발생했습니다.")
        
        # 캐시 리셋
        reset_feedback_cache()
        
        return {
            "message": "모든 피드백이 성공적으로 삭제되었습니다.",
            "backup_created": create_backup
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"피드백 초기화 중 오류가 발생했습니다: {str(e)}")

@router.delete("/reset/category/{category}")
async def reset_feedback_by_category(category: FeedbackCategory, create_backup: bool = True):
    """카테고리별 피드백 초기화 API"""
    
    try:
        success = feedback_manager.clear_feedback_by_category(category.value, create_backup=create_backup)
        
        if not success:
            raise HTTPException(status_code=500, detail="피드백 삭제 중 오류가 발생했습니다.")
        
        # 캐시 리셋
        reset_feedback_cache()
        
        return {
            "message": f"{category.value} 피드백이 성공적으로 삭제되었습니다.",
            "backup_created": create_backup
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"카테고리별 피드백 초기화 중 오류가 발생했습니다: {str(e)}")