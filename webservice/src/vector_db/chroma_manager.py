import chromadb
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer

class ChromaManager:
    """ChromaDB를 사용한 벡터 데이터베이스 관리 클래스"""
    
    def __init__(self, persist_directory: str = "vector_db_data", embedding_model: str = "jhgan/ko-sroberta-multitask", local_model_path: str = None):
        """
        ChromaDB 매니저 초기화
        
        Args:
            persist_directory: 벡터 DB 저장 경로
            embedding_model: 한국어 임베딩 모델 (HuggingFace 모델명)
            local_model_path: 로컬 모델 경로 (우선 사용)
        """
        import os
        
        self.persist_directory = persist_directory
        self.embedding_model_name = embedding_model
        
        # ChromaDB 클라이언트 초기화
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # 임베딩 모델 로드 (로컬 경로 우선)
        if local_model_path and os.path.exists(local_model_path):
            print(f"로컬 임베딩 모델 사용: {local_model_path}")
            try:
                self.embedding_model = SentenceTransformer(local_model_path)
                self.embedding_model_name = f"local:{local_model_path}"
            except Exception as e:
                print(f"로컬 모델 로딩 실패 ({e}), HuggingFace 모델로 대체")
                self.embedding_model = SentenceTransformer(embedding_model)
        else:
            if local_model_path:
                print(f"로컬 모델 경로 없음: {local_model_path}")
            print(f"HuggingFace 임베딩 모델 사용: {embedding_model}")
            try:
                self.embedding_model = SentenceTransformer(embedding_model)
            except Exception as e:
                print(f"임베딩 모델 로딩 실패: {e}")
                print("폐쇄망 환경인 경우 다음 방법을 시도해보세요:")
                print("1. 인터넷 연결 환경에서 모델을 미리 다운로드")
                print("2. config.json의 local_embedding_model_path에 로컬 모델 경로 설정")
                print("3. 또는 config.json에서 rag.enabled를 false로 설정")
                raise
        
        # 컬렉션 초기화
        self.collection_name = "test_scenarios"
        self.collection = self._get_or_create_collection()
    
    def _get_or_create_collection(self):
        """컬렉션 생성 또는 기존 컬렉션 가져오기"""
        try:
            collection = self.client.get_collection(name=self.collection_name)
            print(f"기존 컬렉션 '{self.collection_name}' 로드됨")
            return collection
        except Exception as e:
            if "does not exist" in str(e).lower():
                collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "테스트 시나리오 생성을 위한 Git 분석 데이터"}
                )
                print(f"새 컬렉션 '{self.collection_name}' 생성됨")
                return collection
            else:
                print(f"컬렉션 로드 중 오류 발생: {e}")
                raise
    
    def add_documents(self, documents: List[str], metadatas: List[Dict[str, Any]], ids: List[str]):
        """
        문서들을 벡터 DB에 추가
        
        Args:
            documents: 문서 텍스트 리스트
            metadatas: 각 문서의 메타데이터 리스트
            ids: 각 문서의 고유 ID 리스트
        """
        try:
            # 임베딩 생성
            embeddings = self.embedding_model.encode(documents).tolist()
            
            # ChromaDB에 추가
            self.collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            print(f"{len(documents)}개 문서가 벡터 DB에 추가되었습니다.")
            
        except Exception as e:
            print(f"문서 추가 중 오류 발생: {e}")
            raise
    
    def search_similar_documents(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """
        유사한 문서 검색
        
        Args:
            query: 검색 쿼리
            n_results: 반환할 결과 수
            
        Returns:
            검색 결과 딕셔너리
        """
        try:
            # 쿼리 검증
            if not query or not query.strip():
                print("빈 쿼리로는 검색할 수 없습니다.")
                return {'documents': [], 'metadatas': [], 'distances': []}
            
            # 공백 및 특수문자만 있는 쿼리 검증
            clean_query = query.strip()
            if not clean_query or len(clean_query) < 2:
                print("쿼리가 너무 짧습니다.")
                return {'documents': [], 'metadatas': [], 'distances': []}
            
            # 쿼리 임베딩 생성
            query_embedding = self.embedding_model.encode([clean_query]).tolist()
            
            # 유사도 검색
            results = self.collection.query(
                query_embeddings=query_embedding,
                n_results=n_results,
                include=['documents', 'metadatas', 'distances']
            )
            
            return {
                'documents': results['documents'][0] if results['documents'] else [],
                'metadatas': results['metadatas'][0] if results['metadatas'] else [],
                'distances': results['distances'][0] if results['distances'] else []
            }
            
        except Exception as e:
            print(f"문서 검색 중 오류 발생: {e}")
            return {'documents': [], 'metadatas': [], 'distances': []}
    
    def delete_collection(self):
        """컬렉션 삭제"""
        try:
            self.client.delete_collection(name=self.collection_name)
            print(f"컬렉션 '{self.collection_name}' 삭제됨")
        except Exception as e:
            print(f"컬렉션 삭제 중 오류 발생: {e}")
    
    def get_collection_info(self) -> Dict[str, Any]:
        """컬렉션 정보 반환"""
        try:
            count = self.collection.count()
            return {
                'name': self.collection_name,
                'count': count,
                'persist_directory': self.persist_directory,
                'embedding_model': self.embedding_model_name
            }
        except Exception as e:
            print(f"컬렉션 정보 조회 중 오류 발생: {e}")
            return {}
    
    def update_document(self, document_id: str, document: str, metadata: Dict[str, Any]):
        """기존 문서 업데이트"""
        try:
            embedding = self.embedding_model.encode([document]).tolist()
            
            self.collection.update(
                ids=[document_id],
                documents=[document],
                embeddings=embedding,
                metadatas=[metadata]
            )
            print(f"문서 ID '{document_id}' 업데이트됨")
            
        except Exception as e:
            print(f"문서 업데이트 중 오류 발생: {e}")
            raise