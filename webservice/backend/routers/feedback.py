"""
피드백 관련 API 라우터
"""

from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import JSONResponse, FileResponse
import os
import sys
import logging
import json
from pathlib import Path as PathlibPath
from datetime import datetime
from typing import List, Dict, Any

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

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter()

# 피드백 매니저 인스턴스
feedback_manager = FeedbackManager()

@router.post("/submit")
async def submit_feedback(request: FeedbackRequest):
    """피드백 제출 API"""
    
    logger.info(f"피드백 제출 요청: type={request.feedback_type}, comments_length={len(request.comments) if request.comments else 0}")
    
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
        
        logger.debug(f"피드백 데이터 구성 완료: testcase_feedback_count={len(feedback_data['testcase_feedback'])}")
        
        success = feedback_manager.save_feedback(
            git_analysis=request.git_analysis,
            scenario_content=request.scenario_content,
            feedback_data=feedback_data,
            repo_path=request.repo_path
        )
        
        if not success:
            logger.error("피드백 저장 실패")
            raise HTTPException(status_code=500, detail="피드백 저장 중 오류가 발생했습니다.")
        
        logger.info(f"피드백 제출 성공: type={request.feedback_type}")
        return {"message": "피드백이 성공적으로 제출되었습니다.", "success": True}
        
    except Exception as e:
        logger.error(f"피드백 제출 실패: type={request.feedback_type}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"피드백 제출 중 오류가 발생했습니다: {str(e)}")

@router.get("/stats", response_model=FeedbackStats)
async def get_feedback_stats():
    """피드백 통계 조회 API"""
    
    logger.info("피드백 통계 조회 요청")
    
    try:
        stats = feedback_manager.get_feedback_stats()
        logger.info(f"피드백 통계 조회 성공: total_feedback={stats.get('total_feedback', 0)}")
        return FeedbackStats(**stats)
        
    except Exception as e:
        logger.error(f"피드백 통계 조회 실패: error={str(e)}")
        raise HTTPException(status_code=500, detail=f"피드백 통계 조회 중 오류가 발생했습니다: {str(e)}")

@router.get("/examples/{category}")
async def get_feedback_examples(category: FeedbackCategory, limit: int = 5):
    """피드백 예시 조회 API"""
    
    logger.info(f"피드백 예시 조회 요청: category={category}, limit={limit}")
    
    try:
        examples = feedback_manager.get_feedback_examples(category.value, limit)
        logger.info(f"피드백 예시 조회 성공: category={category}, count={len(examples)}")
        return {"examples": examples}
        
    except Exception as e:
        logger.error(f"피드백 예시 조회 실패: category={category}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"피드백 예시 조회 중 오류가 발생했습니다: {str(e)}")

@router.get("/insights", response_model=ImprovementInsights)
async def get_improvement_insights():
    """개선 인사이트 조회 API"""
    
    logger.info("개선 인사이트 조회 요청")
    
    try:
        insights = feedback_manager.get_improvement_insights()
        logger.info(f"개선 인사이트 조회 성공: negative_feedback_count={insights.get('negative_feedback_count', 0)}")
        return ImprovementInsights(**insights)
        
    except Exception as e:
        logger.error(f"개선 인사이트 조회 실패: error={str(e)}")
        raise HTTPException(status_code=500, detail=f"개선 인사이트 조회 중 오류가 발생했습니다: {str(e)}")

@router.get("/prompt-enhancement")
async def get_prompt_enhancement_info():
    """프롬프트 개선 정보 조회 API"""
    
    logger.info("프롬프트 개선 정보 조회 요청")
    
    try:
        prompt_enhancer = get_prompt_enhancer()
        enhancement_summary = prompt_enhancer.get_enhancement_summary()
        
        logger.info(f"프롬프트 개선 정보 조회 성공: enhancement_count={len(enhancement_summary.get('enhancements', []))}")
        
        # 테스트 호환성을 위해 enhancement_summary 필드를 포함한 응답 구조 생성
        response_data = {
            "enhancement_summary": enhancement_summary,
            **enhancement_summary  # 기존 필드들도 포함
        }
        
        return response_data
        
    except Exception as e:
        logger.error(f"프롬프트 개선 정보 조회 실패: error={str(e)}")
        raise HTTPException(status_code=500, detail=f"프롬프트 개선 정보 조회 중 오류가 발생했습니다: {str(e)}")

@router.get("/prompt-enhancement/preview")
async def get_enhancement_preview():
    """프롬프트 개선 미리보기 API"""
    
    logger.info("프롬프트 개선 미리보기 요청")
    
    try:
        prompt_enhancer = get_prompt_enhancer()
        preview = prompt_enhancer.get_enhanced_prompt_preview()
        
        logger.info("프롬프트 개선 미리보기 성공")
        return {"preview": preview}
        
    except Exception as e:
        logger.error(f"프롬프트 개선 미리보기 실패: error={str(e)}")
        raise HTTPException(status_code=500, detail=f"프롬프트 개선 미리보기 중 오류가 발생했습니다: {str(e)}")

@router.post("/prompt-enhancement/apply")
async def apply_prompt_enhancement():
    """프롬프트 개선 적용 API"""
    
    logger.info("프롬프트 개선 적용 요청")
    
    try:
        prompt_enhancer = get_prompt_enhancer()
        success = prompt_enhancer.apply_enhancements()
        
        if success:
            logger.info("프롬프트 개선 적용 성공")
            return {"message": "프롬프트 개선이 성공적으로 적용되었습니다.", "success": True}
        else:
            logger.error("프롬프트 개선 적용 실패")
            raise HTTPException(status_code=500, detail="프롬프트 개선 적용 중 오류가 발생했습니다.")
        
    except Exception as e:
        logger.error(f"프롬프트 개선 적용 실패: error={str(e)}")
        raise HTTPException(status_code=500, detail=f"프롬프트 개선 적용 중 오류가 발생했습니다: {str(e)}")

@router.get("/export")
async def export_feedback_data():
    """피드백 데이터 내보내기 API"""
    
    logger.info("피드백 데이터 내보내기 요청")
    
    try:
        import sqlite3
        
        # 피드백 데이터 직접 조회하여 반환
        with sqlite3.connect(feedback_manager.db_path) as conn:
            cursor = conn.cursor()
            
            # 모든 피드백 데이터 조회
            cursor.execute('''
                SELECT sf.*, GROUP_CONCAT(tf.testcase_id || ':' || tf.score || ':' || COALESCE(tf.comments, ''), '|') as testcase_data
                FROM scenario_feedback sf
                LEFT JOIN testcase_feedback tf ON sf.scenario_id = tf.scenario_id
                GROUP BY sf.scenario_id
            ''')
            
            results = cursor.fetchall()
            export_data = []
            
            for row in results:
                feedback_item = {
                    'scenario_id': row[1],
                    'timestamp': row[2],
                    'git_analysis_hash': row[3],
                    'repo_path': row[4],
                    'scenario_content': json.loads(row[5]),
                    'overall_score': row[6],
                    'usefulness_score': row[7],
                    'accuracy_score': row[8],
                    'completeness_score': row[9],
                    'category': row[10],
                    'comments': row[11],
                    'created_at': row[12]
                }
                
                # 테스트케이스 피드백 파싱
                if row[13]:  # testcase_data
                    testcase_feedback = []
                    for testcase_item in row[13].split('|'):
                        if testcase_item.strip():
                            parts = testcase_item.split(':')
                            if len(parts) >= 2:
                                testcase_feedback.append({
                                    'testcase_id': parts[0],
                                    'score': int(parts[1]),
                                    'comments': parts[2] if len(parts) > 2 else ''
                                })
                    feedback_item['testcase_feedback'] = testcase_feedback
                else:
                    feedback_item['testcase_feedback'] = []
                
                export_data.append(feedback_item)
        
        # 파일로도 저장
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"feedback_export_{timestamp}.json"
        
        # 루트 디렉토리의 backups 폴더 사용
        backups_dir = PathlibPath("../backups")
        backups_dir.mkdir(exist_ok=True)
        
        with open(backups_dir / filename, 'w', encoding='utf-8') as f:
            json.dump({
                'exported_at': datetime.now().isoformat(),
                'total_records': len(export_data),
                'records': export_data
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"피드백 데이터 내보내기 성공: record_count={len(export_data)}")
        return {
            'message': '데이터가 성공적으로 내보내졌습니다.',
            'filename': filename,
            'total_records': len(export_data),
            'exported_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"피드백 데이터 내보내기 실패: error={str(e)}")
        raise HTTPException(status_code=500, detail=f"피드백 데이터 내보내기 중 오류가 발생했습니다: {str(e)}")

@router.get("/count-by-category")
async def get_feedback_count_by_category():
    """카테고리별 피드백 개수 조회 API"""
    
    logger.info("카테고리별 피드백 개수 조회 요청")
    
    try:
        counts = feedback_manager.get_feedback_count_by_category()
        logger.info(f"카테고리별 피드백 개수 조회 성공: categories={list(counts.keys())}")
        return counts
        
    except Exception as e:
        logger.error(f"카테고리별 피드백 개수 조회 실패: error={str(e)}")
        raise HTTPException(status_code=500, detail=f"카테고리별 피드백 개수 조회 중 오류가 발생했습니다: {str(e)}")

@router.delete("/reset/all")
async def reset_all_feedback(create_backup: bool = True):
    """모든 피드백 초기화 API"""
    
    logger.info(f"모든 피드백 초기화 요청: create_backup={create_backup}")
    
    try:
        success = feedback_manager.reset_all_feedback(create_backup=create_backup)
        
        if success:
            logger.info("모든 피드백 초기화 성공")
            return {"message": "모든 피드백이 성공적으로 초기화되었습니다.", "success": True}
        else:
            logger.error("모든 피드백 초기화 실패")
            raise HTTPException(status_code=500, detail="피드백 초기화 중 오류가 발생했습니다.")
        
    except Exception as e:
        logger.error(f"모든 피드백 초기화 실패: error={str(e)}")
        raise HTTPException(status_code=500, detail=f"피드백 초기화 중 오류가 발생했습니다: {str(e)}")

@router.delete("/reset/category/{category}")
async def reset_feedback_by_category(category: FeedbackCategory, create_backup: bool = True):
    """카테고리별 피드백 초기화 API"""
    
    logger.info(f"카테고리별 피드백 초기화 요청: category={category}, create_backup={create_backup}")
    
    try:
        success = feedback_manager.reset_feedback_by_category(category.value, create_backup=create_backup)
        
        if success:
            logger.info(f"카테고리별 피드백 초기화 성공: category={category}")
            return {"message": f"{category} 카테고리의 피드백이 성공적으로 초기화되었습니다.", "success": True}
        else:
            logger.error(f"카테고리별 피드백 초기화 실패: category={category}")
            raise HTTPException(status_code=500, detail="피드백 초기화 중 오류가 발생했습니다.")
        
    except Exception as e:
        logger.error(f"카테고리별 피드백 초기화 실패: category={category}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"피드백 초기화 중 오류가 발생했습니다: {str(e)}")

@router.post("/cache/reset")
async def reset_feedback_cache():
    """피드백 캐시 초기화 API"""
    
    logger.info("피드백 캐시 초기화 요청")
    
    try:
        reset_feedback_cache()
        logger.info("피드백 캐시 초기화 성공")
        return {"message": "피드백 캐시가 성공적으로 초기화되었습니다.", "success": True}
        
    except Exception as e:
        logger.error(f"피드백 캐시 초기화 실패: error={str(e)}")
        raise HTTPException(status_code=500, detail=f"피드백 캐시 초기화 중 오류가 발생했습니다: {str(e)}")

# 새로운 API 엔드포인트들

@router.get("/backup-files")
async def list_backup_files():
    """백업 파일 목록 조회 API"""
    
    logger.info("백업 파일 목록 조회 요청")
    
    try:
        # 백업 폴더 경로 (루트 디렉토리)
        backup_dir = PathlibPath("../backups")
        
        if not backup_dir.exists():
            logger.warning("백업 폴더가 존재하지 않습니다.")
            return {"files": []}
        
        backup_files = []
        for file_path in backup_dir.glob("feedback_*.json"):
            try:
                stat = file_path.stat()
                backup_files.append({
                    "filename": file_path.name,
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            except Exception as file_error:
                logger.warning(f"백업 파일 정보 읽기 실패: {file_path.name}, error={str(file_error)}")
                continue
        
        # 수정 시간 기준 내림차순 정렬 (최신 파일 먼저)
        backup_files.sort(key=lambda x: x["modified_at"], reverse=True)
        
        logger.info(f"백업 파일 목록 조회 성공: file_count={len(backup_files)}")
        return {"files": backup_files}
        
    except Exception as e:
        logger.error(f"백업 파일 목록 조회 실패: error={str(e)}")
        raise HTTPException(status_code=500, detail=f"백업 파일 목록 조회 중 오류가 발생했습니다: {str(e)}")

@router.delete("/backup-files/{filename}")
async def delete_backup_file(filename: str = Path(..., description="삭제할 백업 파일명")):
    """백업 파일 삭제 API"""
    
    logger.info(f"백업 파일 삭제 요청: filename={filename}")
    
    try:
        # 파일명 검증 (보안 체크)
        if not filename.startswith("feedback_") or not filename.endswith(".json"):
            raise HTTPException(status_code=400, detail="유효하지 않은 백업 파일명입니다.")
        
        # 백업 파일 경로 (루트 디렉토리)
        backup_file = PathlibPath("../backups") / filename
        
        if not backup_file.exists():
            raise HTTPException(status_code=404, detail="백업 파일을 찾을 수 없습니다.")
        
        # 파일 삭제
        backup_file.unlink()
        
        logger.info(f"백업 파일 삭제 성공: filename={filename}")
        return {"message": f"백업 파일 '{filename}'이 성공적으로 삭제되었습니다.", "success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"백업 파일 삭제 실패: filename={filename}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"백업 파일 삭제 중 오류가 발생했습니다: {str(e)}")

@router.get("/backup-files/{filename}/download")
async def download_backup_file(filename: str = Path(..., description="다운로드할 백업 파일명")):
    """백업 파일 다운로드 API"""
    
    logger.info(f"백업 파일 다운로드 요청: filename={filename}")
    
    try:
        # 파일명 검증 (보안 체크)
        if not filename.startswith("feedback_") or not filename.endswith(".json"):
            raise HTTPException(status_code=400, detail="유효하지 않은 백업 파일명입니다.")
        
        # 백업 파일 경로 (루트 디렉토리)
        backup_file = PathlibPath("../backups") / filename
        
        if not backup_file.exists():
            raise HTTPException(status_code=404, detail="백업 파일을 찾을 수 없습니다.")
        
        logger.info(f"백업 파일 다운로드 성공: filename={filename}")
        return FileResponse(
            path=str(backup_file),
            filename=filename,
            media_type="application/json"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"백업 파일 다운로드 실패: filename={filename}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"백업 파일 다운로드 중 오류가 발생했습니다: {str(e)}")

@router.post("/summary-report")
async def generate_summary_report():
    """피드백 요약 보고서 생성 API"""
    
    logger.info("피드백 요약 보고서 생성 요청")
    
    try:
        # 통계 데이터 수집
        stats = feedback_manager.get_feedback_stats()
        insights = feedback_manager.get_improvement_insights()
        
        # 요약 보고서 데이터 구성
        report_data = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_feedback": stats.get("total_feedback", 0),
                "category_distribution": stats.get("category_distribution", {}),
                "average_scores": stats.get("average_scores", {})
            },
            "insights": {
                "negative_feedback_count": insights.get("negative_feedback_count", 0),
                "common_issues": insights.get("common_issues", []),
                "improvement_suggestions": insights.get("improvement_suggestions", [])
            },
            "report_metadata": {
                "report_type": "feedback_summary",
                "report_version": "1.0",
                "data_period": "전체 기간"
            }
        }
        
        # 보고서 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"feedback_summary_report_{timestamp}.json"
        
        logger.info(f"피드백 요약 보고서 생성 성공: total_feedback={stats.get('total_feedback', 0)}")
        return {
            "report_data": report_data,
            "filename": report_filename,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"피드백 요약 보고서 생성 실패: error={str(e)}")
        raise HTTPException(status_code=500, detail=f"요약 보고서 생성 중 오류가 발생했습니다: {str(e)}")