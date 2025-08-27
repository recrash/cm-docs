"""
피드백 기반 프롬프트 개선 시스템
사용자 피드백을 분석하여 프롬프트를 동적으로 개선합니다.
"""

from typing import Dict, List, Tuple, Optional
from .feedback_manager import FeedbackManager
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
        """나쁜 예시에서 공통 이슈 추출 (개선된 텍스트 분석)"""
        common_issues = []
        issue_frequency = {}
        
        # 확장된 키워드 기반 이슈 분석
        issue_keywords = {
            '불명확성': ['불명확', '모호', '애매', '부정확', '이해하기 어려움', '헷갈림'],
            '내용 누락': ['누락', '빠짐', '없음', '부족', '생략', '빼먹음'],
            '중복 문제': ['중복', '반복', '같음', '겹침', '또 나옴'],
            '비현실적': ['비현실적', '불가능', '이상함', '너무', '과도', '말이 안됨'],
            '복잡성': ['복잡', '어려움', '이해하기 힘듦', '길다', '너무 많음'],
            '절차 문제': ['절차', '순서', '단계', '흐름', '프로세스'],
            '데이터 문제': ['데이터', '값', '입력', '파라미터', '변수'],
            '예상결과 문제': ['결과', '기대값', '예상', '출력', '응답'],
            '실무 부적합': ['실무', '실제', '현실', '환경', '적용하기 어려움']
        }
        
        for example in bad_examples:
            comments = example.get('comments', '').strip()
            if not comments:
                continue
                
            comments_lower = comments.lower()
            
            # 각 이슈 타입별로 키워드 매칭
            for issue_type, keywords in issue_keywords.items():
                if any(keyword in comments_lower for keyword in keywords):
                    # 실제 사용자 코멘트를 그대로 활용
                    issue_key = f"{issue_type}"
                    if issue_key not in issue_frequency:
                        issue_frequency[issue_key] = []
                    issue_frequency[issue_key].append(comments[:100])
        
        # 빈도수 기준으로 정렬하여 상위 이슈 선별
        for issue_type, comment_list in issue_frequency.items():
            if len(comment_list) >= 1:  # 1개 이상 나타난 이슈만
                # 대표적인 코멘트 선택
                representative_comment = comment_list[0]
                common_issues.append(f"{issue_type}: \"{representative_comment}\"")
        
        return common_issues[:7]  # 상위 7개로 확장
    
    def _extract_success_patterns(self, good_examples: List[Dict]) -> List[str]:
        """좋은 예시에서 성공 패턴 추출 (개선된 텍스트 분석)"""
        success_patterns = []
        pattern_frequency = {}
        
        # 확장된 긍정적 키워드 분석
        positive_keywords = {
            '명확성': ['명확', '이해하기 쉬움', '분명', '정확', '명료', '확실'],
            '완성도': ['완전', '자세', '충분', '포괄적', '빠짐없이', '완벽'],
            '실용성': ['실용적', '유용', '도움', '실무', '현실적', '적용하기 좋음'],
            '구체성': ['구체적', '세부적', '상세', '정밀', '디테일', '자세함'],
            '체계성': ['체계적', '순서', '단계별', '논리적', '흐름'],
            '효율성': ['효율적', '간결', '핵심', '빠른', '효과적'],
            '창의성': ['창의적', '새로운', '다양', '참신', '독특'],
            '적절성': ['적절', '알맞음', '균형', '조화', '적당']
        }
        
        for example in good_examples:
            comments = example.get('comments', '').strip()
            if not comments:
                continue
                
            comments_lower = comments.lower()
            
            # 각 성공 패턴별로 키워드 매칭
            for pattern_type, keywords in positive_keywords.items():
                if any(keyword in comments_lower for keyword in keywords):
                    pattern_key = f"{pattern_type}"
                    if pattern_key not in pattern_frequency:
                        pattern_frequency[pattern_key] = []
                    pattern_frequency[pattern_key].append(comments[:100])
        
        # 빈도수 기준으로 정렬하여 상위 패턴 선별
        for pattern_type, comment_list in pattern_frequency.items():
            if len(comment_list) >= 1:  # 1개 이상 나타난 패턴만
                # 대표적인 코멘트 선택
                representative_comment = comment_list[0]
                success_patterns.append(f"{pattern_type}: \"{representative_comment}\"")
        
        return success_patterns[:7]  # 상위 7개로 확장
    
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
        
        enhancement_text = "\n=== 사용자 피드백 기반 개선 지침 ===\n"
        
        if low_scoring_areas:
            enhancement_text += f"⚠️ 개선 필요 영역: {', '.join(low_scoring_areas)}\n\n"
        
        if insights['common_issues']:
            enhancement_text += "❌ 사용자가 지적한 문제점들 (실제 피드백 기반):\n"
            for issue in insights['common_issues']:
                enhancement_text += f"- {issue}\n"
            enhancement_text += "\n"
        
        if insights['success_patterns']:
            enhancement_text += "✅ 사용자가 좋아한 패턴들 (실제 피드백 기반):\n"
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
        
        # 사용자 텍스트 피드백을 직접 활용한 구체적 지침
        enhancement_text += "\n💬 사용자 의견을 반영한 구체적 지침:\n"
        enhancement_text += "- 위의 실제 사용자 피드백을 면밀히 검토하여 시나리오를 작성하세요\n"
        enhancement_text += "- 사용자가 좋아한 패턴은 적극 활용하고, 지적한 문제점은 반드시 피하세요\n"
        enhancement_text += "- 사용자의 구체적인 의견과 표현을 참고하여 더 만족스러운 결과를 만들어주세요\n"
        
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
        
        # 좋은 예시 추가 (사용자 텍스트 피드백 강조)
        if good_scenarios:
            enhanced_prompt += "\n=== 사용자가 좋게 평가한 시나리오 예시 ===\n"
            for i, example in enumerate(good_scenarios, 1):
                enhanced_prompt += f"\n👍 좋은 예시 {i} (점수: {example['feedback']['score']}/5):\n"
                enhanced_prompt += f"제목: {example['scenario'].get('Test Scenario Name', 'N/A')}\n"
                enhanced_prompt += f"개요: {example['scenario'].get('Scenario Description', 'N/A')}\n"
                if example['feedback']['comments']:
                    enhanced_prompt += f"🗣️ 사용자 평가: \"{example['feedback']['comments']}\"\n"
                    enhanced_prompt += f"→ 이런 특징들을 적극 활용하세요!\n"
                
                # 테스트케이스 1-2개 예시
                test_cases = example['scenario'].get('Test Cases', [])
                if test_cases:
                    enhanced_prompt += "우수한 테스트케이스 구조 참고:\n"
                    for tc in test_cases[:2]:  # 최대 2개만
                        enhanced_prompt += f"- ID: {tc.get('ID', 'N/A')}\n"
                        enhanced_prompt += f"  절차: {tc.get('절차', 'N/A')[:100]}...\n"
                        enhanced_prompt += f"  예상결과: {tc.get('예상결과', 'N/A')[:100]}...\n"
        
        # 나쁜 예시 추가 (사용자 텍스트 피드백 강조)
        if bad_scenarios:
            enhanced_prompt += "\n=== 사용자가 부정적으로 평가한 패턴 (절대 피해야 함) ===\n"
            for i, example in enumerate(bad_scenarios, 1):
                enhanced_prompt += f"\n👎 피해야 할 패턴 {i} (점수: {example['feedback']['score']}/5):\n"
                if example['feedback']['comments']:
                    enhanced_prompt += f"🗣️ 사용자 불만사항: \"{example['feedback']['comments']}\"\n"
                    enhanced_prompt += f"→ 이런 문제점들은 반드시 피하세요!\n"
                enhanced_prompt += f"문제가 된 제목 예시: {example['scenario'].get('Test Scenario Name', 'N/A')}\n"
        
        enhanced_prompt += "\n🎯 중요: 위의 실제 사용자 피드백과 예시를 면밀히 분석하여, 사용자가 만족할 만한 고품질 테스트 시나리오를 생성해주세요.\n"
        enhanced_prompt += "사용자의 구체적인 의견과 표현 방식을 참고하여 더 나은 결과를 만들어주세요.\n"
        
        # 프롬프트 크기 제한 (약 8000 토큰 제한)
        if len(enhanced_prompt) > 32000:  # 대략적인 토큰 제한
            print(f"⚠️ 프롬프트가 너무 길어서 일부 내용을 제거합니다. (길이: {len(enhanced_prompt)})")
            # 기본 프롬프트 + 개선 지침만 유지
            enhanced_prompt = base_prompt + f"\n\n{enhancement_instructions}\n"
            enhanced_prompt += "\n🎯 중요: 위의 개선 지침을 참고하여 고품질 테스트 시나리오를 생성해주세요.\n"
        
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