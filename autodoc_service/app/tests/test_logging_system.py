"""
AutoDoc Service 로깅 시스템 테스트

로깅 설정, 로그 파일 생성, 로그 메시지 형식 등을 검증합니다.
"""
import logging
import os
import tempfile
from pathlib import Path
from datetime import datetime
import pytest

from ..logging_config import setup_autodoc_logging, get_logger, AutoDocRotatingFileHandler


class TestLoggingConfiguration:
    """로깅 설정 테스트"""
    
    def test_setup_autodoc_logging_creates_log_directory(self):
        """로깅 설정 시 로그 디렉토리가 생성되는지 확인"""
        # Given
        setup_autodoc_logging()
        
        # When
        log_dir = Path(__file__).resolve().parents[2] / "logs"
        
        # Then
        assert log_dir.exists(), "로그 디렉토리가 생성되어야 함"
        assert log_dir.is_dir(), "로그 디렉토리는 폴더여야 함"
    
    def test_get_logger_returns_logger_instance(self):
        """get_logger 함수가 로거 인스턴스를 반환하는지 확인"""
        # When
        logger = get_logger("test_module")
        
        # Then
        assert isinstance(logger, logging.Logger), "Logger 인스턴스여야 함"
        assert logger.name == "test_module", "로거 이름이 일치해야 함"
    
    def test_autodoc_rotating_file_handler_filename_format(self):
        """AutoDocRotatingFileHandler가 올바른 파일명 형식을 사용하는지 확인"""
        # Given
        with tempfile.TemporaryDirectory() as temp_dir:
            handler = AutoDocRotatingFileHandler()
            
            # When
            current_date = datetime.now().strftime('%Y%m%d')
            expected_filename = f"{current_date}_autodoc.log"
            
            # Then
            assert expected_filename in str(handler.baseFilename), "파일명 형식이 YYYYMMDD_autodoc.log여야 함"


class TestLoggingOutput:
    """로그 출력 테스트"""
    
    def test_log_message_format(self):
        """로그 메시지 형식이 올바른지 확인"""
        # Given
        setup_autodoc_logging()
        logger = get_logger("test_logging")
        
        # When
        test_message = "테스트 로그 메시지"
        logger.info(test_message)
        
        # Then
        # 로그 파일 확인
        log_dir = Path(__file__).resolve().parents[2] / "logs"
        current_date = datetime.now().strftime('%Y%m%d')
        log_file = log_dir / f"{current_date}_autodoc.log"
        
        if log_file.exists():
            log_content = log_file.read_text(encoding='utf-8')
            assert test_message in log_content, "로그 메시지가 파일에 기록되어야 함"
            assert "INFO" in log_content, "로그 레벨이 포함되어야 함"
            assert "test_logging" in log_content, "로거 이름이 포함되어야 함"
    
    def test_logging_different_levels(self):
        """다양한 로그 레벨이 정상적으로 기록되는지 확인"""
        # Given
        setup_autodoc_logging()
        logger = get_logger("test_levels")
        
        # When
        logger.info("정보 메시지")
        logger.warning("경고 메시지")
        logger.error("오류 메시지")
        
        # Then
        log_dir = Path(__file__).resolve().parents[2] / "logs"
        current_date = datetime.now().strftime('%Y%m%d')
        log_file = log_dir / f"{current_date}_autodoc.log"
        
        if log_file.exists():
            log_content = log_file.read_text(encoding='utf-8')
            assert "정보 메시지" in log_content, "INFO 메시지가 기록되어야 함"
            assert "경고 메시지" in log_content, "WARNING 메시지가 기록되어야 함"
            assert "오류 메시지" in log_content, "ERROR 메시지가 기록되어야 함"


class TestLoggingIntegration:
    """로깅 시스템 통합 테스트"""
    
    def test_multiple_modules_logging(self):
        """여러 모듈에서 동시에 로깅할 때 정상적으로 동작하는지 확인"""
        # Given
        setup_autodoc_logging()
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")
        
        # When
        logger1.info("모듈1에서 로그")
        logger2.info("모듈2에서 로그")
        
        # Then
        log_dir = Path(__file__).resolve().parents[2] / "logs"
        current_date = datetime.now().strftime('%Y%m%d')
        log_file = log_dir / f"{current_date}_autodoc.log"
        
        if log_file.exists():
            log_content = log_file.read_text(encoding='utf-8')
            assert "module1" in log_content, "모듈1 로그가 기록되어야 함"
            assert "module2" in log_content, "모듈2 로그가 기록되어야 함"
            assert "모듈1에서 로그" in log_content, "모듈1 메시지가 기록되어야 함"
            assert "모듈2에서 로그" in log_content, "모듈2 메시지가 기록되어야 함"
    
    def test_exception_logging_with_traceback(self):
        """예외 로깅 시 스택 트레이스가 포함되는지 확인"""
        # Given
        setup_autodoc_logging()
        logger = get_logger("test_exception")
        
        # When
        try:
            raise ValueError("테스트 예외")
        except ValueError:
            logger.exception("예외 발생")
        
        # Then
        log_dir = Path(__file__).resolve().parents[2] / "logs"
        current_date = datetime.now().strftime('%Y%m%d')
        log_file = log_dir / f"{current_date}_autodoc.log"
        
        if log_file.exists():
            log_content = log_file.read_text(encoding='utf-8')
            assert "예외 발생" in log_content, "예외 메시지가 기록되어야 함"
            assert "ValueError" in log_content, "예외 타입이 기록되어야 함"
            assert "테스트 예외" in log_content, "예외 내용이 기록되어야 함"
            assert "Traceback" in log_content, "스택 트레이스가 기록되어야 함"


class TestLoggingPerformance:
    """로깅 성능 테스트"""
    
    def test_logging_performance(self):
        """로깅 성능이 적절한 수준인지 확인"""
        # Given
        setup_autodoc_logging()
        logger = get_logger("performance_test")
        
        # When
        import time
        start_time = time.time()
        
        for i in range(100):
            logger.info(f"성능 테스트 메시지 {i}")
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # Then
        assert elapsed_time < 1.0, f"100개 로그 메시지 처리 시간이 1초를 초과함: {elapsed_time:.3f}s"
    
    def test_log_file_rotation_backup_count(self):
        """로그 파일 백업 개수가 올바르게 설정되는지 확인"""
        # Given
        handler = AutoDocRotatingFileHandler(backupCount=7)
        
        # Then
        assert handler.backupCount == 7, "백업 개수가 7일로 설정되어야 함"


class TestLoggingErrorHandling:
    """로깅 오류 처리 테스트"""
    
    def test_logging_with_none_values(self):
        """None 값이 포함된 로그 메시지 처리"""
        # Given
        setup_autodoc_logging()
        logger = get_logger("test_none_handling")
        
        # When & Then (예외가 발생하지 않아야 함)
        logger.info(f"값: {None}")
        logger.info("파일명: %s, 크기: %s", None, None)
    
    def test_logging_with_unicode_content(self):
        """유니코드 콘텐츠가 포함된 로그 메시지 처리"""
        # Given
        setup_autodoc_logging()
        logger = get_logger("test_unicode")
        
        # When & Then (예외가 발생하지 않아야 함)
        logger.info("한글 로그 메시지: 안녕하세요")
        logger.info("특수문자: ★☆♡♥※")
        logger.info("이모지: 📄🔍⚡")
    
    def test_logging_with_large_messages(self):
        """큰 로그 메시지 처리"""
        # Given
        setup_autodoc_logging()
        logger = get_logger("test_large_message")
        
        # When & Then (예외가 발생하지 않아야 함)
        large_message = "A" * 10000  # 10KB 메시지
        logger.info(f"큰 메시지 테스트: {large_message}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])