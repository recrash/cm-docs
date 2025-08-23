import os
import json
import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
import portalocker

from .document_reader import DocumentReader
from .rag_manager import RAGManager


class DocumentIndexer:
    """documents 폴더의 문서들을 자동으로 인덱싱하는 클래스 (영속적 캐시 지원)"""
    
    CACHE_VERSION = "1.0"
    CACHE_FILENAME = "indexed_files_cache.json"
    
    def __init__(self, rag_manager: RAGManager, documents_folder: str = "documents"):
        self.rag_manager = rag_manager
        
        # pathlib.Path 사용 및 상대 경로로 처리
        if not Path(documents_folder).is_absolute():
            # 현재 파일의 디렉토리에서 프로젝트 루트로 이동
            current_dir = Path(__file__).parent
            project_root = current_dir.parent.parent  # src/vector_db/ 상위로 두 번
            
            # 상대 경로를 프로젝트 루트 기준으로 절대 경로로 변환
            self.documents_folder = (project_root / documents_folder).resolve()
        else:
            self.documents_folder = Path(documents_folder)
            
        # 캐시 파일 경로 (프로젝트 루트)
        self.cache_file_path = self.documents_folder.parent / self.CACHE_FILENAME
        
        self.document_reader = DocumentReader()
        self.indexed_files_cache = {}  # 메모리 캐시
        
        # 영속적 캐시 로드
        self._load_persistent_cache()
        
    def _load_persistent_cache(self):
        """영속적 캐시 파일을 로드"""
        try:
            if not self.cache_file_path.exists():
                print(f"캐시 파일이 없습니다: {self.cache_file_path}")
                return
                
            # 파일 락을 사용하여 안전하게 읽기
            with self.cache_file_path.open('r', encoding='utf-8') as f:
                portalocker.lock(f, portalocker.LOCK_SH)
                try:
                    cache_data = json.load(f)
                finally:
                    portalocker.unlock(f)
                    
            # 캐시 데이터 검증
            if not isinstance(cache_data, dict) or 'indexed_files' not in cache_data:
                print("캐시 파일 형식이 올바르지 않습니다. 빈 캐시로 초기화합니다.")
                return
                
            # 버전 호환성 검사
            cache_version = cache_data.get('cache_version', '0.0')
            if cache_version != self.CACHE_VERSION:
                print(f"캐시 버전 불일치 (현재: {self.CACHE_VERSION}, 캐시: {cache_version}). 캐시를 초기화합니다.")
                return
                
            self.indexed_files_cache = cache_data['indexed_files']
            print(f"캐시 로드 완료: {len(self.indexed_files_cache)}개 파일")
            
        except json.JSONDecodeError as e:
            print(f"캐시 파일이 손상되었습니다 ({e}). 빈 캐시로 초기화합니다.")
            self.indexed_files_cache = {}
        except Exception as e:
            print(f"캐시 로드 중 오류 발생 ({e}). 빈 캐시로 초기화합니다.")
            self.indexed_files_cache = {}
    
    def _save_persistent_cache(self):
        """영속적 캐시 파일을 저장 (Atomic Write 패턴 사용)"""
        try:
            cache_data = {
                'cache_version': self.CACHE_VERSION,
                'last_updated': datetime.now().isoformat(),
                'indexed_files': self.indexed_files_cache
            }
            
            # Atomic Write: 임시 파일에 쓴 후 원본과 교체
            temp_file = self.cache_file_path.with_suffix('.tmp')
            
            # 파일 락을 사용하여 안전하게 쓰기
            with temp_file.open('w', encoding='utf-8') as f:
                portalocker.lock(f, portalocker.LOCK_EX)
                try:
                    json.dump(cache_data, f, indent=2, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())  # 디스크에 강제 쓰기
                finally:
                    portalocker.unlock(f)
            
            # 원자적 교체
            temp_file.replace(self.cache_file_path)
            
        except Exception as e:
            print(f"캐시 저장 중 오류 발생: {e}")
            # 임시 파일이 남아있다면 정리
            temp_file = self.cache_file_path.with_suffix('.tmp')
            if temp_file.exists():
                temp_file.unlink()
    
    def index_documents_folder(self, force_reindex: bool = False, 
                             progress_callback: Optional[Callable[[str, float], None]] = None) -> Dict[str, Any]:
        """
        documents 폴더의 모든 문서를 인덱싱
        
        Args:
            force_reindex: 기존 인덱스를 무시하고 모든 파일을 다시 인덱싱
            progress_callback: 진행률 알림 콜백 함수 (메시지, 진행률 0.0-1.0)
            
        Returns:
            인덱싱 결과 정보
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[INDEXER] index_documents_folder 메서드 시작 - force_reindex: {force_reindex}")
        logger.info(f"[INDEXER] documents_folder 경로: {self.documents_folder}")
        
        def notify_progress(message: str, progress: float):
            if progress_callback:
                progress_callback(message, progress)
        
        logger.info(f"[INDEXER] 문서 폴더 존재 여부 확인: {self.documents_folder.exists()}")
        if not self.documents_folder.exists():
            error_msg = f"문서 폴더가 존재하지 않습니다: {self.documents_folder}"
            logger.error(f"[INDEXER] {error_msg}")
            notify_progress(error_msg, 1.0)
            return {
                'status': 'error',
                'message': error_msg,
                'indexed_count': 0,
                'skipped_count': 0,
                'error_count': 0
            }
        
        logger.info(f"[INDEXER] notify_progress 호출 - 문서 폴더 스캔 중")
        notify_progress(f"문서 폴더 스캔 중: {self.documents_folder}", 0.1)
        logger.info(f"[INDEXER] 문서 폴더 인덱싱 시작: {self.documents_folder}")
        
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
        notify_progress("지원 파일 검색 중...", 0.2)
        supported_files = self._find_supported_files()
        
        if not supported_files:
            notify_progress("인덱싱할 지원 파일이 없습니다.", 1.0)
            print("인덱싱할 지원 파일이 없습니다.")
            return results
        
        print(f"발견된 지원 파일: {len(supported_files)}개")
        notify_progress(f"발견된 지원 파일: {len(supported_files)}개", 0.25)
        
        # 파일 처리
        total_files = len(supported_files)
        for i, file_path in enumerate(supported_files):
            # 진행률 계산 (25% ~ 90%)
            file_progress = 0.25 + (0.65 * i / total_files)
            notify_progress(f"처리 중: {Path(file_path).name} ({i+1}/{total_files})", file_progress)
            
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
                
                # 파일 캐시 업데이트
                self._update_file_cache(file_path, chunks_added)
                
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
        
        # 캐시 저장
        notify_progress("캐시 저장 중...", 0.95)
        self._save_persistent_cache()
        
        notify_progress("인덱싱 완료!", 1.0)
        
        print(f"\n인덱싱 완료:")
        print(f"  - 성공: {results['indexed_count']}개")
        print(f"  - 스킵: {results['skipped_count']}개")
        print(f"  - 오류: {results['error_count']}개")
        print(f"  - 총 청크: {results['total_chunks_added']}개")
        
        return results
    
    def _find_supported_files(self) -> List[str]:
        """지원하는 파일들을 찾아서 반환"""
        supported_files = []
        
        for file_path in self.documents_folder.rglob('*'):
            if file_path.is_file() and self.document_reader.is_supported_file(str(file_path)):
                supported_files.append(str(file_path))
        
        return sorted(supported_files)
    
    def _is_file_modified(self, file_path: str) -> bool:
        """
        파일이 마지막 인덱싱 이후 수정되었는지 확인
        성능 최적화: mtime 먼저 확인 후 해시 계산
        """
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return True
                
            # 현재 파일 정보 가져오기
            stat_info = file_path_obj.stat()
            current_mtime = stat_info.st_mtime
            current_size = stat_info.st_size
            
            # 캐시된 정보 확인
            cached_info = self.indexed_files_cache.get(file_path)
            if not cached_info:
                return True  # 캐시에 없으면 인덱싱 필요
            
            # 1차 검사: mtime과 size 비교 (빠른 스크리닝)
            cached_mtime = cached_info.get('mtime', 0)
            cached_size = cached_info.get('file_size', 0)
            
            if current_mtime == cached_mtime and current_size == cached_size:
                return False  # 수정되지 않음
            
            # 2차 검사: 해시 비교 (mtime이나 size가 다를 경우에만)
            current_hash = self._get_file_hash(file_path)
            cached_hash = cached_info.get('hash', '')
            
            return current_hash != cached_hash
            
        except Exception as e:
            print(f"파일 변경 확인 중 오류 ({file_path}): {e}")
            return True  # 오류가 발생하면 다시 인덱싱
    
    def _get_file_hash(self, file_path: str) -> str:
        """파일의 MD5 해시값 계산 (메모리 효율적)"""
        hash_md5 = hashlib.md5()
        
        try:
            file_path_obj = Path(file_path)
            
            # 파일 메타데이터 포함 (변경 감지 정확도 향상)
            stat_info = file_path_obj.stat()
            metadata = f"{stat_info.st_mtime}_{stat_info.st_size}"
            hash_md5.update(metadata.encode())
            
            # 파일 내용 해시 (청크 단위로 읽어서 메모리 효율적)
            with file_path_obj.open('rb') as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hash_md5.update(chunk)
            
            return hash_md5.hexdigest()
            
        except Exception as e:
            print(f"파일 해시 계산 중 오류 ({file_path}): {e}")
            # 오류 시 현재 시간 기반 해시 반환 (항상 다름을 보장)
            return hashlib.md5(str(time.time()).encode()).hexdigest()
    
    def _update_file_cache(self, file_path: str, chunks_count: int = 0):
        """파일 캐시 업데이트"""
        try:
            file_path_obj = Path(file_path)
            stat_info = file_path_obj.stat()
            
            self.indexed_files_cache[file_path] = {
                'mtime': stat_info.st_mtime,
                'hash': self._get_file_hash(file_path),
                'last_indexed': datetime.now().isoformat(),
                'chunks_count': chunks_count,
                'file_size': stat_info.st_size
            }
            
        except Exception as e:
            print(f"파일 캐시 업데이트 중 오류 ({file_path}): {e}")
    
    def get_folder_info(self) -> Dict[str, Any]:
        """documents 폴더 정보 반환"""
        if not self.documents_folder.exists():
            return {
                'exists': False,
                'total_files': 0,
                'supported_files': 0,
                'file_types': {}
            }
        
        all_files = []
        supported_files = []
        file_types = {}
        
        for file_path in self.documents_folder.rglob('*'):
            if file_path.is_file():
                all_files.append(str(file_path))
                
                file_ext = file_path.suffix.lower()
                file_types[file_ext] = file_types.get(file_ext, 0) + 1
                
                if self.document_reader.is_supported_file(str(file_path)):
                    supported_files.append(str(file_path))
        
        return {
            'exists': True,
            'folder_path': str(self.documents_folder.resolve()),
            'total_files': len(all_files),
            'supported_files': len(supported_files),
            'supported_extensions': self.document_reader.get_supported_extensions(),
            'file_types': file_types,
            'files': supported_files,
            'cache_info': {
                'cache_file': str(self.cache_file_path),
                'cached_files_count': len(self.indexed_files_cache),
                'cache_exists': self.cache_file_path.exists()
            }
        }
    
    def clear_document_index(self, clear_persistent_cache: bool = True):
        """문서 인덱스 캐시 초기화"""
        self.indexed_files_cache.clear()
        
        if clear_persistent_cache:
            try:
                if self.cache_file_path.exists():
                    self.cache_file_path.unlink()
                    print("영속적 캐시 파일이 삭제되었습니다.")
            except Exception as e:
                print(f"캐시 파일 삭제 중 오류 발생: {e}")
        
        print("문서 인덱스 캐시가 초기화되었습니다.")
    
    def reindex_single_file(self, file_path: str, 
                          progress_callback: Optional[Callable[[str, float], None]] = None) -> Dict[str, Any]:
        """단일 파일을 다시 인덱싱"""
        def notify_progress(message: str, progress: float):
            if progress_callback:
                progress_callback(message, progress)
        
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            error_msg = f'파일이 존재하지 않습니다: {file_path}'
            notify_progress(error_msg, 1.0)
            return {
                'status': 'error',
                'message': error_msg
            }
        
        if not self.document_reader.is_supported_file(file_path):
            error_msg = f'지원하지 않는 파일 형식입니다: {file_path}'
            notify_progress(error_msg, 1.0)
            return {
                'status': 'error',
                'message': error_msg
            }
        
        try:
            notify_progress(f"파일 읽기: {file_path_obj.name}", 0.2)
            print(f"단일 파일 인덱싱: {file_path}")
            
            # 문서 읽기
            doc_result = self.document_reader.read_document(file_path)
            
            if doc_result['metadata']['status'] == 'error':
                error_msg = doc_result['metadata'].get('error', 'Unknown error')
                notify_progress(error_msg, 1.0)
                return {
                    'status': 'error',
                    'message': error_msg
                }
            
            notify_progress("RAG 시스템에 추가 중...", 0.6)
            
            # RAG에 문서 추가
            chunks_added = self.rag_manager.add_document(
                document_text=doc_result['content'],
                document_type=f"document_{doc_result['metadata']['file_type']}",
                source_path=file_path
            )
            
            notify_progress("캐시 업데이트 중...", 0.9)
            
            # 파일 해시 업데이트
            self._update_file_cache(file_path, chunks_added)
            
            # 캐시 저장
            self._save_persistent_cache()
            
            notify_progress("완료!", 1.0)
            
            return {
                'status': 'success',
                'file': file_path,
                'chunks_added': chunks_added,
                'file_type': doc_result['metadata']['file_type'],
                'metadata': doc_result['metadata']
            }
            
        except Exception as e:
            error_msg = f'파일 인덱싱 중 오류 발생: {str(e)}'
            notify_progress(error_msg, 1.0)
            return {
                'status': 'error',
                'message': error_msg
            }
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """캐시 통계 정보 반환"""
        try:
            cache_exists = self.cache_file_path.exists()
            cache_size = self.cache_file_path.stat().st_size if cache_exists else 0
            
            # 캐시된 파일들의 통계
            total_chunks = sum(info.get('chunks_count', 0) for info in self.indexed_files_cache.values())
            
            # 최근 인덱싱된 파일들
            recent_files = []
            for file_path, info in sorted(
                self.indexed_files_cache.items(), 
                key=lambda x: x[1].get('last_indexed', ''), 
                reverse=True
            )[:5]:
                recent_files.append({
                    'file': Path(file_path).name,
                    'last_indexed': info.get('last_indexed'),
                    'chunks_count': info.get('chunks_count', 0)
                })
            
            return {
                'cache_file_exists': cache_exists,
                'cache_file_size_bytes': cache_size,
                'cached_files_count': len(self.indexed_files_cache),
                'total_cached_chunks': total_chunks,
                'recent_indexed_files': recent_files,
                'cache_file_path': str(self.cache_file_path)
            }
            
        except Exception as e:
            return {
                'error': f'캐시 통계 생성 중 오류: {str(e)}'
            }

    # TODO: FAISS에서 ChromaDB로 마이그레이션 필요
    # 현재 코드는 ChromaDB를 사용하고 있지만, 향후 FAISS 관련 레거시 코드가 
    # 발견될 경우 ChromaDB로 완전 마이그레이션해야 합니다.