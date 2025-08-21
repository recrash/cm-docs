"""
AutoDoc Service 로깅 설정

AutoDoc Service에 특화된 로깅 시스템 구성
- 일별 로그 파일 생성
- 적절한 로그 레벨 설정
- 서비스 특성에 맞는 로그 형식
- Windows 환경 한글 지원
"""
import logging
import sys
import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import datetime




class AutoDocRotatingFileHandler(TimedRotatingFileHandler):
    """
    AutoDoc Service용 커스텀 로그 핸들러
    날짜별 로그 파일 생성: YYYYMMDD_autodoc.log
    """
    def __init__(self, when='midnight', backupCount=7, encoding=None, delay=False, utc=False, atTime=None):
        # AutoDoc Service 로그 디렉토리 설정
        self.log_dir = Path(__file__).resolve().parents[1] / "logs"
        self.log_dir.mkdir(exist_ok=True)
        
        # 초기 파일명 구성
        current_date = datetime.date.today().strftime('%Y%m%d')
        filename = self.log_dir / f"{current_date}_autodoc.log"
        
        super().__init__(str(filename), when, 1, backupCount, encoding, delay, utc, atTime)

    def doRollover(self):
        """
        로그 파일 롤오버 시 새로운 날짜 기반 파일명 생성
        """
        if self.stream:
            self.stream.close()
        
        # 새로운 날짜 기반 파일명 생성
        current_date = datetime.date.today().strftime('%Y%m%d')
        new_filename = str(self.log_dir / f"{current_date}_autodoc.log")
        
        # 기존 파일이 있으면 제거 (같은 날짜 파일 덮어쓰기)
        if os.path.exists(new_filename):
            os.remove(new_filename)
        
        self.baseFilename = new_filename
        self.stream = self._open()
        
        # 백업 파일 정리
        if self.backupCount > 0:
            for file_to_delete in self.getFilesToDelete():
                os.remove(file_to_delete)


def setup_autodoc_logging():
    """
    AutoDoc Service 로깅 설정 초기화
    
    - 일별 로그 파일 생성 (UTF-8 인코딩)
    - 콘솔 출력 비활성화 (한글 인코딩 에러 방지)
    - AutoDoc Service에 최적화된 로그 형식
    - 모든 플랫폼에서 안정적인 파일 기반 로깅
    """
    # 로그 디렉토리 생성
    log_dir = Path(__file__).resolve().parents[1] / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # 로그 형식 설정
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
    formatter = logging.Formatter(log_format)
    
    # 파일 핸들러 설정 (일별 로테이션, 7일 백업, UTF-8 인코딩)
    file_handler = AutoDocRotatingFileHandler(backupCount=7, encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # 루트 로거 설정 (콘솔 핸들러 제외, 파일 핸들러만 사용)
    root_logger = logging.getLogger()
    
    # 기존 핸들러 제거 (중복 방지)
    if root_logger.handlers:
        root_logger.handlers.clear()
    
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    
    # AutoDoc Service 로거 초기화 메시지 (파일에만 기록)
    logger = logging.getLogger(__name__)
    logger.info("AutoDoc Service 로깅 시스템 초기화 완료")
    logger.info(f"로그 파일 위치: {log_dir}")
    logger.info("안정성을 위해 파일 로깅만 활성화됨 (콘솔 출력 비활성화)")


def get_logger(name: str) -> logging.Logger:
    """
    AutoDoc Service용 로거 생성 헬퍼 함수
    
    Args:
        name: 로거 이름 (보통 __name__ 사용)
    
    Returns:
        설정된 로거 인스턴스
    """
    return logging.getLogger(name)