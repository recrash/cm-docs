from typing import List, Dict, Any, Optional
from .chroma_manager import ChromaManager
from .document_chunker import DocumentChunker

class RAGManager:
    """RAG (Retrieval-Augmented Generation) 시스템 통합 관리 클래스"""
    
    def __init__(self, 
                 persist_directory: str = "vector_db_data",
                 embedding_model: str = "jhgan/ko-sroberta-multitask",
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200):
        """
        RAG 매니저 초기화
        
        Args:
            persist_directory: 벡터 DB 저장 경로
            embedding_model: 한국어 임베딩 모델
            chunk_size: 청크 크기
            chunk_overlap: 청크 겹침
        """
        self.chroma_manager = ChromaManager(persist_directory, embedding_model)
        self.document_chunker = DocumentChunker(chunk_size, chunk_overlap)
        
        print("RAG 시스템 초기화 완료")
    
    def add_git_analysis(self, git_analysis_text: str, repo_path: str) -> int:
        """
        Git 분석 결과를 벡터 DB에 추가
        
        Args:
            git_analysis_text: Git 분석 결과 텍스트
            repo_path: Git 저장소 경로
            
        Returns:
            추가된 청크 수
        """
        try:
            # Git 분석 결과를 청크로 분할
            chunks = self.document_chunker.chunk_git_analysis(git_analysis_text, repo_path)
            
            if not chunks:
                print("청크가 생성되지 않았습니다.")
                return 0
            
            # 벡터 DB에 추가
            documents = [chunk['text'] for chunk in chunks]
            metadatas = [chunk['metadata'] for chunk in chunks]
            ids = [chunk['id'] for chunk in chunks]
            
            self.chroma_manager.add_documents(documents, metadatas, ids)
            
            return len(chunks)
            
        except Exception as e:
            print(f"Git 분석 데이터 추가 중 오류 발생: {e}")
            return 0
    
    def add_document(self, document_text: str, document_type: str, source_path: str = "") -> int:
        """
        일반 문서를 벡터 DB에 추가
        
        Args:
            document_text: 문서 텍스트
            document_type: 문서 타입
            source_path: 원본 파일 경로
            
        Returns:
            추가된 청크 수
        """
        try:
            # 문서를 청크로 분할
            chunks = self.document_chunker.chunk_document(document_text, document_type, source_path)
            
            if not chunks:
                print("청크가 생성되지 않았습니다.")
                return 0
            
            # 벡터 DB에 추가
            documents = [chunk['text'] for chunk in chunks]
            metadatas = [chunk['metadata'] for chunk in chunks]
            ids = [chunk['id'] for chunk in chunks]
            
            self.chroma_manager.add_documents(documents, metadatas, ids)
            
            return len(chunks)
            
        except Exception as e:
            print(f"문서 추가 중 오류 발생: {e}")
            return 0
    
    def add_test_scenarios(self, test_scenarios: List[Dict[str, Any]]) -> int:
        """
        기존 테스트 시나리오를 학습 데이터로 벡터 DB에 추가
        
        Args:
            test_scenarios: 테스트 시나리오 리스트
            
        Returns:
            추가된 청크 수
        """
        try:
            # 테스트 시나리오를 청크로 분할
            chunks = self.document_chunker.chunk_test_scenarios(test_scenarios)
            
            if not chunks:
                print("테스트 시나리오 청크가 생성되지 않았습니다.")
                return 0
            
            # 벡터 DB에 추가
            documents = [chunk['text'] for chunk in chunks]
            metadatas = [chunk['metadata'] for chunk in chunks]
            ids = [chunk['id'] for chunk in chunks]
            
            self.chroma_manager.add_documents(documents, metadatas, ids)
            
            return len(chunks)
            
        except Exception as e:
            print(f"테스트 시나리오 추가 중 오류 발생: {e}")
            return 0
    
    def search_relevant_context(self, query: str, n_results: int = 5, source_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        쿼리와 관련된 컨텍스트 검색
        
        Args:
            query: 검색 쿼리
            n_results: 반환할 결과 수
            source_filter: 소스 필터 (예: 'git_analysis', 'test_scenario')
            
        Returns:
            검색 결과와 관련 컨텍스트
        """
        try:
            # 유사도 검색 수행
            search_results = self.chroma_manager.search_similar_documents(query, n_results)
            
            # 소스 필터 적용
            if source_filter:
                filtered_docs = []
                filtered_metas = []
                filtered_distances = []
                
                for doc, meta, dist in zip(search_results['documents'], 
                                         search_results['metadatas'], 
                                         search_results['distances']):
                    if meta.get('source') == source_filter:
                        filtered_docs.append(doc)
                        filtered_metas.append(meta)
                        filtered_distances.append(dist)
                
                search_results = {
                    'documents': filtered_docs,
                    'metadatas': filtered_metas,
                    'distances': filtered_distances
                }
            
            # 컨텍스트 생성
            context = self._build_context(search_results)
            
            return {
                'context': context,
                'search_results': search_results,
                'query': query
            }
            
        except Exception as e:
            print(f"컨텍스트 검색 중 오류 발생: {e}")
            return {'context': '', 'search_results': {}, 'query': query}
    
    def _build_context(self, search_results: Dict[str, Any]) -> str:
        """검색 결과를 바탕으로 컨텍스트 문자열 생성"""
        if not search_results.get('documents'):
            return ""
        
        context_parts = []
        
        for i, (doc, meta, distance) in enumerate(zip(
            search_results['documents'],
            search_results['metadatas'],
            search_results['distances']
        )):
            source = meta.get('source', 'unknown')
            section = meta.get('section', '')
            
            context_part = f"[참조 {i+1}] (출처: {source}"
            if section:
                context_part += f", 섹션: {section}"
            context_part += f", 유사도: {1-distance:.3f})\n{doc}\n"
            
            context_parts.append(context_part)
        
        return "\n".join(context_parts)
    
    def get_system_info(self) -> Dict[str, Any]:
        """RAG 시스템 정보 반환"""
        chroma_info = self.chroma_manager.get_collection_info()
        
        return {
            'chroma_info': chroma_info,
            'chunk_size': self.document_chunker.chunk_size,
            'chunk_overlap': self.document_chunker.chunk_overlap
        }
    
    def clear_database(self):
        """벡터 데이터베이스 초기화"""
        try:
            self.chroma_manager.delete_collection()
            # 컬렉션 재생성
            self.chroma_manager.collection = self.chroma_manager._get_or_create_collection()
            print("벡터 데이터베이스가 초기화되었습니다.")
        except Exception as e:
            print(f"데이터베이스 초기화 중 오류 발생: {e}")
    
    def create_enhanced_prompt(self, base_prompt: str, git_analysis: str, use_rag: bool = True) -> str:
        """
        RAG를 활용하여 향상된 프롬프트 생성
        
        Args:
            base_prompt: 기본 프롬프트
            git_analysis: Git 분석 결과
            use_rag: RAG 사용 여부
            
        Returns:
            향상된 프롬프트
        """
        if not use_rag:
            return base_prompt.format(git_analysis=git_analysis)
        
        try:
            # 디버깅: Git 분석 내용 확인
            print(f"[DEBUG] Git 분석 내용 길이: {len(git_analysis) if git_analysis else 0}")
            print(f"[DEBUG] Git 분석 내용 미리보기: {repr(git_analysis[:100]) if git_analysis else 'None'}")
            
            # Git 분석 내용 검증
            if not git_analysis or not git_analysis.strip():
                print("Git 분석 내용이 비어있어 RAG를 사용할 수 없습니다.")
                return base_prompt.format(git_analysis=git_analysis)
            
            # 공백문자, 탭, 줄바꿈만 있는지 검사
            clean_analysis = git_analysis.strip()
            if not clean_analysis or len(clean_analysis) < 10:
                print("Git 분석 내용이 너무 짧아 RAG를 사용할 수 없습니다.")
                return base_prompt.format(git_analysis=git_analysis)
            
            # 유의미한 텍스트가 있는지 확인 (알파벳, 숫자, 한글이 포함되어야 함)
            import re
            if not re.search(r'[a-zA-Z0-9가-힣]', clean_analysis):
                print("Git 분석 내용에 유의미한 텍스트가 없어 RAG를 사용할 수 없습니다.")
                return base_prompt.format(git_analysis=git_analysis)
            
            # Git 분석 내용을 쿼리로 사용하여 관련 컨텍스트 검색
            query = clean_analysis[:500]  # 처음 500자를 쿼리로 사용
            if not query or len(query.strip()) < 2:
                print("쿼리가 유효하지 않아 RAG를 사용할 수 없습니다.")
                return base_prompt.format(git_analysis=git_analysis)
                
            rag_results = self.search_relevant_context(query, n_results=3)
            
            enhanced_prompt = base_prompt
            
            # 관련 컨텍스트가 있으면 프롬프트에 추가
            if rag_results['context'] and rag_results['context'].strip():
                enhanced_prompt = enhanced_prompt.replace(
                    "### 분석할 Git 변경 내역:",
                    f"### 관련 참조 정보:\n{rag_results['context']}\n\n### 분석할 Git 변경 내역:"
                )
            
            return enhanced_prompt.format(git_analysis=git_analysis)
            
        except Exception as e:
            print(f"RAG 프롬프트 생성 중 오류 발생: {e}")
            print("기본 프롬프트를 사용합니다.")
            return base_prompt.format(git_analysis=git_analysis)