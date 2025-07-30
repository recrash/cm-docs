"""
피드백 시스템 관리자
사용자 피드백을 수집, 저장, 분석하는 기능을 제공합니다.
"""

import sqlite3
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

class FeedbackManager:
    def __init__(self, db_path: str = "feedback.db"):
        """피드백 매니저 초기화"""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """데이터베이스 테이블 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 시나리오 피드백 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scenario_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scenario_id TEXT UNIQUE NOT NULL,
                    timestamp TEXT NOT NULL,
                    git_analysis_hash TEXT NOT NULL,
                    repo_path TEXT,
                    scenario_content TEXT NOT NULL,
                    overall_score INTEGER CHECK(overall_score >= 1 AND overall_score <= 5),
                    usefulness_score INTEGER CHECK(usefulness_score >= 1 AND usefulness_score <= 5),
                    accuracy_score INTEGER CHECK(accuracy_score >= 1 AND accuracy_score <= 5),
                    completeness_score INTEGER CHECK(completeness_score >= 1 AND completeness_score <= 5),
                    category TEXT CHECK(category IN ('good', 'bad', 'neutral')),
                    comments TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 개별 테스트케이스 피드백 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS testcase_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scenario_id TEXT NOT NULL,
                    testcase_id TEXT NOT NULL,
                    score INTEGER CHECK(score >= 1 AND score <= 5),
                    comments TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (scenario_id) REFERENCES scenario_feedback (scenario_id)
                )
            ''')
            
            conn.commit()
    
    def generate_scenario_id(self, git_analysis: str, scenario_content: Dict) -> str:
        """Git 분석과 시나리오 내용을 기반으로 고유 ID 생성"""
        content_str = json.dumps(scenario_content, sort_keys=True, ensure_ascii=False)
        combined = f"{git_analysis}{content_str}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()[:16]
    
    def save_feedback(self, 
                     git_analysis: str,
                     scenario_content: Dict,
                     feedback_data: Dict,
                     repo_path: str = "") -> bool:
        """피드백 데이터 저장"""
        try:
            scenario_id = self.generate_scenario_id(git_analysis, scenario_content)
            git_analysis_hash = hashlib.sha256(git_analysis.encode('utf-8')).hexdigest()[:16]
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 시나리오 피드백 저장 (REPLACE를 사용해 중복 시 업데이트)
                cursor.execute('''
                    INSERT OR REPLACE INTO scenario_feedback 
                    (scenario_id, timestamp, git_analysis_hash, repo_path, scenario_content,
                     overall_score, usefulness_score, accuracy_score, completeness_score, 
                     category, comments)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    scenario_id,
                    datetime.now().isoformat(),
                    git_analysis_hash,
                    repo_path,
                    json.dumps(scenario_content, ensure_ascii=False),
                    feedback_data.get('overall_score'),
                    feedback_data.get('usefulness_score'),
                    feedback_data.get('accuracy_score'),
                    feedback_data.get('completeness_score'),
                    feedback_data.get('category'),
                    feedback_data.get('comments', '')
                ))
                
                # 기존 테스트케이스 피드백 삭제
                cursor.execute('DELETE FROM testcase_feedback WHERE scenario_id = ?', (scenario_id,))
                
                # 개별 테스트케이스 피드백 저장
                testcase_feedback = feedback_data.get('testcase_feedback', [])
                for tc_feedback in testcase_feedback:
                    cursor.execute('''
                        INSERT INTO testcase_feedback 
                        (scenario_id, testcase_id, score, comments)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        scenario_id,
                        tc_feedback.get('testcase_id'),
                        tc_feedback.get('score'),
                        tc_feedback.get('comments', '')
                    ))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"피드백 저장 중 오류 발생: {e}")
            return False
    
    def get_feedback_stats(self) -> Dict[str, Any]:
        """피드백 통계 조회"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 전체 통계
            cursor.execute('SELECT COUNT(*) FROM scenario_feedback')
            total_feedback = cursor.fetchone()[0]
            
            # 카테고리별 통계
            cursor.execute('''
                SELECT category, COUNT(*) 
                FROM scenario_feedback 
                WHERE category IS NOT NULL
                GROUP BY category
            ''')
            category_stats = dict(cursor.fetchall())
            
            # 평균 점수
            cursor.execute('''
                SELECT 
                    AVG(overall_score) as avg_overall,
                    AVG(usefulness_score) as avg_usefulness,
                    AVG(accuracy_score) as avg_accuracy,
                    AVG(completeness_score) as avg_completeness
                FROM scenario_feedback 
                WHERE overall_score IS NOT NULL
            ''')
            scores = cursor.fetchone()
            
            return {
                'total_feedback': total_feedback,
                'category_distribution': category_stats,
                'average_scores': {
                    'overall': round(scores[0] or 0, 2),
                    'usefulness': round(scores[1] or 0, 2),
                    'accuracy': round(scores[2] or 0, 2),
                    'completeness': round(scores[3] or 0, 2)
                }
            }
    
    def get_feedback_examples(self, category: str = None, limit: int = 10) -> List[Dict]:
        """피드백 예시 조회 (좋은 예시/나쁜 예시)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT scenario_id, scenario_content, overall_score, category, comments, timestamp
                FROM scenario_feedback
            '''
            params = []
            
            if category:
                query += ' WHERE category = ?'
                params.append(category)
            
            query += ' ORDER BY timestamp DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            examples = []
            for row in results:
                examples.append({
                    'scenario_id': row[0],
                    'scenario_content': json.loads(row[1]),
                    'overall_score': row[2],
                    'category': row[3],
                    'comments': row[4],
                    'timestamp': row[5]
                })
            
            return examples
    
    def get_improvement_insights(self) -> Dict[str, Any]:
        """개선 포인트 분석"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 낮은 점수 영역 분석
            cursor.execute('''
                SELECT 
                    COUNT(CASE WHEN usefulness_score <= 2 THEN 1 END) as low_usefulness,
                    COUNT(CASE WHEN accuracy_score <= 2 THEN 1 END) as low_accuracy,
                    COUNT(CASE WHEN completeness_score <= 2 THEN 1 END) as low_completeness,
                    COUNT(*) as total
                FROM scenario_feedback
                WHERE overall_score IS NOT NULL
            ''')
            
            result = cursor.fetchone()
            total = result[3] or 1  # 0으로 나누기 방지
            
            # 자주 나오는 부정적 키워드 (간단한 분석)
            cursor.execute('''
                SELECT comments 
                FROM scenario_feedback 
                WHERE category = 'bad' AND comments IS NOT NULL AND comments != ''
            ''')
            
            negative_comments = [row[0] for row in cursor.fetchall()]
            
            return {
                'problem_areas': {
                    'usefulness': round((result[0] / total) * 100, 1),
                    'accuracy': round((result[1] / total) * 100, 1),
                    'completeness': round((result[2] / total) * 100, 1)
                },
                'negative_feedback_count': len(negative_comments),
                'sample_negative_comments': negative_comments[:5]  # 최근 5개 샘플
            }
    
    def export_feedback_data(self, output_path: str = "feedback_export.json") -> bool:
        """피드백 데이터를 JSON으로 내보내기"""
        try:
            with sqlite3.connect(self.db_path) as conn:
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
                        'scores': {
                            'overall': row[6],
                            'usefulness': row[7],
                            'accuracy': row[8],
                            'completeness': row[9]
                        },
                        'category': row[10],
                        'comments': row[11],
                        'created_at': row[12]
                    }
                    
                    # 테스트케이스 피드백 파싱
                    if row[13]:  # testcase_data가 있는 경우
                        testcase_feedback = []
                        for tc_data in row[13].split('|'):
                            if tc_data:
                                parts = tc_data.split(':')
                                if len(parts) >= 2:
                                    testcase_feedback.append({
                                        'testcase_id': parts[0],
                                        'score': int(parts[1]),
                                        'comments': parts[2] if len(parts) > 2 else ''
                                    })
                        feedback_item['testcase_feedback'] = testcase_feedback
                    
                    export_data.append(feedback_item)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
                
                return True
                
        except Exception as e:
            print(f"피드백 데이터 내보내기 중 오류 발생: {e}")
            return False