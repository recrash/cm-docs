"""
RAG 시스템 API 테스트
"""

import pytest
from unittest.mock import patch, MagicMock

def test_get_rag_system_info(client):
    """RAG 시스템 정보 조회 테스트"""
    
    mock_rag_info = {
        "chroma_info": {
            "count": 100,
            "embedding_model": "jhgan/ko-sroberta-multitask"
        },
        "chunk_size": 1000,
        "documents": {
            "enabled": True,
            "folder_path": "/documents",
            "supported_files": 5,
            "total_files": 10,
            "file_types": {"docx": 3, "txt": 2}
        }
    }
    
    with patch('app.api.routers.rag.get_rag_info') as mock_get_rag_info:
        mock_get_rag_info.return_value = mock_rag_info
        
        response = client.get("/api/rag/info")
        
        assert response.status_code == 200
        data = response.json()
        assert "chroma_info" in data
        assert "chunk_size" in data
        assert "documents" in data

def test_index_documents_success(client):
    """문서 인덱싱 성공 테스트"""
    
    mock_result = {
        "status": "success",
        "indexed_count": 5,
        "total_chunks_added": 50,
        "message": "인덱싱 완료"
    }
    
    with patch('app.api.routers.rag.index_documents_folder') as mock_index, \
         patch('app.core.vector_db.document_indexer.DocumentIndexer'):
        mock_index.return_value = mock_result
        
        request_data = {"force_reindex": False}
        response = client.post("/api/rag/index", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["indexed_count"] == 5
        assert data["total_chunks_added"] == 50

def test_index_documents_force_reindex(client):
    """강제 재인덱싱 테스트"""
    
    mock_result = {
        "status": "success",
        "indexed_count": 10,
        "total_chunks_added": 100,
        "message": "재인덱싱 완료"
    }
    
    with patch('app.api.routers.rag.index_documents_folder') as mock_index, \
         patch('app.core.vector_db.document_indexer.DocumentIndexer'):
        mock_index.return_value = mock_result
        
        request_data = {"force_reindex": True}
        response = client.post("/api/rag/index", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        mock_index.assert_called_once_with(force_reindex=True)

def test_index_documents_failure(client):
    """문서 인덱싱 실패 테스트"""
    
    with patch('app.api.routers.rag.index_documents_folder') as mock_index:
        mock_index.side_effect = Exception("인덱싱 오류")
        
        request_data = {"force_reindex": False}
        response = client.post("/api/rag/index", json=request_data)
        
        assert response.status_code == 500
        assert "문서 인덱싱 중 오류" in response.json()["detail"]

def test_clear_vector_database_success(client):
    """벡터 데이터베이스 초기화 성공 테스트"""
    
    with patch('app.api.routers.rag.get_rag_manager') as mock_get_manager:
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager
        
        response = client.delete("/api/rag/clear")
        
        assert response.status_code == 200
        data = response.json()
        assert "성공적으로 초기화" in data["message"]
        mock_manager.clear_database.assert_called_once()

def test_clear_vector_database_no_manager(client):
    """RAG 매니저가 없는 경우 테스트"""
    
    with patch('app.api.routers.rag.get_rag_manager') as mock_get_manager:
        mock_get_manager.return_value = None
        
        response = client.delete("/api/rag/clear")
        
        assert response.status_code == 500
        assert "RAG 시스템을 초기화할 수 없습니다" in response.json()["detail"]

def test_clear_vector_database_failure(client):
    """벡터 데이터베이스 초기화 실패 테스트"""
    
    with patch('app.api.routers.rag.get_rag_manager') as mock_get_manager:
        mock_manager = MagicMock()
        mock_manager.clear_database.side_effect = Exception("초기화 오류")
        mock_get_manager.return_value = mock_manager
        
        response = client.delete("/api/rag/clear")
        
        assert response.status_code == 500
        assert "벡터 데이터베이스 초기화 중 오류" in response.json()["detail"]

def test_get_documents_info(client):
    """문서 정보 조회 테스트"""
    
    mock_rag_info = {
        "documents": {
            "enabled": True,
            "folder_path": "/documents",
            "supported_files": 8,
            "total_files": 15,
            "file_types": {"docx": 5, "txt": 3}
        }
    }
    
    with patch('app.api.routers.rag.get_rag_info') as mock_get_rag_info:
        mock_get_rag_info.return_value = mock_rag_info
        
        response = client.get("/api/rag/documents/info")
        
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert data["folder_path"] == "/documents"
        assert data["supported_files"] == 8
        assert data["total_files"] == 15

def test_get_rag_status_active(client):
    """RAG 시스템 활성 상태 테스트"""
    
    mock_rag_info = {
        "chroma_info": {
            "count": 50,
            "embedding_model": "jhgan/ko-sroberta-multitask"
        },
        "chunk_size": 1000
    }
    
    with patch('app.api.routers.rag.get_rag_info') as mock_get_rag_info, \
         patch('app.api.routers.rag.get_rag_manager') as mock_get_manager:
        
        mock_get_rag_info.return_value = mock_rag_info
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager
        
        response = client.get("/api/rag/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        assert "자동으로 활성화되었습니다" in data["message"]
        assert data["document_count"] == 50
        assert data["embedding_model"] == "jhgan/ko-sroberta-multitask"

def test_get_rag_status_inactive(client):
    """RAG 시스템 비활성 상태 테스트"""
    
    mock_rag_info = {
        "chroma_info": {"count": 0, "embedding_model": "Unknown"},
        "chunk_size": 0
    }
    
    with patch('app.api.routers.rag.get_rag_info') as mock_get_rag_info, \
         patch('app.api.routers.rag.get_rag_manager') as mock_get_manager:
        
        mock_get_rag_info.return_value = mock_rag_info
        mock_get_manager.return_value = None
        
        response = client.get("/api/rag/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "자동으로 로드됩니다" in data["message"]

def test_get_rag_status_error(client):
    """RAG 시스템 오류 상태 테스트"""
    
    with patch('app.api.routers.rag.get_rag_info') as mock_get_rag_info:
        mock_get_rag_info.side_effect = Exception("RAG 오류")
        
        response = client.get("/api/rag/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "오류가 발생했습니다" in data["message"]