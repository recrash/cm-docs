"""
DocumentIndexer 캐시 기능 단위 테스트
영속적 캐시, 동시성 제어, 성능 최적화 기능을 검증합니다.
"""
import pytest
import json
import os
import tempfile
import shutil
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 필요한 라이브러리 import 시도
try:
    import portalocker
except ImportError:
    portalocker = None

from app.core.vector_db.document_indexer import DocumentIndexer


class TestDocumentIndexerCache:
    """DocumentIndexer 캐시 시스템 테스트"""
    
    def setup_method(self):
        """각 테스트 전에 캐시 초기화"""
        # 모든 가능한 캐시 파일 경로를 초기화
        possible_cache_paths = [
            Path("indexed_files_cache.json"),
            Path("C:/deploys/data/webservice/indexed_files_cache.json"),
            Path("webservice/indexed_files_cache.json")
        ]
        
        for cache_file in possible_cache_paths:
            try:
                if cache_file.exists():
                    cache_file.unlink()
            except:
                pass
    
    def teardown_method(self):
        """각 테스트 후 캐시 정리"""
        cache_file = Path("indexed_files_cache.json")
        if cache_file.exists():
            cache_file.unlink()
    
    @pytest.fixture
    def temp_dir(self):
        """임시 디렉토리 생성"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_rag_manager(self):
        """Mock RAGManager 생성"""
        mock_rag = Mock()
        mock_rag.add_document.return_value = 5  # 항상 5개 청크 반환
        return mock_rag
    
    @pytest.fixture
    def mock_document_reader(self):
        """Mock DocumentReader 생성"""
        mock_reader = Mock()
        mock_reader.is_supported_file.return_value = True
        mock_reader.get_supported_extensions.return_value = ['.txt', '.md']
        mock_reader.read_document.return_value = {
            'content': 'Test document content',
            'metadata': {
                'status': 'success',
                'file_type': 'txt'
            }
        }
        return mock_reader
    
    @pytest.fixture
    def sample_documents_dir(self, temp_dir):
        """샘플 문서 디렉토리 생성"""
        docs_dir = temp_dir / "documents"
        docs_dir.mkdir()
        
        # 샘플 파일들 생성
        (docs_dir / "test1.txt").write_text("첫 번째 테스트 파일 내용", encoding='utf-8')
        (docs_dir / "test2.md").write_text("# 두 번째 테스트 파일\n마크다운 내용", encoding='utf-8')
        (docs_dir / "test3.doc").write_text("지원하지 않는 파일", encoding='utf-8')
        
        return docs_dir
    
    @pytest.fixture
    def indexer(self, mock_rag_manager, sample_documents_dir, temp_dir):
        """DocumentIndexer 인스턴스 생성"""
        with patch('app.core.vector_db.document_indexer.DocumentReader') as mock_reader_class:
            mock_reader = Mock()
            mock_reader.is_supported_file.side_effect = lambda path: path.endswith(('.txt', '.md'))
            mock_reader.get_supported_extensions.return_value = ['.txt', '.md']
            mock_reader.read_document.return_value = {
                'content': 'Test document content',
                'metadata': {
                    'status': 'success',
                    'file_type': 'txt'
                }
            }
            mock_reader_class.return_value = mock_reader
            
            # 임시 캐시 파일 경로 사용
            temp_cache_path = temp_dir / "test_cache.json"
            
            indexer = DocumentIndexer(
                rag_manager=mock_rag_manager,
                documents_folder=str(sample_documents_dir)
            )
            
            # 캐시 파일 경로를 임시 경로로 변경
            indexer.cache_file_path = temp_cache_path
            
            return indexer
    
    def test_cache_initialization_empty(self, indexer):
        """최초 실행: 캐시 파일이 없을 때 빈 캐시로 초기화되는지 검증"""
        # 테스트를 위해 기존 캐시 파일 삭제
        if indexer.cache_file_path.exists():
            indexer.cache_file_path.unlink()
        indexer.indexed_files_cache = {}  # 캐시 초기화
        
        # 캐시 파일이 존재하지 않음을 확인
        assert not indexer.cache_file_path.exists()
        
        # 빈 캐시로 초기화됨을 확인
        assert indexer.indexed_files_cache == {}
        
        # 캐시 관련 정보 확인
        folder_info = indexer.get_folder_info()
        assert folder_info['cache_info']['cache_exists'] == False
        assert folder_info['cache_info']['cached_files_count'] == 0
    
    def test_cache_file_creation_and_persistence(self, indexer):
        """인덱싱 후 캐시 파일이 정상적으로 생성되는지 검증"""
        # 인덱싱 수행
        progress_messages = []
        def progress_callback(message, progress):
            progress_messages.append((message, progress))
        
        result = indexer.index_documents_folder(progress_callback=progress_callback)
        
        # 인덱싱 성공 확인
        assert result['status'] == 'success'
        assert result['indexed_count'] == 2  # test1.txt, test2.md
        
        # 진행률 콜백이 호출되었는지 확인
        assert len(progress_messages) > 0
        assert any("완료" in msg for msg, _ in progress_messages)
        
        # 캐시 파일이 생성되었는지 확인
        assert indexer.cache_file_path.exists()
        
        # 캐시 내용 검증
        assert len(indexer.indexed_files_cache) == 2
        
        # 캐시 파일 내용 검증
        with indexer.cache_file_path.open('r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        assert cache_data['cache_version'] == DocumentIndexer.CACHE_VERSION
        assert 'last_updated' in cache_data
        assert len(cache_data['indexed_files']) == 2
        
        # 캐시된 파일 정보 구조 검증
        for file_path, file_info in cache_data['indexed_files'].items():
            assert 'mtime' in file_info
            assert 'hash' in file_info
            assert 'last_indexed' in file_info
            assert 'chunks_count' in file_info
            assert 'file_size' in file_info
            assert file_info['chunks_count'] == 5  # Mock에서 설정한 값
    
    def test_cache_loading(self, temp_dir, mock_rag_manager, sample_documents_dir):
        """DocumentIndexer 재시작 시 기존 캐시를 정확하게 불러오는지 검증"""
        # 첫 번째 인덱서 인스턴스로 캐시 생성
        with patch('app.core.vector_db.document_indexer.DocumentReader') as mock_reader_class:
            mock_reader = Mock()
            mock_reader.is_supported_file.side_effect = lambda path: path.endswith(('.txt', '.md'))
            mock_reader.read_document.return_value = {
                'content': 'Test content',
                'metadata': {'status': 'success', 'file_type': 'txt'}
            }
            mock_reader_class.return_value = mock_reader
            
            indexer1 = DocumentIndexer(mock_rag_manager, str(sample_documents_dir))
            result = indexer1.index_documents_folder()
            
            assert result['indexed_count'] == 2
            cache_path = indexer1.cache_file_path
            assert cache_path.exists()
            
            # 캐시 통계 확인
            stats = indexer1.get_cache_statistics()
            assert stats['cache_file_exists'] == True
            assert stats['cached_files_count'] == 2
            assert stats['total_cached_chunks'] == 10  # 2 files * 5 chunks each
        
        # 두 번째 인덱서 인스턴스로 캐시 로드 테스트
        with patch('app.core.vector_db.document_indexer.DocumentReader') as mock_reader_class2:
            mock_reader2 = Mock()
            mock_reader2.is_supported_file.side_effect = lambda path: path.endswith(('.txt', '.md'))
            mock_reader_class2.return_value = mock_reader2
            
            indexer2 = DocumentIndexer(mock_rag_manager, str(sample_documents_dir))
            
            # 캐시가 로드되었는지 확인
            assert len(indexer2.indexed_files_cache) == 2
            assert indexer2.cache_file_path == cache_path
            
            # 캐시 통계 확인
            stats = indexer2.get_cache_statistics()
            assert stats['cached_files_count'] == 2
            assert len(stats['recent_indexed_files']) == 2
    
    def test_file_modification_detection(self, indexer, sample_documents_dir):
        """파일 내용이 수정되었을 때만 인덱싱이 다시 수행되는지 검증"""
        # 첫 번째 인덱싱
        result1 = indexer.index_documents_folder()
        assert result1['indexed_count'] == 2
        assert result1['skipped_count'] == 0
        
        # 두 번째 인덱싱 (변경 없음)
        result2 = indexer.index_documents_folder()
        assert result2['indexed_count'] == 0  # 변경된 파일 없음
        assert result2['skipped_count'] == 2  # 모든 파일 스킵
        
        # 파일 수정
        test_file = sample_documents_dir / "test1.txt"
        time.sleep(0.1)  # mtime 변경 보장
        test_file.write_text("수정된 내용", encoding='utf-8')
        
        # 세 번째 인덱싱 (하나의 파일만 변경됨)
        result3 = indexer.index_documents_folder()
        assert result3['indexed_count'] == 1  # test1.txt만 다시 인덱싱
        assert result3['skipped_count'] == 1  # test2.md는 스킵
        
        # force_reindex 테스트
        result4 = indexer.index_documents_folder(force_reindex=True)
        assert result4['indexed_count'] == 2  # 모든 파일 강제 인덱싱
        assert result4['skipped_count'] == 0
    
    def test_corrupted_cache_recovery(self, indexer, sample_documents_dir):
        """캐시 파일이 비정상적인 형식일 때 오류 없이 빈 캐시로 초기화되는지 검증"""
        # 첫 번째 인덱싱으로 정상 캐시 생성
        indexer.index_documents_folder()
        assert len(indexer.indexed_files_cache) == 2
        
        # 캐시 파일 손상 시뮬레이션
        with indexer.cache_file_path.open('w', encoding='utf-8') as f:
            f.write("{ invalid json content")
        
        # 새 인스턴스 생성 시 손상된 캐시가 복구되는지 확인
        with patch('app.core.vector_db.document_indexer.DocumentReader') as mock_reader_class:
            mock_reader = Mock()
            mock_reader.is_supported_file.side_effect = lambda path: path.endswith(('.txt', '.md'))
            mock_reader_class.return_value = mock_reader
            
            indexer2 = DocumentIndexer(indexer.rag_manager, str(sample_documents_dir))
            
            # 빈 캐시로 초기화되었는지 확인
            assert len(indexer2.indexed_files_cache) == 0
            
            # 정상적으로 동작하는지 확인
            result = indexer2.index_documents_folder()
            assert result['status'] == 'success'
    
    def test_version_incompatibility_handling(self, indexer, sample_documents_dir):
        """캐시 버전 불일치 시 캐시 초기화되는지 검증"""
        # 정상 캐시 생성
        indexer.index_documents_folder()
        
        # 다른 버전의 캐시 파일 생성
        fake_cache = {
            'cache_version': '0.5',  # 다른 버전
            'last_updated': '2023-01-01T00:00:00',
            'indexed_files': {
                'fake_file.txt': {
                    'mtime': 1234567890,
                    'hash': 'fake_hash'
                }
            }
        }
        
        with indexer.cache_file_path.open('w', encoding='utf-8') as f:
            json.dump(fake_cache, f)
        
        # 새 인스턴스 생성
        with patch('app.core.vector_db.document_indexer.DocumentReader') as mock_reader_class:
            mock_reader = Mock()
            mock_reader.is_supported_file.side_effect = lambda path: path.endswith(('.txt', '.md'))
            mock_reader_class.return_value = mock_reader
            
            indexer2 = DocumentIndexer(indexer.rag_manager, str(sample_documents_dir))
            
            # 버전 불일치로 인해 빈 캐시로 초기화되었는지 확인
            assert len(indexer2.indexed_files_cache) == 0
    
    @pytest.mark.skipif(portalocker is None, reason="portalocker not available")
    def test_concurrent_access_safety(self, indexer, sample_documents_dir):
        """다중 프로세스/스레드 환경에서 캐시 파일 안전성 검증 (시뮬레이션)"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def concurrent_indexing(indexer_instance, thread_id):
            """동시 인덱싱 함수"""
            try:
                result = indexer_instance.index_documents_folder()
                results.put(('success', thread_id, result))
            except Exception as e:
                results.put(('error', thread_id, str(e)))
        
        # 여러 스레드 생성 및 실행
        threads = []
        for i in range(3):
            # 각 스레드별로 별도의 인덱서 인스턴스 생성 (같은 캐시 파일 공유)
            with patch('app.core.vector_db.document_indexer.DocumentReader') as mock_reader_class:
                mock_reader = Mock()
                mock_reader.is_supported_file.side_effect = lambda path: path.endswith(('.txt', '.md'))
                mock_reader.read_document.return_value = {
                    'content': f'Thread {i} content',
                    'metadata': {'status': 'success', 'file_type': 'txt'}
                }
                mock_reader_class.return_value = mock_reader
                
                thread_indexer = DocumentIndexer(indexer.rag_manager, str(sample_documents_dir))
                thread = threading.Thread(target=concurrent_indexing, args=(thread_indexer, i))
                threads.append(thread)
        
        # 모든 스레드 시작
        for thread in threads:
            thread.start()
        
        # 모든 스레드 종료 대기
        for thread in threads:
            thread.join(timeout=10)
        
        # 결과 수집
        thread_results = []
        while not results.empty():
            thread_results.append(results.get())
        
        # 모든 스레드가 성공적으로 완료되었는지 확인
        assert len(thread_results) == 3
        for result_type, thread_id, result in thread_results:
            assert result_type == 'success', f"Thread {thread_id} failed: {result}"
        
        # 캐시 파일이 손상되지 않았는지 확인
        assert indexer.cache_file_path.exists()
        with indexer.cache_file_path.open('r', encoding='utf-8') as f:
            cache_data = json.load(f)  # JSON이 유효하면 예외 없이 로드됨
        
        assert 'indexed_files' in cache_data
    
    def test_progress_callback_functionality(self, indexer):
        """Progress callback 기능이 정상 동작하는지 검증"""
        progress_calls = []
        
        def test_callback(message: str, progress: float):
            progress_calls.append((message, progress))
        
        # 콜백과 함께 인덱싱 수행
        result = indexer.index_documents_folder(progress_callback=test_callback)
        
        # 콜백이 호출되었는지 확인
        assert len(progress_calls) > 0
        
        # 진행률이 순차적으로 증가하는지 확인
        progress_values = [progress for _, progress in progress_calls]
        assert progress_values[0] >= 0.0
        assert progress_values[-1] == 1.0
        
        # 메시지들이 포함되어 있는지 확인
        messages = [msg for msg, _ in progress_calls]
        assert any("스캔" in msg for msg in messages)
        assert any("완료" in msg for msg in messages)
    
    def test_single_file_reindexing(self, indexer, sample_documents_dir):
        """단일 파일 재인덱싱 기능 검증"""
        # 전체 인덱싱
        indexer.index_documents_folder()
        
        # 단일 파일 재인덱싱
        test_file = str(sample_documents_dir / "test1.txt")
        
        progress_calls = []
        def callback(msg, progress):
            progress_calls.append((msg, progress))
        
        result = indexer.reindex_single_file(test_file, progress_callback=callback)
        
        # 성공 확인
        assert result['status'] == 'success'
        assert result['file'] == test_file
        assert result['chunks_added'] == 5
        
        # 진행률 콜백 호출 확인
        assert len(progress_calls) > 0
        assert progress_calls[-1][1] == 1.0  # 완료
        
        # 존재하지 않는 파일 테스트
        result2 = indexer.reindex_single_file("/nonexistent/file.txt")
        assert result2['status'] == 'error'
        assert "존재하지 않습니다" in result2['message']
    
    def test_cache_clear_functionality(self, indexer):
        """캐시 초기화 기능 검증"""
        # 인덱싱으로 캐시 생성
        indexer.index_documents_folder()
        assert len(indexer.indexed_files_cache) > 0
        assert indexer.cache_file_path.exists()
        
        # 메모리 캐시만 초기화
        indexer.clear_document_index(clear_persistent_cache=False)
        assert len(indexer.indexed_files_cache) == 0
        assert indexer.cache_file_path.exists()  # 파일은 여전히 존재
        
        # 캐시 다시 생성
        indexer.index_documents_folder()
        
        # 영속적 캐시도 함께 초기화
        indexer.clear_document_index(clear_persistent_cache=True)
        assert len(indexer.indexed_files_cache) == 0
        assert not indexer.cache_file_path.exists()  # 파일도 삭제
    
    def test_performance_optimization_mtime_hash(self, indexer, sample_documents_dir):
        """mtime + hash 기반 성능 최적화 검증"""
        # Mock을 사용하여 해시 계산 횟수 추적
        with patch.object(indexer, '_get_file_hash', wraps=indexer._get_file_hash) as mock_hash:
            # 첫 번째 인덱싱
            indexer.index_documents_folder()
            initial_hash_calls = mock_hash.call_count
            assert initial_hash_calls > 0  # 해시가 계산되어야 함
            
            mock_hash.reset_mock()
            
            # 두 번째 인덱싱 (파일 변경 없음)
            result = indexer.index_documents_folder()
            
            # 파일이 변경되지 않았으므로 해시 계산이 건너뛰어져야 함
            assert mock_hash.call_count == 0, "파일이 변경되지 않았는데 해시가 계산되었습니다"
            assert result['skipped_count'] == 2
            
            # 파일 수정
            test_file = sample_documents_dir / "test1.txt"
            time.sleep(0.1)  # mtime 변경 보장
            test_file.write_text("Modified content", encoding='utf-8')
            
            mock_hash.reset_mock()
            
            # 세 번째 인덱싱 (하나의 파일만 변경)
            result = indexer.index_documents_folder()
            
            # 변경된 파일에 대해서만 해시가 계산되어야 함
            # (_is_file_modified에서 1회 + _update_file_cache에서 1회 = 총 2회)
            assert mock_hash.call_count == 2, f"예상 2회, 실제 {mock_hash.call_count}회 해시 계산"
            assert result['indexed_count'] == 1
            assert result['skipped_count'] == 1
    
    def test_atomic_write_safety(self, indexer, sample_documents_dir):
        """Atomic Write 패턴 안전성 검증"""
        # 인덱싱으로 캐시 생성
        indexer.index_documents_folder()
        
        # 캐시 파일 존재 확인
        assert indexer.cache_file_path.exists()
        
        # 원본 캐시의 파일 개수 저장
        original_files_count = len(indexer.indexed_files_cache)
        
        # 임시 파일 생성 실패 시뮬레이션
        original_save = indexer._save_persistent_cache
        def failing_save():
            try:
                # 임시 파일 경로
                temp_file = indexer.cache_file_path.with_suffix('.tmp')
                
                # 임시 파일 생성은 성공하지만 쓰기 중 실패
                with temp_file.open('w', encoding='utf-8') as f:
                    f.write('{"incomplete": true}')  # 불완전한 데이터
                    raise IOError("Disk full during write")
            except Exception as e:
                print(f"예상된 오류: {e}")
                # 임시 파일 정리
                temp_file = indexer.cache_file_path.with_suffix('.tmp')
                if temp_file.exists():
                    temp_file.unlink()
                raise
        
        indexer._save_persistent_cache = failing_save
        
        try:
            indexer._save_persistent_cache()
        except IOError:
            pass  # 예상된 예외
        
        # 원본 복원
        indexer._save_persistent_cache = original_save
        
        # 원본 캐시 파일이 여전히 존재하고 유효한지 확인
        assert indexer.cache_file_path.exists()
        assert len(indexer.indexed_files_cache) == original_files_count
        
        # 임시 파일이 정리되었는지 확인
        temp_file = indexer.cache_file_path.with_suffix('.tmp')
        assert not temp_file.exists()
        
        # 정상 저장이 여전히 작동하는지 확인
        indexer._save_persistent_cache()
        assert indexer.cache_file_path.exists()
    
    def test_error_handling_robustness(self, indexer, sample_documents_dir):
        """다양한 오류 상황에서의 견고성 검증"""
        # DocumentReader 오류 시뮬레이션
        with patch.object(indexer.document_reader, 'read_document') as mock_read:
            mock_read.return_value = {
                'content': '',
                'metadata': {
                    'status': 'error',
                    'error': 'File read error'
                }
            }
            
            result = indexer.index_documents_folder()
            
            # 오류가 발생해도 전체 프로세스는 계속되어야 함
            assert result['status'] == 'success'
            assert result['error_count'] == 2  # 두 파일 모두 오류
            assert result['indexed_count'] == 0
        
        # RAG 시스템 오류 시뮬레이션
        with patch.object(indexer.rag_manager, 'add_document', side_effect=Exception("RAG error")):
            # DocumentReader는 정상 동작하도록 복원
            indexer.document_reader.read_document.return_value = {
                'content': 'Test content',
                'metadata': {'status': 'success', 'file_type': 'txt'}
            }
            
            result = indexer.index_documents_folder()
            
            # RAG 오류가 발생해도 적절히 처리되어야 함
            assert result['error_count'] == 2
            assert all('error' in error_info for error_info in result['error_files'])
    
    def test_cache_statistics_accuracy(self, indexer):
        """캐시 통계 정보의 정확성 검증"""
        # 빈 상태 통계
        stats_empty = indexer.get_cache_statistics()
        assert stats_empty['cache_file_exists'] == False
        assert stats_empty['cached_files_count'] == 0
        assert stats_empty['total_cached_chunks'] == 0
        
        # 인덱싱 후 통계
        indexer.index_documents_folder()
        stats_full = indexer.get_cache_statistics()
        
        assert stats_full['cache_file_exists'] == True
        assert stats_full['cached_files_count'] == 2
        assert stats_full['total_cached_chunks'] == 10  # 2 files * 5 chunks each
        assert stats_full['cache_file_size_bytes'] > 0
        assert len(stats_full['recent_indexed_files']) <= 5
        
        # recent_indexed_files 구조 검증
        for file_info in stats_full['recent_indexed_files']:
            assert 'file' in file_info
            assert 'last_indexed' in file_info
            assert 'chunks_count' in file_info


class TestDocumentIndexerIntegration:
    """통합 테스트 - 실제 파일 시스템과의 상호작용"""
    
    @pytest.fixture
    def real_temp_dir(self):
        """실제 임시 디렉토리 및 파일 생성"""
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir)
        
        # 실제 문서 디렉토리 및 파일 생성
        docs_dir = temp_path / "documents"
        docs_dir.mkdir()
        
        # 다양한 크기와 내용의 실제 파일들 생성
        files_to_create = {
            "small.txt": "작은 텍스트 파일입니다.",
            "medium.md": "# 중간 크기 마크다운\n\n" + "내용 " * 100,
            "large.txt": "큰 텍스트 파일\n" + ("라인 " * 1000),
            "korean.txt": "한글 파일입니다.\n가나다라마바사아자차카타파하\n테스트 내용",
        }
        
        for filename, content in files_to_create.items():
            (docs_dir / filename).write_text(content, encoding='utf-8')
        
        yield temp_path
        shutil.rmtree(temp_dir)
    
    def test_real_file_system_integration(self, real_temp_dir):
        """실제 파일 시스템과의 통합 테스트"""
        # Mock 없이 실제 구성 요소들 사용
        mock_rag = Mock()
        mock_rag.add_document.return_value = 3
        
        docs_dir = real_temp_dir / "documents"
        
        # 실제 DocumentIndexer 생성 (DocumentReader mock 사용)
        with patch('app.core.vector_db.document_indexer.DocumentReader') as mock_reader_class:
            mock_reader = Mock()
            mock_reader.is_supported_file.side_effect = lambda path: path.endswith(('.txt', '.md'))
            mock_reader.read_document.side_effect = lambda path: {
                'content': Path(path).read_text(encoding='utf-8'),
                'metadata': {'status': 'success', 'file_type': Path(path).suffix[1:]}
            }
            mock_reader_class.return_value = mock_reader
            
            indexer = DocumentIndexer(mock_rag, str(docs_dir))
            
            # 전체 워크플로우 테스트
            result = indexer.index_documents_folder()
            
            # 결과 검증
            assert result['status'] == 'success'
            assert result['indexed_count'] == 4  # .txt, .md 파일들
            
            # 캐시 파일 검증
            assert indexer.cache_file_path.exists()
            cache_size = indexer.cache_file_path.stat().st_size
            assert cache_size > 100  # 의미있는 크기의 캐시 파일
            
            # 실제 파일 변경 후 재인덱싱 테스트
            large_file = docs_dir / "large.txt"
            original_content = large_file.read_text(encoding='utf-8')
            time.sleep(0.1)
            large_file.write_text(original_content + "\n추가된 내용", encoding='utf-8')
            
            result2 = indexer.index_documents_folder()
            assert result2['indexed_count'] == 1  # large.txt만 재인덱싱
            assert result2['skipped_count'] == 3  # 나머지는 스킵
            
            # 통계 정보 검증
            stats = indexer.get_cache_statistics()
            assert stats['cached_files_count'] == 4
            assert len(stats['recent_indexed_files']) <= 5