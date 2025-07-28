"""
피드백 기반 프롬프트 개선 시스템
사용자 피드백을 분석하여 프롬프트를 동적으로 개선합니다.
"""

from typing import Dict, List, Tuple, Optional
from src.feedback_manager import FeedbackManager
import re
import json

class PromptEnhancer:
    def __init__(self, feedback_manager: FeedbackManager):
        """프롬프트 개선기 초기화"""
        self.feedback_manager = feedback_manager
    
    def get_feedback_insights(self) -> Dict[str, any]:
        """피드백 데이터에서 개선 포인트 추출"""
        # 좋은 예시와 나쁜 예시 분석
        good_examples = self.feedback_manager.get_feedback_examples('good', 10)
        bad_examples = self.feedback_manager.get_feedback_examples('bad', 10)
        
        # 개선 포인트 분석
        insights = self.feedback_manager.get_improvement_insights()
        
        return {
            'good_examples': good_examples,
            'bad_examples': bad_examples,
            'problem_areas': insights['problem_areas'],
            'common_issues': self._extract_common_issues(bad_examples),
            'success_patterns': self._extract_success_patterns(good_examples)
        }
    
    def _extract_common_issues(self, bad_examples: List[Dict]) -> List[str]:
        """나쁜 예시에서 공통 이슈 추출"""
        common_issues = []
        
        # 키워드 기반 이슈 분석
        issue_keywords = {
            '불명확': ['불명확', '모호', '애매', '부정확'],
            '누락': ['누락', '빠짐', '없음', '부족'],
            '중복': ['중복', '반복', '같음'],
            '비현실적': ['비현실적', '불가능', '이상함', '너무'],
            '복잡함': ['복잡', '어려움', '이해하기 힘듦', '길다']
        }
        
        for example in bad_examples:
            comments = example.get('comments', '').lower()
            for issue_type, keywords in issue_keywords.items():
                if any(keyword in comments for keyword in keywords):
                    issue_desc = f"{issue_type}: {comments[:50]}..."
                    if issue_desc not in common_issues:
                        common_issues.append(issue_desc)
        
        return common_issues[:5]  # 상위 5개만
    
    def _extract_success_patterns(self, good_examples: List[Dict]) -> List[str]:
        """좋은 예시에서 성공 패턴 추출"""
        success_patterns = []
        
        # 긍정적 키워드 분석
        positive_keywords = {
            '명확성': ['명확', '이해하기 쉬움', '분명', '정확'],
            '완성도': ['완전', '자세', '충분', '포괄적'],
            '실용성': ['실용적', '유용', '도움', '실무'],
            '구체성': ['구체적', '세부적', '상세', '정밀']
        }
        
        for example in good_examples:
            comments = example.get('comments', '').lower()
            for pattern_type, keywords in positive_keywords.items():
                if any(keyword in comments for keyword in keywords):
                    pattern_desc = f"{pattern_type}: {comments[:50]}..."
                    if pattern_desc not in success_patterns:
                        success_patterns.append(pattern_desc)
        
        return success_patterns[:5]  # 상위 5개만
    
    def generate_enhancement_instructions(self) -> str:
        """피드백 기반 개선 지침 생성"""
        insights = self.get_feedback_insights()
        stats = self.feedback_manager.get_feedback_stats()
        
        # 평균 점수가 낮은 영역 파악
        low_scoring_areas = []
        for area, score in stats['average_scores'].items():
            if score < 3.5:  # 3.5점 미만은 개선 필요
                area_korean = {
                    'usefulness': '유용성',
                    'accuracy': '정확성', 
                    'completeness': '완성도',
                    'overall': '전반적 만족도'
                }.get(area, area)
                low_scoring_areas.append(f"{area_korean}({score:.1f}점)")
        
        enhancement_text = "\n=== 피드백 기반 개선 지침 ===\n"
        
        if low_scoring_areas:
            enhancement_text += f"⚠️ 개선 필요 영역: {', '.join(low_scoring_areas)}\n\n"
        
        if insights['common_issues']:
            enhancement_text += "❌ 피해야 할 패턴:\n"
            for issue in insights['common_issues']:
                enhancement_text += f"- {issue}\n"
            enhancement_text += "\n"
        
        if insights['success_patterns']:
            enhancement_text += "✅ 권장하는 패턴:\n"
            for pattern in insights['success_patterns']:
                enhancement_text += f"- {pattern}\n"
            enhancement_text += "\n"
        
        # 구체적인 개선 가이드라인
        enhancement_text += "📋 구체적 개선 방향:\n"
        
        if stats['average_scores']['accuracy'] < 3.5:
            enhancement_text += "- 코드 변경사항을 더 정확히 반영하여 테스트 시나리오를 작성하세요\n"
            enhancement_text += "- Git diff 내용과 직접적으로 연관된 테스트케이스를 우선적으로 생성하세요\n"
        
        if stats['average_scores']['usefulness'] < 3.5:
            enhancement_text += "- 실무에서 실제로 수행할 수 있는 현실적인 테스트 절차를 작성하세요\n"
            enhancement_text += "- 테스트 데이터는 실제 환경에서 사용 가능한 값으로 설정하세요\n"
        
        if stats['average_scores']['completeness'] < 3.5:
            enhancement_text += "- 테스트 시나리오의 사전조건, 절차, 예상결과를 모두 구체적으로 작성하세요\n"
            enhancement_text += "- Edge case와 예외 상황도 고려한 테스트케이스를 포함하세요\n"
        
        enhancement_text += "\n=== 개선 지침 끝 ===\n"
        
        return enhancement_text
    
    def get_example_scenarios(self) -> Tuple[List[Dict], List[Dict]]:
        """좋은 예시와 나쁜 예시 시나리오 반환"""
        good_examples = self.feedback_manager.get_feedback_examples('good', 3)
        bad_examples = self.feedback_manager.get_feedback_examples('bad', 2)
        
        # 시나리오 내용만 추출하여 예시로 사용
        good_scenarios = []
        for example in good_examples:
            scenario = example['scenario_content']
            feedback_info = {
                'score': example['overall_score'],
                'comments': example['comments']
            }
            good_scenarios.append({'scenario': scenario, 'feedback': feedback_info})
        
        bad_scenarios = []
        for example in bad_examples:
            scenario = example['scenario_content']
            feedback_info = {
                'score': example['overall_score'],
                'comments': example['comments']
            }
            bad_scenarios.append({'scenario': scenario, 'feedback': feedback_info})
        
        return good_scenarios, bad_scenarios
    
    def enhance_prompt(self, base_prompt: str) -> str:
        """기본 프롬프트에 피드백 기반 개선사항 추가"""
        stats = self.feedback_manager.get_feedback_stats()
        
        # 피드백이 충분하지 않으면 기본 프롬프트 반환
        if stats['total_feedback'] < 3:
            return base_prompt
        
        # 개선 지침 생성
        enhancement_instructions = self.generate_enhancement_instructions()
        
        # 예시 시나리오 추가
        good_scenarios, bad_scenarios = self.get_example_scenarios()
        
        enhanced_prompt = base_prompt
        
        # 개선 지침을 프롬프트에 추가
        enhanced_prompt += f"\n\n{enhancement_instructions}\n"
        
        # 좋은 예시 추가
        if good_scenarios:
            enhanced_prompt += "\n=== 좋은 시나리오 예시 ===\n"
            for i, example in enumerate(good_scenarios, 1):
                enhanced_prompt += f"\n좋은 예시 {i} (점수: {example['feedback']['score']}/5):\n"
                enhanced_prompt += f"제목: {example['scenario'].get('Test Scenario Name', 'N/A')}\n"
                enhanced_prompt += f"개요: {example['scenario'].get('Scenario Description', 'N/A')}\n"
                if example['feedback']['comments']:
                    enhanced_prompt += f"평가 의견: {example['feedback']['comments']}\n"
                
                # 테스트케이스 1-2개 예시
                test_cases = example['scenario'].get('Test Cases', [])
                if test_cases:
                    enhanced_prompt += "테스트케이스 예시:\n"
                    for tc in test_cases[:2]:  # 최대 2개만
                        enhanced_prompt += f"- ID: {tc.get('ID', 'N/A')}\n"
                        enhanced_prompt += f"  절차: {tc.get('절차', 'N/A')[:100]}...\n"
                        enhanced_prompt += f"  예상결과: {tc.get('예상결과', 'N/A')[:100]}...\n"
        
        # 나쁜 예시 추가 (주의사항)
        if bad_scenarios:
            enhanced_prompt += "\n=== 피해야 할 패턴 (나쁜 예시) ===\n"
            for i, example in enumerate(bad_scenarios, 1):
                enhanced_prompt += f"\n주의할 점 {i} (점수: {example['feedback']['score']}/5):\n"
                if example['feedback']['comments']:
                    enhanced_prompt += f"문제점: {example['feedback']['comments']}\n"
                enhanced_prompt += f"문제가 된 제목 예시: {example['scenario'].get('Test Scenario Name', 'N/A')}\n"
        
        enhanced_prompt += "\n위의 피드백과 예시를 참고하여 더 나은 테스트 시나리오를 생성해주세요.\n"
        
        return enhanced_prompt
    
    def get_enhancement_summary(self) -> Dict[str, any]:
        """프롬프트 개선 요약 정보 반환"""
        stats = self.feedback_manager.get_feedback_stats()
        insights = self.get_feedback_insights()
        
        return {
            'feedback_count': stats['total_feedback'],
            'average_score': stats['average_scores']['overall'],
            'improvement_areas': [
                area for area, score in stats['average_scores'].items() 
                if score < 3.5
            ],
            'common_issues_count': len(insights['common_issues']),
            'success_patterns_count': len(insights['success_patterns']),
            'good_examples_available': len(insights['good_examples']),
            'bad_examples_available': len(insights['bad_examples'])
        }