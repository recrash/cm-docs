import logging
import sys
import os
import time
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import datetime



class DatedRotatingFileHandler(TimedRotatingFileHandler):
    """
    Custom handler to create log files with date at the beginning of the filename.
    e.g., 20250803_backend.log
    """
    def __init__(self, filename_prefix, when='midnight', backupCount=0, encoding=None, delay=False, utc=False, atTime=None):
        self.prefix = filename_prefix
        # Correctly determine project root and logs directory
        self.log_dir = Path(__file__).resolve().parents[1] / "logs"
        self.log_dir.mkdir(exist_ok=True)
        
        # Construct the initial filename
        current_date = datetime.date.today().strftime('%Y%m%d')
        filename = self.log_dir / f"{current_date}_{self.prefix}.log"
        
        super().__init__(str(filename), when, 1, backupCount, encoding, delay, utc, atTime)

    def doRollover(self):
        """
        Overwrites the rollover method to use the new date in the filename.
        """
        self.stream.close()
        # get the time that this sequence started at and make it a TimeTuple
        t = self.rolloverAt - self.interval
        if self.utc:
            timeTuple = time.gmtime(t)
        else:
            timeTuple = time.localtime(t)
        
        # New filename based on the new date
        dfn = str(self.log_dir / f"{time.strftime('%Y%m%d', timeTuple)}_{self.prefix}.log")

        if os.path.exists(dfn):
            os.remove(dfn)

        self.baseFilename = dfn
        
        # Open new log file
        self.stream = self._open()
        
        # Cleanup old logs
        if self.backupCount > 0:
            for s in self.getFilesToDelete():
                os.remove(s)

def setup_logging():
    """
    전체 애플리케이션의 로깅 설정을 초기화합니다.
    
    - 일별 로그 파일 생성 (backend, frontend 분리)
    - 콘솔 출력 비활성화 (한글 인코딩 에러 방지)
    - UTF-8 인코딩으로 파일 로깅
    - 모든 플랫폼에서 안정적인 동작
    """
    log_dir = Path(__file__).resolve().parents[1] / "logs"
    log_dir.mkdir(exist_ok=True)

    log_format = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    formatter = logging.Formatter(log_format)

    # --- 파일 핸들러 설정 ---
    backend_handler = DatedRotatingFileHandler("backend", backupCount=7)
    frontend_handler = DatedRotatingFileHandler("frontend", backupCount=7)
    
    backend_handler.setFormatter(formatter)
    frontend_handler.setFormatter(formatter)

    # --- 로거 설정 (콘솔 핸들러 제외, 파일 핸들러만 사용) ---
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(backend_handler)

    frontend_logger = logging.getLogger("frontend")
    if not frontend_logger.handlers:
        frontend_logger.setLevel(logging.INFO)
        frontend_logger.propagate = False
        frontend_logger.addHandler(frontend_handler)

    # 로깅 시스템 초기화 메시지 (파일에만 기록)
    initial_logger = logging.getLogger(__name__)
    initial_logger.info("로깅 시스템이 날짜 접두어 파일명으로 설정되었습니다.")
    initial_logger.info("안정성을 위해 파일 로깅만 활성화됨 (콘솔 출력 비활성화)")
