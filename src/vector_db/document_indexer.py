import os
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional
from .document_reader import DocumentReader
from .rag_manager import RAGManager

class DocumentIndexer:
    """documents 폴더의 문서들을 자동으로 인덱싱하는 클래스"""
    
    def __init__(self, rag_manager: RAGManager, documents_folder: str = "documents"):
        self.rag_manager = rag_manager
        
        # documents 폴더 경로를 절대 경로로 변환
        if not os.path.isabs(documents_folder):
            # 현재 파일의 디렉토리에서 프로젝트 루트로 이동
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))  # src/vector_db/ 상위로 두 번
            self.documents_folder = os.path.join(project_root, documents_folder)
        else:
            self.documents_folder = documents_folder
            
        self.document_reader = DocumentReader()
        self.indexed_files_cache = {}  # 파일 해시 캐시
        
    def index_documents_folder(self, force_reindex: bool = False) -> Dict[str, Any]:
        """
        documents 폴더의 모든 문서를 인덱싱
        
        Args:
            force_reindex: 기존 인덱스를 무시하고 모든 파일을 다시 인덱싱
            
        Returns:
            인덱싱 결과 정보
        """
        if not os.path.exists(self.documents_folder):
            print(f"문서 폴더가 존재하지 않습니다: {self.documents_folder}")
            return {
                'status': 'error',
                'message': f'문서 폴더가 존재하지 않습니다: {self.documents_folder}',
                'indexed_count': 0,
                'skipped_count': 0,
                'error_count': 0
            }
        
        print(f"문서 폴더 인덱싱 시작: {self.documents_folder}")
        
        results = {
            'status': 'success',
            'indexed_files': [],
            'skipped_files': [],
            'error_files': [],
            'indexed_count': 0,
            'skipped_count': 0,
            'error_count': 0,
            'total_chunks_added': 0
        }
        
        # 지원하는 파일들 찾기
        supported_files = self._find_supported_files()
        
        if not supported_files:
            print("인덱싱할 지원 파일이 없습니다.")
            return results
        
        print(f"발견된 지원 파일: {len(supported_files)}개")
        
        for file_path in supported_files:
            try:
                # 파일이 변경되었는지 확인
                if not force_reindex and not self._is_file_modified(file_path):
                    print(f"스킵 (변경 없음): {file_path}")
                    results['skipped_files'].append(file_path)
                    results['skipped_count'] += 1
                    continue
                
                print(f"인덱싱 중: {file_path}")
                
                # 문서 읽기
                doc_result = self.document_reader.read_document(file_path)
                
                if doc_result['metadata']['status'] == 'error':
                    results['error_files'].append({
                        'file': file_path,
                        'error': doc_result['metadata'].get('error', 'Unknown error')
                    })
                    results['error_count'] += 1
                    continue
                
                # RAG에 문서 추가
                chunks_added = self.rag_manager.add_document(
                    document_text=doc_result['content'],
                    document_type=f"document_{doc_result['metadata']['file_type']}",
                    source_path=file_path
                )
                
                # 파일 해시 업데이트
                self._update_file_cache(file_path)
                
                results['indexed_files'].append({
                    'file': file_path,
                    'chunks_added': chunks_added,
                    'file_type': doc_result['metadata']['file_type'],
                    'metadata': doc_result['metadata']
                })
                results['indexed_count'] += 1
                results['total_chunks_added'] += chunks_added
                
                print(f"  → {chunks_added}개 청크 추가됨")
                
            except Exception as e:
                print(f"파일 인덱싱 중 오류 발생 ({file_path}): {e}")
                results['error_files'].append({
                    'file': file_path,
                    'error': str(e)
                })
                results['error_count'] += 1
        
        print(f"\n인덱싱 완료:")
        print(f"  - 성공: {results['indexed_count']}개")
        print(f"  - 스킵: {results['skipped_count']}개")
        print(f"  - 오류: {results['error_count']}개")
        print(f"  - 총 청크: {results['total_chunks_added']}개")
        
        return results
    
    def _find_supported_files(self) -> List[str]:
        """지원하는 파일들을 찾아서 반환"""
        supported_files = []
        
        for root, dirs, files in os.walk(self.documents_folder):
            for file in files:
                file_path = os.path.join(root, file)
                
                if self.document_reader.is_supported_file(file_path):
                    supported_files.append(file_path)
        
        return sorted(supported_files)
    
    def _is_file_modified(self, file_path: str) -> bool:
        """파일이 마지막 인덱싱 이후 수정되었는지 확인"""
        try:
            current_hash = self._get_file_hash(file_path)
            cached_hash = self.indexed_files_cache.get(file_path)
            
            return current_hash != cached_hash
            
        except Exception as e:
            print(f"파일 해시 확인 중 오류 ({file_path}): {e}")
            return True  # 오류가 발생하면 다시 인덱싱
    
    def _get_file_hash(self, file_path: str) -> str:
        """파일의 MD5 해시값 계산"""
        hash_md5 = hashlib.md5()
        
        # 파일 내용과 수정 시간을 함께 해시
        stat = os.stat(file_path)
        hash_md5.update(f"{stat.st_mtime}_{stat.st_size}".encode())
        
        return hash_md5.hexdigest()
    
    def _update_file_cache(self, file_path: str):
        """파일 캐시 업데이트"""
        try:
            self.indexed_files_cache[file_path] = self._get_file_hash(file_path)
        except Exception as e:
            print(f"파일 캐시 업데이트 중 오류 ({file_path}): {e}")
    
    def get_folder_info(self) -> Dict[str, Any]:
        """documents 폴더 정보 반환"""
        if not os.path.exists(self.documents_folder):
            return {
                'exists': False,
                'total_files': 0,
                'supported_files': 0,
                'file_types': {}
            }
        
        all_files = []
        supported_files = []
        file_types = {}
        
        for root, dirs, files in os.walk(self.documents_folder):
            for file in files:
                file_path = os.path.join(root, file)
                all_files.append(file_path)
                
                file_ext = os.path.splitext(file)[1].lower()
                file_types[file_ext] = file_types.get(file_ext, 0) + 1
                
                if self.document_reader.is_supported_file(file_path):
                    supported_files.append(file_path)
        
        return {
            'exists': True,
            'folder_path': os.path.abspath(self.documents_folder),
            'total_files': len(all_files),
            'supported_files': len(supported_files),
            'supported_extensions': self.document_reader.get_supported_extensions(),
            'file_types': file_types,
            'files': supported_files
        }
    
    def clear_document_index(self):
        """문서 인덱스 캐시 초기화"""
        self.indexed_files_cache.clear()
        print("문서 인덱스 캐시가 초기화되었습니다.")
    
    def reindex_single_file(self, file_path: str) -> Dict[str, Any]:
        """단일 파일을 다시 인덱싱"""
        if not os.path.exists(file_path):
            return {
                'status': 'error',
                'message': f'파일이 존재하지 않습니다: {file_path}'
            }
        
        if not self.document_reader.is_supported_file(file_path):
            return {
                'status': 'error',
                'message': f'지원하지 않는 파일 형식입니다: {file_path}'
            }
        
        try:
            print(f"단일 파일 인덱싱: {file_path}")
            
            # 문서 읽기
            doc_result = self.document_reader.read_document(file_path)
            
            if doc_result['metadata']['status'] == 'error':
                return {
                    'status': 'error',
                    'message': doc_result['metadata'].get('error', 'Unknown error')
                }
            
            # RAG에 문서 추가
            chunks_added = self.rag_manager.add_document(
                document_text=doc_result['content'],
                document_type=f"document_{doc_result['metadata']['file_type']}",
                source_path=file_path
            )
            
            # 파일 해시 업데이트
            self._update_file_cache(file_path)
            
            return {
                'status': 'success',
                'file': file_path,
                'chunks_added': chunks_added,
                'file_type': doc_result['metadata']['file_type'],
                'metadata': doc_result['metadata']
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'파일 인덱싱 중 오류 발생: {str(e)}'
            }