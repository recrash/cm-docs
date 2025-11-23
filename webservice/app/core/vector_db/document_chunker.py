import re
from typing import List, Dict, Any
from datetime import datetime

# 코드 구조 인식용 분리자 (우선순위 순서)
DEFAULT_SEPARATORS = [
    "\nclass ",    # Python 클래스 정의
    "\ndef ",      # Python 함수 정의
    "\n\n",        # 문단 구분
    "\n",          # 줄바꿈
    " ",           # 공백
    ""             # 문자 단위 분할 (최후 수단)
]

class DocumentChunker:
    """문서를 청크 단위로 분할하는 클래스"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        문서 청커 초기화
        
        Args:
            chunk_size: 각 청크의 최대 문자 수
            chunk_overlap: 청크 간 겹치는 문자 수
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_git_analysis(self, git_analysis_text: str, repo_path: str) -> List[Dict[str, Any]]:
        """
        Git 분석 결과를 청크로 분할
        
        Args:
            git_analysis_text: Git 분석 결과 텍스트
            repo_path: Git 저장소 경로
            
        Returns:
            청크 딕셔너리 리스트
        """
        chunks = []
        
        # 섹션별로 나누기 (커밋 메시지, 코드 변경사항 등)
        sections = self._split_into_sections(git_analysis_text)
        
        for section_name, section_content in sections.items():
            section_chunks = self._chunk_text(section_content)
            
            for i, chunk in enumerate(section_chunks):
                chunk_data = {
                    'text': chunk,
                    'metadata': {
                        'source': 'git_analysis',
                        'repo_path': repo_path,
                        'section': section_name,
                        'chunk_index': i,
                        'timestamp': datetime.now().isoformat(),
                        'chunk_size': len(chunk)
                    },
                    'id': f"git_{section_name}_{i}_{hash(chunk) % 10000}"
                }
                chunks.append(chunk_data)
        
        return chunks
    
    def chunk_document(self, document_text: str, document_type: str, source_path: str = "") -> List[Dict[str, Any]]:
        """
        일반 문서를 청크로 분할
        
        Args:
            document_text: 문서 텍스트
            document_type: 문서 타입 (예: 'docx', 'txt', 'requirements')
            source_path: 원본 파일 경로
            
        Returns:
            청크 딕셔너리 리스트
        """
        chunks = []
        text_chunks = self._chunk_text(document_text)
        
        for i, chunk in enumerate(text_chunks):
            chunk_data = {
                'text': chunk,
                'metadata': {
                    'source': document_type,
                    'source_path': source_path,
                    'chunk_index': i,
                    'timestamp': datetime.now().isoformat(),
                    'chunk_size': len(chunk)
                },
                'id': f"{document_type}_{i}_{hash(chunk) % 10000}"
            }
            chunks.append(chunk_data)
        
        return chunks
    
    def _split_into_sections(self, git_analysis_text: str) -> Dict[str, str]:
        """Git 분석 텍스트를 섹션별로 분할"""
        sections = {}
        
        # 커밋 메시지 섹션 추출
        commit_match = re.search(r'### 커밋 메시지 목록:(.*?)(?=###|$)', git_analysis_text, re.DOTALL)
        if commit_match:
            sections['commits'] = commit_match.group(1).strip()
        
        # 코드 변경사항 섹션 추출
        code_match = re.search(r'### 주요 코드 변경 내용.*?:(.*?)(?=###|$)', git_analysis_text, re.DOTALL)
        if code_match:
            sections['code_changes'] = code_match.group(1).strip()
        
        # 파일 변경사항 섹션 추출
        file_match = re.search(r'### 변경된 파일 목록:(.*?)(?=###|$)', git_analysis_text, re.DOTALL)
        if file_match:
            sections['file_changes'] = file_match.group(1).strip()
        
        # 기타 섹션이 없는 경우 전체 텍스트 사용
        if not sections:
            sections['full_text'] = git_analysis_text
        
        return sections

    def _recursive_split_text(self, text: str, separators: List[str]) -> List[str]:
        """
        재귀적으로 텍스트를 의미 있는 단위로 분할

        Args:
            text: 분할할 텍스트
            separators: 우선순위 순 분리자 리스트

        Returns:
            분할된 청크 리스트
        """
        # 1. 기본 케이스: 텍스트가 충분히 작으면 그대로 반환
        if not text:
            return []

        if len(text) <= self.chunk_size:
            return [text]

        # 2. 분리자 없으면 강제 문자 단위 분할
        if not separators:
            return [text[i:i + self.chunk_size]
                    for i in range(0, len(text), self.chunk_size)]

        # 3. 현재 분리자로 분할 시도
        separator = separators[0]
        next_separators = separators[1:]

        # 빈 문자열 분리자는 문자 단위 분할
        if separator == "":
            return [text[i:i + self.chunk_size]
                    for i in range(0, len(text), self.chunk_size)]

        # 4. 분리자로 텍스트 분할
        splits = text.split(separator)

        # 5. 분할된 조각들을 chunk_size 이하로 병합
        chunks = []
        current_chunk = []
        current_length = 0

        for i, split in enumerate(splits):
            # 분리자 복원 (첫 조각 제외)
            if i > 0:
                split = separator + split

            split_length = len(split)

            # 단일 조각이 chunk_size 초과 시 재귀 분할
            if split_length > self.chunk_size:
                # 현재 누적 청크 저장
                if current_chunk:
                    chunks.append("".join(current_chunk))
                    current_chunk = []
                    current_length = 0

                # 큰 조각을 다음 분리자로 재귀 분할
                chunks.extend(
                    self._recursive_split_text(split, next_separators)
                )

            # 현재 청크에 추가 가능한 경우
            elif current_length + split_length <= self.chunk_size:
                current_chunk.append(split)
                current_length += split_length

            # 새 청크 시작
            else:
                if current_chunk:
                    chunks.append("".join(current_chunk))
                current_chunk = [split]
                current_length = split_length

        # 마지막 청크 추가
        if current_chunk:
            chunks.append("".join(current_chunk))

        return chunks

    def _chunk_text(self, text: str) -> List[str]:
        """
        텍스트를 의미 있는 단위로 청크 분할 (코드 구조 인식)

        Args:
            text: 분할할 텍스트

        Returns:
            청크 리스트
        """
        # 빈 문자열 또는 None 처리
        if not text:
            return []

        # 텍스트가 chunk_size 이하면 그대로 반환
        if len(text) <= self.chunk_size:
            return [text]

        # 재귀적 분할 수행 (코드 구조 인식)
        chunks = self._recursive_split_text(text, DEFAULT_SEPARATORS)

        # 빈 청크 제거 및 공백 정리
        return [chunk.strip() for chunk in chunks if chunk.strip()]
    
    def chunk_test_scenarios(self, test_scenarios: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        기존 테스트 시나리오를 청크로 분할하여 학습 데이터로 활용
        
        Args:
            test_scenarios: 테스트 시나리오 리스트
            
        Returns:
            청크 딕셔너리 리스트
        """
        chunks = []
        
        for scenario_idx, scenario in enumerate(test_scenarios):
            # 시나리오 전체를 하나의 문서로 처리
            scenario_text = f"""
테스트 시나리오명: {scenario.get('Test Scenario Name', '')}
시나리오 개요: {scenario.get('Scenario Description', '')}

테스트 케이스:
"""
            
            for case in scenario.get('Test Cases', []):
                case_text = f"""
ID: {case.get('ID', '')}
절차: {case.get('절차', '')}
사전조건: {case.get('사전조건', '')}
테스트 데이터: {case.get('데이터', '')}
예상결과: {case.get('예상결과', '')}
테스트 종류: {case.get('종류', '')}
"""
                scenario_text += case_text
            
            # 시나리오를 청크로 분할
            text_chunks = self._chunk_text(scenario_text.strip())
            
            for i, chunk in enumerate(text_chunks):
                chunk_data = {
                    'text': chunk,
                    'metadata': {
                        'source': 'test_scenario',
                        'scenario_index': scenario_idx,
                        'chunk_index': i,
                        'scenario_name': scenario.get('Test Scenario Name', ''),
                        'timestamp': datetime.now().isoformat(),
                        'chunk_size': len(chunk)
                    },
                    'id': f"scenario_{scenario_idx}_{i}_{hash(chunk) % 10000}"
                }
                chunks.append(chunk_data)
        
        return chunks